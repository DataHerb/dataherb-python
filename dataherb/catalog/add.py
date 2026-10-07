"""Add git repositories to the catalog as entries in catalog/.

Entries are Markdown files: the fields go in the YAML front matter and the
body is free text shown on the dataset page.

A repo that already carries metadata (dataherb.json, dataherb.yml or the
legacy .dataherb/metadata.yml) gets a short pointer entry; the builder reads
the metadata on every build. A repo without metadata is cloned and scanned
like `dataherb create` does, and gets an inline entry with the inferred
resources, so it shows up in the catalog without touching the data repo.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import yaml

from .config import Config
from .infer import scaffold
from .resolve import METADATA_CANDIDATES, load_entries
from .stores import GitStore, StoreError, git_key, make_stores
from .util import (
    FetchError,
    env_token,
    front_matter_document,
    http_get,
    slugify,
    split_front_matter,
)


@dataclass
class Added:
    repo: str
    id: str
    path: Path | None
    kind: str  # pointer | inline | skipped
    note: str = ""


def list_org_repos(
    org: str,
    match: str = "",
    api_url: str = "https://api.github.com",
    token: str | None = None,
    include_archived: bool = False,
) -> list[str]:
    """owner/name of every repo of a GitHub org (or user) whose name starts with match."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    api = api_url.rstrip("/")
    repos: list[dict] = []
    for kind in ("orgs", "users"):
        repos, page = [], 1
        try:
            while True:
                raw = http_get(
                    f"{api}/{kind}/{quote(org)}/repos?per_page=100&type=all&page={page}",
                    headers=headers,
                )
                batch = json.loads(raw)
                repos.extend(batch)
                if len(batch) < 100:
                    break
                page += 1
            break
        except FetchError as e:
            if e.status == 404 and kind == "orgs":
                continue
            raise
    return sorted(
        r["full_name"]
        for r in repos
        if r["name"].lower().startswith(match.lower())
        and (include_archived or not r.get("archived"))
    )


def default_id(repo: str, strip_prefix: str = "") -> str:
    name = repo.split("/")[-1]
    if strip_prefix and name.lower().startswith(strip_prefix.lower()):
        name = name[len(strip_prefix) :].lstrip("-_.") or name
    return slugify(name)


def _remote_metadata(store: GitStore, repo: str, ref: str | None) -> str | None:
    for c in METADATA_CANDIDATES:
        try:
            store.read(git_key(repo, c, ref))
            return c
        except FetchError:
            continue
    return None


def _clone(url: str, ref: str | None, dest: Path) -> None:
    cmd = ["git", "clone", "--quiet", "--depth", "1"]
    if ref and ref != "HEAD":
        cmd += ["--branch", ref]
    subprocess.run(cmd + [url, str(dest)], check=True, capture_output=True, text=True)


def add_repos(
    cfg: Config,
    repos: list[str],
    store_name: str | None = None,
    ref: str | None = None,
    strip_prefix: str = "",
    tags: tuple[str, ...] = (),
    clone_url_template: str | None = None,
    force: bool = False,
    dry_run: bool = False,
    fmt: str = "md",
) -> list[Added]:
    stores = make_stores(cfg.stores, cfg.root)
    git_stores = {n: s for n, s in stores.items() if isinstance(s, GitStore)}
    if store_name:
        if store_name not in git_stores:
            raise StoreError(f"'{store_name}' is not a git store in the config")
        store = git_stores[store_name]
    elif git_stores:
        store_name, store = next(iter(git_stores.items()))
    else:
        raise StoreError("the config has no store of type git")

    dirs = cfg.catalog.get("dirs") or ["catalog"]
    out_dir = cfg.path(dirs[0])
    entries, _ = load_entries(cfg)
    known_repos = {
        str(e.get("repo") or e.get("repository")).lower(): e
        for e in entries
        if e.get("repo") or e.get("repository")
    }
    known_ids = {str(e["id"]) for e in entries}
    clone_tmpl = clone_url_template or (
        store.conf.get("web_url_template", "https://github.com/{repo}") + ".git"
    )
    # Only one git store: entries can leave `store` out and still resolve to it.
    explicit_store = len(git_stores) > 1

    results = []
    for repo in repos:
        repo = repo.strip().strip("/")
        if repo.count("/") != 1:
            results.append(Added(repo, "", None, "skipped", "expected owner/name"))
            continue
        existing = known_repos.get(repo.lower())
        if existing and not force:
            results.append(
                Added(
                    repo,
                    str(existing["id"]),
                    cfg.path(existing["_file"]),
                    "skipped",
                    f"already in {existing['_file']}",
                )
            )
            continue
        did = str(existing["id"]) if existing else default_id(repo, strip_prefix)
        target = (
            cfg.path(existing["_file"]) if existing else out_dir / f"{did}.{fmt}"
        )
        if not existing and (did in known_ids or target.exists()) and not force:
            results.append(
                Added(repo, did, target, "skipped", f"id '{did}' is already taken")
            )
            continue

        entry: dict = {"id": did}
        if explicit_store:
            entry["store"] = store_name
        entry["repo"] = repo
        if ref:
            entry["ref"] = ref

        found = _remote_metadata(store, repo, ref)
        inferred = None
        if found is None:
            # Not readable over raw URLs (no metadata, or a private repo without a
            # token): look at a shallow clone, which uses the local git credentials.
            with tempfile.TemporaryDirectory() as tmp:
                dest = Path(tmp) / "repo"
                try:
                    _clone(clone_tmpl.format(repo=repo), ref, dest)
                except subprocess.CalledProcessError as e:
                    results.append(
                        Added(
                            repo,
                            did,
                            None,
                            "skipped",
                            f"cannot clone: {(e.stderr or '').strip()}",
                        )
                    )
                    continue
                found = next((c for c in METADATA_CANDIDATES if (dest / c).exists()), None)
                if found is None:
                    inferred = scaffold(dest, dataset_id=did)

        if inferred is not None:
            entry["inline"] = True
            for k in ("name", "description", "datapackage"):
                entry[k] = inferred[k]
            kind, note = "inline", f"no metadata in the repo; inferred {len(inferred['datapackage']['resources'])} resource(s)"
        else:
            kind, note = "pointer", f"reads {found}"
        if tags:
            entry["tags"] = list(tags)

        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.suffix == ".md":
                text = front_matter_document(entry, _keep_body(target) if force else "")
            else:
                text = yaml.safe_dump(entry, sort_keys=False, allow_unicode=True)
            target.write_text(text, encoding="utf-8")
        known_ids.add(did)
        known_repos[repo.lower()] = {"id": did, "_file": str(target)}
        results.append(Added(repo, did, target, kind, note))
    return results


def _keep_body(path: Path) -> str:
    """The Markdown body of an entry that is being overwritten, so --force keeps hand-written notes."""
    if not path.exists():
        return ""
    return split_front_matter(path.read_text(encoding="utf-8"))[1]


def org_token(cfg: Config, store_name: str | None) -> str | None:
    for name, conf in (cfg.stores or {}).items():
        if conf.get("type") == "git" and (store_name in (None, name)):
            return env_token(conf.get("token_env"))
    return None
