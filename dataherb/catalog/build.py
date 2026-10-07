"""`dataherb catalog build`: config + catalog entries + job status -> a static site in dist/."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from dataherb.version import __version__
from .resolve import BuildIssue, build_catalog, load_entries
from .config import Config
from .lint import lint_dataset
from .status import HEALTH_ORDER, collect
from .stores import LocalStore, make_stores
from .util import dump_json, iso, log, utcnow
from .validate import errors


@dataclass
class BuildSummary:
    datasets: int
    jobs: int
    errors: int
    warnings: int
    out: Path


def validate_inputs(cfg: Config) -> list[BuildIssue]:
    issues = [
        BuildIssue("error", None, f"dataherb.config.yml {e}")
        for e in errors("config", cfg.data)
    ]
    entries, load_issues = load_entries(cfg)
    issues.extend(load_issues)
    for e in entries:
        doc = {k: v for k, v in e.items() if k != "_file"}
        for msg in errors("catalog-entry", doc):
            issues.append(BuildIssue("error", e.get("id"), f"{e['_file']} {msg}"))
        if e.get("inline"):
            for msg in errors("dataset", doc):
                issues.append(BuildIssue("warning", e.get("id"), f"{e['_file']} {msg}"))
    return issues


def link_jobs(datasets: list[dict], jobs: list[dict]) -> None:
    """Attach job health to datasets, via status_job in metadata or datasets[] in status files."""
    by_dataset: dict[str, set[str]] = {}
    for j in jobs:
        for d in (j.get("state") or {}).get("datasets") or []:
            if d.get("id"):
                by_dataset.setdefault(str(d["id"]), set()).add(j["id"])
    job_by_id = {j["id"]: j for j in jobs}
    for d in datasets:
        ids = list(
            dict.fromkeys(
                [*d.get("status_jobs", []), *sorted(by_dataset.get(d["id"], ()))]
            )
        )
        d["status_jobs"] = ids
        healths = [job_by_id[i]["health"] for i in ids if i in job_by_id]
        d["health"] = min(healths, key=HEALTH_ORDER.index) if healths else None
        updated = []
        for i in ids:
            jb = job_by_id.get(i)
            if not jb:
                continue
            updated.append(jb.get("last_success_at"))
            for ds in (jb.get("state") or {}).get("datasets") or []:
                if str(ds.get("id")) == d["id"] and ds.get("data_updated_at"):
                    updated.append(ds["data_updated_at"])
        d["updated_at"] = max((u for u in updated if u), default=None)


def build(
    cfg: Config, out: Path, site_dir: Path | None = None, strict: bool = False
) -> BuildSummary:
    started = utcnow()
    site_dir = site_dir or cfg.root / "site"
    if not (site_dir / "index.html").is_file():
        raise FileNotFoundError(
            f"no site template at {site_dir}; build from a fork of "
            "https://github.com/DataHerb/dataherb-explorer or pass --site"
        )
    issues = validate_inputs(cfg)

    log.info("resolving catalog")
    cat = build_catalog(cfg)
    issues.extend(cat.issues)

    log.info("collecting job status")
    jobs, status_issues = collect(cfg, now=started)
    issues.extend(BuildIssue(**i) for i in status_issues)

    link_jobs(cat.datasets, jobs)
    known = {j["id"] for j in jobs}
    for d in cat.datasets:
        d["quality"] = lint_dataset(d, known_jobs=known)

    # Assemble the site.
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(site_dir, out, ignore=shutil.ignore_patterns("data", ".DS_Store"))
    for store in make_stores(cfg.stores, cfg.root).values():
        if isinstance(store, LocalStore):
            store.publish(out)
    if (
        cfg.explorer.get("duckdb", {}).get("mode") == "vendored"
        and not (out / "vendor" / "duckdb").exists()
    ):
        issues.append(
            BuildIssue(
                "error",
                None,
                "explorer.duckdb.mode is 'vendored' but site/vendor/duckdb is missing; run `npm ci && npm run vendor`",
            )
        )

    visible = [d for d in cat.datasets if not d.get("hidden")]
    n_err = sum(1 for i in issues if i.level == "error")
    n_warn = sum(1 for i in issues if i.level == "warning")
    generated = iso(utcnow())
    dump_json(
        {**cfg.public(), "generated_at": generated, "version": __version__},
        out / "data" / "config.json",
    )
    dump_json(
        {"generated_at": generated, "datasets": visible}, out / "data" / "catalog.json"
    )
    dump_json({"generated_at": generated, "jobs": jobs}, out / "data" / "status.json")
    dump_json(
        {
            "generated_at": generated,
            "duration_seconds": round((utcnow() - started).total_seconds(), 2),
            "version": __version__,
            "datasets": len(visible),
            "jobs": len(jobs),
            "errors": n_err,
            "warnings": n_warn,
            "issues": [i.as_dict() for i in issues],
        },
        out / "data" / "build.json",
        pretty=True,
    )
    (out / ".nojekyll").write_text("")
    if strict and n_err:
        raise SystemExit(
            f"build finished with {n_err} error(s); see {out / 'data' / 'build.json'}"
        )
    return BuildSummary(
        datasets=len(visible), jobs=len(jobs), errors=n_err, warnings=n_warn, out=out
    )
