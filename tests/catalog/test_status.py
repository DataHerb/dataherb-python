import datetime as dt
import json

from dataherb.catalog.status import assess, emit
from dataherb.catalog.stores import LocalStore

T0 = dt.datetime(2026, 1, 1, 12, tzinfo=dt.timezone.utc)
JOB = {"id": "etl", "expected_interval": "P1D", "max_duration": "PT1H"}


def state(status, started, finished=None, last_success=None, checks=None):
    run = {"id": "r", "status": status, "started_at": started.isoformat()}
    if finished:
        run["finished_at"] = finished.isoformat()
    return {
        "job": JOB,
        "run": run,
        "last_success": last_success,
        "checks": checks or [],
    }


def test_healthy_then_stale():
    s = state("success", T0, T0 + dt.timedelta(minutes=5))
    assert assess(s, now=T0 + dt.timedelta(hours=2))["health"] == "healthy"
    assert assess(s, now=T0 + dt.timedelta(hours=37))["health"] == "stale"


def test_failing_stuck_degraded_unknown():
    assert assess(state("failed", T0, T0), now=T0)["health"] == "failing"
    assert (
        assess(state("running", T0), now=T0 + dt.timedelta(hours=2))["health"]
        == "stuck"
    )
    assert (
        assess(
            state("running", T0, last_success={"finished_at": T0.isoformat()}),
            now=T0 + dt.timedelta(minutes=5),
        )["health"]
        == "running"
    )
    ok = {"finished_at": T0.isoformat()}
    assert (
        assess(state("partial", T0, T0, last_success=ok), now=T0)["health"]
        == "degraded"
    )
    assert (
        assess(state("partial", T0, T0), now=T0)["health"] == "stale"
    )  # never succeeded
    assert (
        assess(
            state("success", T0, T0, checks=[{"name": "c", "status": "fail"}]), now=T0
        )["health"]
        == "degraded"
    )
    assert assess({"job": JOB}, now=T0)["health"] == "unknown"


def test_emit_start_finish_carries_last_success(tmp_path):
    store = LocalStore("s", {"type": "local", "path": str(tmp_path)}, tmp_path)
    emit(
        store,
        "status",
        JOB,
        {"id": "1", "status": "success", "started_at": T0.isoformat()},
        now=T0 + dt.timedelta(minutes=1),
    )
    emit(
        store,
        "status",
        JOB,
        {"id": "2", "status": "running"},
        now=T0 + dt.timedelta(days=1),
    )
    doc = emit(
        store,
        "status",
        {"id": "etl"},
        {"status": "failed", "error": {"message": "boom"}},
        now=T0 + dt.timedelta(days=1, minutes=3),
    )

    assert doc["run"]["id"] == "2"  # finish reuses the running run
    assert doc["run"]["duration_seconds"] == 180
    assert doc["last_success"]["id"] == "1"
    assert doc["job"]["expected_interval"] == "P1D"  # job fields persist
    latest = json.loads((tmp_path / "status" / "etl" / "latest.json").read_text())
    assert latest["run"]["status"] == "failed"
    runs = sorted((tmp_path / "status" / "etl" / "runs").iterdir())
    assert len(runs) == 2  # run 2 was written twice under the same name
    assert (
        assess(latest, now=T0 + dt.timedelta(days=1, minutes=4))["health"] == "failing"
    )


def test_status_file_matches_schema(tmp_path):
    from dataherb.catalog.validate import errors

    store = LocalStore("s", {"type": "local", "path": str(tmp_path)}, tmp_path)
    doc = emit(
        store,
        "",
        JOB,
        {"id": "1", "status": "success"},
        checks=[{"name": "n", "status": "pass"}],
        metrics={"rows": 3},
    )
    assert errors("job-status", doc) == []
