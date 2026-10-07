"""Catalog quality checks. Each dataset gets a 0-100 score and a list of findings."""

from __future__ import annotations

# (check id, weight, message when it fails)
CHECKS = [
    ("description", 15, "Add a description of at least 40 characters."),
    ("owner", 15, "Name an owner (team or email) people can ask."),
    ("resources", 15, "List at least one data file under datapackage.resources."),
    ("schema", 15, "Declare the columns (schema.fields) for every data file."),
    ("field_docs", 10, "Describe at least half of the columns."),
    ("tags", 5, "Add tags so the dataset shows up in filters."),
    ("license", 5, "State a license or usage terms."),
    ("frequency", 5, "Say how often it is updated (update_frequency)."),
    ("status", 10, "Link a job (status_job) so freshness is monitored."),
    ("reachable", 5, "Metadata could not be fetched."),
]


def lint_dataset(d: dict, known_jobs: set[str] | None = None) -> dict:
    res = d.get("resources") or []
    fields = [f for r in res for f in r.get("fields") or []]
    documented = [f for f in fields if f.get("description")]
    jobs = d.get("status_jobs") or []
    passed = {
        "description": len(d.get("description") or "") >= 40,
        "owner": bool(d.get("owner")),
        "resources": bool(res),
        "schema": bool(res) and all(r.get("fields") for r in res),
        "field_docs": bool(fields) and len(documented) * 2 >= len(fields),
        "tags": bool(d.get("tags")),
        "license": bool(d.get("license")),
        "frequency": bool(d.get("update_frequency")),
        "status": bool(jobs)
        and (known_jobs is None or any(j in known_jobs for j in jobs)),
        "reachable": not d.get("error"),
    }
    total = sum(w for _, w, _ in CHECKS)
    score = sum(w for cid, w, _ in CHECKS if passed[cid])
    findings = [
        {"check": cid, "message": msg} for cid, _, msg in CHECKS if not passed[cid]
    ]
    if jobs and known_jobs is not None and not passed["status"]:
        findings = [
            f
            if f["check"] != "status"
            else {
                **f,
                "message": f"status_job {', '.join(jobs)} has no status files yet.",
            }
            for f in findings
        ]
    return {"score": round(100 * score / total), "findings": findings}
