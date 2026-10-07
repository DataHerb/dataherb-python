"""Job status files: writing them (emit), reading them (collect) and judging them (assess).

Layout under a status prefix (see docs/job-status-spec.md):

    <prefix>/<job_id>/latest.json                     current state, overwritten every write
    <prefix>/<job_id>/runs/<started>-<run_id>.json    one immutable file per run
"""

from __future__ import annotations

import datetime as dt
import json
import posixpath
import re
from pathlib import Path
from typing import Any

from dataherb.version import __version__
from .config import Config
from .stores import LocalStore, S3Store, Store, StoreError, make_stores
from .util import FetchError, iso, parse_duration, parse_time, utcnow

SPEC = "dataherb.status/v1"

# Worst first. The site sorts and colours by this order.
HEALTH_ORDER = [
    "failing",
    "stuck",
    "stale",
    "degraded",
    "running",
    "healthy",
    "unknown",
]

TERMINAL = {"success", "partial", "failed", "skipped", "cancelled"}


def assess(state: dict, now: dt.datetime | None = None, grace: float = 0.5) -> dict:
    """Derive health from a latest.json document.

    Returns {"health", "reason", "last_success_at", "next_expected_at"}.
    Mirrored in site/assets/lib/health.js of dataherb-explorer; keep the two in sync.
    """
    now = now or utcnow()
    job = state.get("job") or {}
    run = state.get("run") or {}
    status = run.get("status")
    expected = parse_duration(job.get("expected_interval"))
    max_duration = parse_duration(job.get("max_duration"))

    last_success = state.get("last_success")
    if status == "success":
        last_success = run
    ls_at = parse_time(
        (last_success or {}).get("finished_at")
        or (last_success or {}).get("started_at")
    )
    next_expected = ls_at + expected if (ls_at and expected) else None
    stale = bool(expected and (ls_at is None or now - ls_at > expected * (1 + grace)))

    def out(health: str, reason: str) -> dict:
        return {
            "health": health,
            "reason": reason,
            "last_success_at": iso(ls_at),
            "next_expected_at": iso(next_expected),
        }

    if not run:
        return out("unknown", "no runs recorded")
    started = parse_time(run.get("started_at"))
    if status in ("running", "queued"):
        if max_duration and started and now - started > max_duration:
            return out(
                "stuck",
                f"{status} for {_human(now - started)} (max {job.get('max_duration')})",
            )
        if stale:
            return out("stale", _stale_reason(now, ls_at))
        return out(
            "running", f"{status} for {_human(now - started)}" if started else status
        )
    if status in ("failed", "cancelled"):
        err = (run.get("error") or {}).get("message") or run.get("message") or ""
        return out("failing", f"last run {status}" + (f": {err}" if err else ""))
    if stale:
        return out("stale", _stale_reason(now, ls_at))
    failed_checks = [
        c.get("name") for c in state.get("checks") or [] if c.get("status") == "fail"
    ]
    if status == "partial" or failed_checks:
        why = (
            "last run partial"
            if status == "partial"
            else f"checks failed: {', '.join(failed_checks)}"
        )
        return out("degraded", why)
    if status in ("success", "skipped"):
        return out(
            "healthy",
            "last run succeeded" if status == "success" else "last run skipped",
        )
    return out("unknown", f"unrecognised status {status!r}")


def _stale_reason(now: dt.datetime, ls_at: dt.datetime | None) -> str:
    if ls_at is None:
        return "never succeeded"
    return f"last success {_human(now - ls_at)} ago"


def _human(td: dt.timedelta) -> str:
    s = int(td.total_seconds())
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if s >= size:
            return f"{s // size}{unit}"
    return f"{s}s"


def run_filename(run: dict) -> str:
    started = parse_time(run.get("started_at")) or utcnow()
    safe_id = re.sub(r"[^A-Za-z0-9._-]+", "_", str(run.get("id")))[:120]
    return f"{started.strftime('%Y%m%dT%H%M%SZ')}-{safe_id}.json"


def _read_json(store: Store, key: str) -> dict | None:
    try:
        return json.loads(store.read(key))
    except FetchError:
        return None


def emit(
    store: Store,
    prefix: str,
    job: dict,
    run: dict,
    datasets: list[dict] | None = None,
    checks: list[dict] | None = None,
    metrics: dict | None = None,
    now: dt.datetime | None = None,
) -> dict:
    """Write a status update for one run. Safe to call at start and again at the end of a run."""
    now = now or utcnow()
    if not job.get("id"):
        raise ValueError("job.id is required")
    base = (
        posixpath.join(prefix.strip("/"), job["id"]) if prefix.strip("/") else job["id"]
    )
    previous = _read_json(store, f"{base}/latest.json") or {}
    prev_run = previous.get("run") or {}

    run = {k: v for k, v in run.items() if v is not None}
    run.setdefault(
        "id",
        prev_run.get("id")
        if prev_run.get("status") in ("running", "queued")
        else iso(now),
    )
    same_run = prev_run.get("id") == run["id"]
    if same_run:
        run.setdefault("started_at", prev_run.get("started_at"))
        if prev_run.get("attempt") and "attempt" not in run:
            run["attempt"] = prev_run["attempt"]
    run.setdefault("started_at", iso(now))
    run.setdefault("status", "running")
    if run["status"] in TERMINAL:
        run.setdefault("finished_at", iso(now))
        s, f = parse_time(run["started_at"]), parse_time(run["finished_at"])
        if s and f and "duration_seconds" not in run:
            run["duration_seconds"] = round((f - s).total_seconds(), 3)

    # Job description: keep fields from earlier writes unless overridden.
    merged_job = {
        **(previous.get("job") or {}),
        **{k: v for k, v in job.items() if v is not None},
    }

    last_success = previous.get("last_success")
    if prev_run.get("status") == "success" and not same_run:
        last_success = prev_run
    if run["status"] == "success":
        last_success = run

    doc: dict[str, Any] = {
        "spec": SPEC,
        "job": merged_job,
        "run": run,
        "last_success": last_success,
        "datasets": datasets or [],
        "checks": checks or [],
        "metrics": metrics or {},
        "producer": {"name": "dataherb", "version": __version__},
        "written_at": iso(now),
    }
    body = json.dumps(doc, indent=2, default=str).encode()
    store.write(f"{base}/runs/{run_filename(run)}", body)
    store.write(f"{base}/latest.json", body)
    return doc


def store_for_target(target: str, root: Path | None = None) -> tuple[Store, str]:
    """Resolve `s3://bucket/prefix` or a local folder into (store, prefix) for emitters without a config."""
    if target.startswith("s3://"):
        bucket, _, prefix = target[5:].partition("/")
        return (
            S3Store("target", {"type": "s3", "bucket": bucket}, root or Path(".")),
            prefix,
        )
    return (
        LocalStore(
            "target",
            {"type": "local", "path": str(Path(target).resolve())},
            root or Path("."),
        ),
        "",
    )


def _summary(run: dict) -> dict:
    return {
        k: run.get(k)
        for k in (
            "id",
            "status",
            "started_at",
            "finished_at",
            "duration_seconds",
            "url",
            "message",
        )
    }


def collect(
    cfg: Config, now: dt.datetime | None = None
) -> tuple[list[dict], list[dict]]:
    """Read every job's latest.json (and run history where the store can list)."""
    now = now or utcnow()
    stores = make_stores(cfg.stores, cfg.root)
    grace = float(cfg.status.get("stale_grace", 0.5))
    history_n = int(cfg.status.get("history", 30))
    jobs: dict[str, dict] = {}
    issues: list[dict] = []

    for src in cfg.status.get("sources") or []:
        store = stores.get(src.get("store"))
        if store is None:
            issues.append(
                {
                    "level": "error",
                    "dataset": None,
                    "message": f"status: unknown store '{src.get('store')}'",
                }
            )
            continue
        prefix = (src.get("prefix") or "").strip("/")
        keys: list[str] = []
        job_ids = list(src.get("jobs") or [])
        if not job_ids:
            try:
                keys = store.list(prefix)
            except (StoreError, FetchError) as e:
                issues.append(
                    {
                        "level": "error",
                        "dataset": None,
                        "message": f"status {store.name}:{prefix}: {e}",
                    }
                )
                continue
            rel = [k[len(prefix) :].lstrip("/") if prefix else k for k in keys]
            job_ids = sorted(
                {
                    r.split("/")[0]
                    for r in rel
                    if r.endswith("/latest.json") and r.count("/") == 1
                }
            )
        for jid in job_ids:
            base = f"{prefix}/{jid}" if prefix else jid
            state = _read_json(store, f"{base}/latest.json")
            if state is None:
                issues.append(
                    {
                        "level": "error",
                        "dataset": None,
                        "message": f"status: cannot read {store.describe(base + '/latest.json')}",
                    }
                )
                continue
            run_keys = sorted(
                (
                    k
                    for k in keys
                    if k.startswith(f"{base}/runs/") and k.endswith(".json")
                ),
                reverse=True,
            )
            history = []
            for k in run_keys[:history_n]:
                r = _read_json(store, k)
                if r and r.get("run"):
                    history.append(_summary(r["run"]))
            if not history and state.get("run"):
                history = [_summary(state["run"])]
            job = state.get("job") or {}
            verdict = assess(state, now=now, grace=grace)
            jobs[jid] = {
                "id": jid,
                "name": job.get("name") or jid,
                "description": job.get("description"),
                "owner": job.get("owner"),
                "orchestrator": job.get("orchestrator"),
                "url": job.get("url"),
                "schedule": job.get("schedule"),
                "expected_interval": job.get("expected_interval"),
                "max_duration": job.get("max_duration"),
                "tags": job.get("tags") or [],
                "latest_url": store.browser_url(f"{base}/latest.json"),
                "state": state,
                "history": history,
                **verdict,
            }
    ordered = sorted(
        jobs.values(),
        key=lambda j: (HEALTH_ORDER.index(j["health"]), j["name"].lower()),
    )
    return ordered, issues
