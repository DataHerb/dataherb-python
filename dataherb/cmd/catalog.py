"""`dataherb catalog ...` and `dataherb status ...` commands.

`catalog` builds and checks a DataHerb Explorer site (a static catalog
configured by dataherb.config.yml). `status` writes and checks job status
files (spec: dataherb.status/v1).
"""

import functools
import http.server
import json
import sys
from pathlib import Path

import click

from dataherb.catalog.util import iso, utcnow

CONFIG_OPTION = click.option(
    "--config",
    "-c",
    "config_path",
    default="dataherb.config.yml",
    show_default=True,
    type=click.Path(dir_okay=False),
    help="Path to the explorer config.",
)


def _load(config_path):
    from dataherb.catalog.config import load_config

    return load_config(config_path)


@click.group()
def catalog():
    """Build and check a static DataHerb Explorer catalog."""


@catalog.command()
@CONFIG_OPTION
@click.option("--out", "-o", default="dist", show_default=True, help="Output folder.")
@click.option(
    "--site",
    default=None,
    help="Site template folder; defaults to site/ next to the config.",
)
@click.option(
    "--strict", is_flag=True, help="Exit non-zero when any dataset fails to resolve."
)
def build(config_path, out, site, strict):
    """Build the static site from the config, catalog entries and job status."""
    from dataherb.catalog.build import build as _build

    s = _build(
        _load(config_path),
        Path(out).resolve(),
        site_dir=Path(site).resolve() if site else None,
        strict=strict,
    )
    click.echo(
        f"built {s.datasets} datasets, {s.jobs} jobs -> {s.out}  ({s.errors} errors, {s.warnings} warnings)"
    )
    for i in json.loads((s.out / "data" / "build.json").read_text())["issues"]:
        if i["level"] == "error":
            click.secho(
                f"  error: {i['dataset'] or '-'}: {i['message']}", fg="red", err=True
            )


@catalog.command("validate")
@CONFIG_OPTION
def validate_catalog(config_path):
    """Validate the config and catalog entries against the schemas."""
    from dataherb.catalog.build import validate_inputs

    issues = validate_inputs(_load(config_path))
    for i in issues:
        click.secho(
            f"{i.level}: {i.dataset or '-'}: {i.message}",
            fg="red" if i.level == "error" else "yellow",
        )
    n = sum(1 for i in issues if i.level == "error")
    if n:
        click.secho(f"{n} error(s)", fg="red")
        sys.exit(1)
    click.secho("config and catalog entries are valid", fg="green")


@catalog.command()
@CONFIG_OPTION
@click.option(
    "--min-score", type=int, default=None, help="Fail when any dataset scores lower."
)
def lint(config_path, min_score):
    """Score metadata quality for every dataset and list what is missing."""
    from dataherb.catalog.lint import lint_dataset
    from dataherb.catalog.resolve import build_catalog
    from dataherb.catalog.status import collect

    cfg = _load(config_path)
    cat = build_catalog(cfg)
    jobs, _ = collect(cfg)
    known = {j["id"] for j in jobs}
    rows = []
    for d in cat.datasets:
        q = lint_dataset(d, known_jobs=known)
        rows.append((q["score"], d["id"], q["findings"]))
    rows.sort()
    for score, did, findings in rows:
        click.echo(f"{score:>3}  {did}")
        for f in findings:
            click.echo(f"       - {f['message']}")
    worst = min((r[0] for r in rows), default=100)
    if min_score is not None and worst < min_score:
        click.secho(
            f"lowest score {worst} is below --min-score {min_score}", fg="red", err=True
        )
        sys.exit(1)


@catalog.command("add")
@CONFIG_OPTION
@click.argument("repos", nargs=-1)
@click.option("--org", help="Add every repo of this GitHub org (or user).")
@click.option(
    "--match",
    default="",
    help="With --org: only repos whose name starts with this, e.g. dataset.",
)
@click.option(
    "--strip-prefix",
    default=None,
    help="Drop this from repo names to make ids. Defaults to --match.",
)
@click.option("--store", "store_name", help="Git store from the config.")
@click.option("--ref", help="Branch, tag or sha to pin.")
@click.option(
    "--tag", "tags", multiple=True, help="Tag for the new entries. Repeatable."
)
@click.option(
    "--api-url",
    default="https://api.github.com",
    show_default=True,
    help="GitHub API, for --org (GitHub Enterprise: https://HOST/api/v3).",
)
@click.option(
    "--include-archived", is_flag=True, help="With --org: keep archived repos."
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["md", "yml"]),
    default="md",
    show_default=True,
    help="Markdown with YAML front matter, or plain YAML.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite entries that already exist (a Markdown body is kept).",
)
@click.option("--dry-run", is_flag=True, help="Show what would be written.")
def add_to_catalog(
    config_path,
    repos,
    org,
    match,
    strip_prefix,
    store_name,
    ref,
    tags,
    api_url,
    include_archived,
    fmt,
    force,
    dry_run,
):
    """Add git repos (owner/name) to the catalog, one Markdown file per repo in catalog/.

    Repos with a dataherb.json/.yml get a pointer entry. Repos without one
    are cloned and scanned, and get an inline entry with the inferred files
    and columns.

    \b
    dataherb catalog add DataHerb/dataset-covid-19
    dataherb catalog add --org DataHerb --match dataset
    """
    from dataherb.catalog.add import add_repos, list_org_repos, org_token

    cfg = _load(config_path)
    repos = list(repos)
    if org:
        repos += list_org_repos(
            org,
            match,
            api_url=api_url,
            token=org_token(cfg, store_name),
            include_archived=include_archived,
        )
    if not repos:
        raise click.UsageError("give repos as owner/name, or --org")
    results = add_repos(
        cfg,
        list(dict.fromkeys(repos)),
        store_name=store_name,
        ref=ref,
        strip_prefix=match if strip_prefix is None else strip_prefix,
        tags=tags,
        force=force,
        dry_run=dry_run,
        fmt=fmt,
    )
    colors = {"pointer": "green", "inline": "green", "skipped": "yellow"}
    for r in results:
        where = (
            r.path.relative_to(cfg.root)
            if r.path and r.path.is_relative_to(cfg.root)
            else (r.path or "-")
        )
        click.secho(f"{r.kind:<8} {r.repo} -> {where}  ({r.note})", fg=colors[r.kind])
    added = sum(r.kind != "skipped" for r in results)
    click.echo(
        f"{'would add' if dry_run else 'added'} {added} of {len(results)} repo(s)"
    )


@catalog.command("serve")
@click.argument("folder", default="dist", type=click.Path(exists=True, file_okay=False))
@click.option("--port", "-p", default=8000, show_default=True)
def serve_catalog(folder, port):
    """Serve a built catalog locally."""
    root = Path(folder).resolve()
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(root)
    )
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        click.echo(f"serving {root} at http://127.0.0.1:{port}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


@click.group()
def status():
    """Write and check job status files (spec: dataherb.status/v1)."""


def _number(v):
    try:
        return float(v) if "." in v else int(v)
    except ValueError:
        return None


@status.command()
@click.option(
    "--target", help="s3://bucket/prefix or a local folder. Overrides the config."
)
@click.option(
    "--config",
    "-c",
    "config_path",
    default="dataherb.config.yml",
    show_default=True,
    help="Explorer config, used when --target is not given.",
)
@click.option("--store", help="Status source store from the config.")
@click.option("--job-id", required=True)
@click.option("--job-name")
@click.option("--owner")
@click.option("--orchestrator")
@click.option("--job-url")
@click.option("--schedule")
@click.option(
    "--expected-interval",
    help="ISO 8601 duration between successful runs, e.g. P1D, PT6H.",
)
@click.option(
    "--max-duration", help="ISO 8601 duration after which a running run is stuck."
)
@click.option("--run-id")
@click.option(
    "--status",
    "run_status",
    required=True,
    type=click.Choice(
        ["queued", "running", "success", "partial", "failed", "skipped", "cancelled"]
    ),
)
@click.option("--started-at")
@click.option("--finished-at")
@click.option("--attempt", type=int)
@click.option(
    "--trigger",
    type=click.Choice(["schedule", "manual", "event", "backfill", "unknown"]),
)
@click.option("--run-url")
@click.option("--message")
@click.option("--error")
@click.option(
    "--dataset",
    "datasets",
    multiple=True,
    help="Dataset id this run refreshed, optionally id:rows. Repeatable.",
)
@click.option(
    "--check", "checks", multiple=True, help="name=pass|warn|fail. Repeatable."
)
@click.option("--metric", "metrics", multiple=True, help="name=number. Repeatable.")
def emit(
    target,
    config_path,
    store,
    job_id,
    job_name,
    owner,
    orchestrator,
    job_url,
    schedule,
    expected_interval,
    max_duration,
    run_id,
    run_status,
    started_at,
    finished_at,
    attempt,
    trigger,
    run_url,
    message,
    error,
    datasets,
    checks,
    metrics,
):
    """Write a status update for a job run (call at start and at the end)."""
    from dataherb.catalog.status import emit as _emit
    from dataherb.catalog.status import store_for_target
    from dataherb.catalog.stores import make_stores

    if target:
        st, prefix = store_for_target(target)
    else:
        cfg = _load(config_path)
        stores = make_stores(cfg.stores, cfg.root)
        src = next(
            (
                s
                for s in cfg.status.get("sources") or []
                if not store or s.get("store") == store
            ),
            None,
        )
        if src is None:
            raise click.UsageError(
                "no status source in the config (or --store not found); pass --target"
            )
        st, prefix = stores[src["store"]], src.get("prefix", "")
    job = {
        "id": job_id,
        "name": job_name,
        "owner": owner,
        "orchestrator": orchestrator,
        "url": job_url,
        "schedule": schedule,
        "expected_interval": expected_interval,
        "max_duration": max_duration,
    }
    run = {
        "id": run_id,
        "status": run_status,
        "started_at": started_at,
        "finished_at": finished_at,
        "attempt": attempt,
        "trigger": trigger,
        "url": run_url,
        "message": message,
        "error": {"message": error} if error else None,
    }
    ds = []
    for d in datasets:
        did, _, rows = d.partition(":")
        ds.append(
            {
                "id": did,
                **({"rows": int(rows)} if rows else {}),
                "data_updated_at": iso(utcnow()),
            }
        )
    ck = []
    for c in checks:
        name, _, result = c.partition("=")
        ck.append({"name": name, "status": result or "pass"})
    ms = {k: _number(v) for k, _, v in (m.partition("=") for m in metrics)}
    doc = _emit(st, prefix, job, run, datasets=ds, checks=ck, metrics=ms)
    click.echo(
        f"{doc['job']['id']}: run {doc['run']['id']} -> {doc['run']['status']} ({st.describe(prefix)})"
    )


@status.command()
@CONFIG_OPTION
@click.option(
    "--fail-on",
    default="failing,stuck,stale",
    show_default=True,
    help="Health values that make the command fail.",
)
def check(config_path, fail_on):
    """Print every job's health; exit 1 if any job is unhealthy."""
    from dataherb.catalog.status import collect

    jobs, issues = collect(_load(config_path))
    bad = set(fail_on.split(","))
    failing = 0
    for j in jobs:
        hit = j["health"] in bad
        failing += hit
        click.secho(
            f"{'!!' if hit else '  '} {j['health']:<9} {j['id']:<32} {j['reason']}",
            fg="red" if hit else None,
        )
    for i in issues:
        click.secho(f"{i['level']}: {i['message']}", fg="yellow", err=True)
    if failing:
        sys.exit(1)
