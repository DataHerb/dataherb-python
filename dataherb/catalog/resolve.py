"""Turn catalog entries and discovered metadata files into normalized dataset records."""

from __future__ import annotations

import posixpath
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import Config
from .stores import (
    GitStore,
    HttpStore,
    LocalStore,
    S3Store,
    Store,
    StoreError,
    git_key,
    join,
    make_stores,
)
from .util import (
    FetchError,
    iso,
    load_file,
    load_structured,
    log,
    split_front_matter,
    utcnow,
)

METADATA_CANDIDATES = (
    "dataherb.json",
    "dataherb.yml",
    "dataherb.yaml",
    ".dataherb/metadata.yml",
)

# Catalog entry files. Markdown entries keep the fields in YAML front matter
# and free text (shown on the dataset page) in the body.
ENTRY_SUFFIXES = (".md", ".yml", ".yaml", ".json")

# Keys in a catalog entry that say where the dataset is, rather than describe it.
LOCATOR_KEYS = {
    "store",
    "repo",
    "ref",
    "prefix",
    "url",
    "metadata_path",
    "inline",
    "hidden",
    "_file",
    "_body",
}

FORMAT_BY_EXT = {
    ".csv": "csv",
    ".tsv": "tsv",
    ".parquet": "parquet",
    ".pq": "parquet",
    ".json": "json",
    ".ndjson": "ndjson",
    ".jsonl": "ndjson",
    ".xlsx": "xlsx",
    ".geojson": "geojson",
}


@dataclass
class Located:
    """Where a dataset lives: a store plus a base inside it."""

    store: Store
    base: str = ""  # prefix (local, s3, http) or repo (git)
    ref: str | None = None

    def key(self, path: str) -> str:
        if isinstance(self.store, GitStore):
            return git_key(self.base, path.lstrip("/"), self.ref)
        return join(self.base, path)

    def location(self) -> str:
        if isinstance(self.store, GitStore):
            return f"{self.base}" + (f"@{self.ref}" if self.ref else "")
        if isinstance(self.store, S3Store):
            return f"s3://{self.store.bucket}/{self.base.lstrip('/')}"
        if isinstance(self.store, HttpStore):
            return self.store.browser_url(self.base)
        return f"{self.store.name}:{self.base}"

    def web_url(self) -> str | None:
        if isinstance(self.store, GitStore):
            return self.store.web_url(self.base)
        return None


@dataclass
class BuildIssue:
    level: str  # error | warning
    dataset: str | None
    message: str

    def as_dict(self) -> dict:
        return {"level": self.level, "dataset": self.dataset, "message": self.message}


@dataclass
class CatalogResult:
    datasets: list[dict] = field(default_factory=list)
    issues: list[BuildIssue] = field(default_factory=list)


def load_entries(cfg: Config) -> tuple[list[dict], list[BuildIssue]]:
    entries, issues = [], []
    for d in cfg.catalog.get("dirs", []):
        folder = cfg.path(d)
        if not folder.exists():
            issues.append(
                BuildIssue("warning", None, f"catalog dir {d} does not exist")
            )
            continue
        for p in sorted(folder.rglob("*")):
            if p.suffix not in ENTRY_SUFFIXES or p.name.startswith("_"):
                continue
            body = ""
            try:
                if p.suffix == ".md":
                    data, body = split_front_matter(p.read_text(encoding="utf-8"))
                    if data is None:  # a README or notes, not an entry
                        continue
                    data = data or {}
                else:
                    data = load_file(p)
            except Exception as e:
                issues.append(
                    BuildIssue(
                        "error", None, f"{p.relative_to(cfg.root)}: cannot parse ({e})"
                    )
                )
                continue
            # flora v1 files are a one-element list
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    issues.append(
                        BuildIssue(
                            "error",
                            None,
                            f"{p.relative_to(cfg.root)}: expected a mapping",
                        )
                    )
                    continue
                item = dict(item)
                item["_file"] = str(p.relative_to(cfg.root)).replace("\\", "/")
                if body.strip():
                    item["_body"] = body.strip()
                if "id" not in item:
                    item["id"] = p.stem
                entries.append(item)
    return entries, issues


def locate(entry: dict, stores: dict[str, Store]) -> Located:
    name = entry.get("store")
    if name:
        if name not in stores:
            raise StoreError(f"unknown store '{name}'")
        store = stores[name]
    elif entry.get("repo") or entry.get("repository"):
        git_stores: list[Store] = [
            s for s in stores.values() if isinstance(s, GitStore)
        ]
        store = git_stores[0] if git_stores else GitStore("github", {}, Path("."))
    elif entry.get("url"):
        store = HttpStore("http", {"base_url": ""}, Path("."))
    else:
        local_stores: list[Store] = [
            s for s in stores.values() if isinstance(s, LocalStore)
        ]
        if not local_stores:
            raise StoreError("entry has no store, repo or url")
        store = local_stores[0]
    if isinstance(store, GitStore):
        return Located(
            store, str(entry.get("repo") or entry.get("repository")), entry.get("ref")
        )
    if isinstance(store, HttpStore):
        return Located(store, str(entry.get("url") or entry.get("prefix", "")))
    return Located(store, str(entry.get("prefix", "")))


def fetch_metadata(loc: Located, metadata_path: str | None) -> tuple[dict, str]:
    candidates = [metadata_path] if metadata_path else list(METADATA_CANDIDATES)
    last: Exception | None = None
    for c in candidates:
        try:
            raw = loc.store.read(loc.key(c))
        except FetchError as e:
            last = e
            if e.status not in (404, None) and metadata_path is None:
                break
            continue
        data = load_structured(raw, c)
        if not isinstance(data, dict):
            raise ValueError(f"{c} is not a mapping")
        if c.startswith(".dataherb/"):
            data = from_legacy(data)
        return data, c
    raise FetchError(
        loc.location(),
        getattr(last, "status", None),
        f"no metadata file found ({last})",
    )


def from_legacy(meta: dict) -> dict:
    """Convert the original flora `.dataherb/metadata.yml` format."""
    resources = []
    for d in meta.get("data") or []:
        resources.append(
            {
                "name": d.get("name"),
                "path": d.get("path"),
                "description": d.get("description"),
                "format": d.get("format"),
                "schema": {"fields": d.get("fields") or []},
            }
        )
    out = {k: v for k, v in meta.items() if k not in ("data",)}
    out["datapackage"] = {"resources": resources}
    contributors = meta.get("contributors") or []
    if contributors and not meta.get("owner"):
        out["owner"] = {"name": contributors[0].get("name")}
    refs = meta.get("references") or []
    if refs and not meta.get("documentation"):
        out["documentation"] = "\n".join(
            f"- [{r.get('name')}]({r.get('link')})" for r in refs
        )
    return out


def _owner(value: Any) -> dict | None:
    if not value:
        return None
    if isinstance(value, str):
        return {"email": value} if "@" in value else {"name": value}
    if isinstance(value, dict):
        return {
            k: value.get(k) for k in ("name", "team", "email", "url") if value.get(k)
        }
    return None


def _as_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def resource_format(res: dict) -> str:
    fmt = (res.get("format") or "").lower()
    if fmt:
        return fmt
    path = (res.get("path") or "").lower()
    for comp in (".gz", ".zst", ".bz2"):
        if path.endswith(comp):
            path = path[: -len(comp)]
    return FORMAT_BY_EXT.get(posixpath.splitext(path)[1], "")


def resource_url(
    path: str | None, loc: Located | None, stores: dict[str, Store]
) -> str | None:
    if not path:
        return None
    if path.startswith(("http://", "https://")):
        return path
    if path.startswith("s3://"):
        bucket, _, key = path[5:].partition("/")
        for s in stores.values():
            if isinstance(s, S3Store) and s.bucket == bucket:
                return s.browser_url(key)
        return f"https://{bucket}.s3.amazonaws.com/{key}"
    if loc is None:
        return None
    return loc.store.browser_url(loc.key(path))


def normalize(
    meta: dict, entry: dict, loc: Located | None, stores: dict[str, Store], cfg: Config
) -> dict:
    """Merge remote metadata with catalog overrides into the record the site renders."""
    merged = {**meta, **{k: v for k, v in entry.items() if k not in LOCATOR_KEYS}}
    resources = []
    for i, r in enumerate(
        (merged.get("datapackage") or {}).get("resources")
        or merged.get("resources")
        or []
    ):
        if not isinstance(r, dict):
            continue
        path = r.get("path")
        if isinstance(
            path, list
        ):  # frictionless allows multi-part paths; take the first
            path = path[0] if path else None
        fields = []
        for f in (r.get("schema") or {}).get("fields") or []:
            if isinstance(f, dict) and f.get("name"):
                fields.append(
                    {
                        k: f.get(k)
                        for k in ("name", "type", "description", "unit", "example")
                        if f.get(k) not in (None, "")
                    }
                )
        try:
            url = resource_url(path, loc, stores)
        except StoreError as e:
            url = None
            log.warning("%s: %s", merged.get("id"), e)
        resources.append(
            {
                "name": r.get("name")
                or (posixpath.basename(path) if path else f"resource-{i}"),
                "title": r.get("title"),
                "description": r.get("description"),
                "path": path,
                "url": url,
                "format": resource_format({**r, "path": path}),
                "bytes": r.get("bytes"),
                "rows": r.get("rows"),
                "fields": fields,
                "primary_key": (r.get("schema") or {}).get("primaryKey"),
            }
        )
    repo_url = cfg.site.get("repository")
    entry_file = entry.get("_file")
    return {
        "id": str(merged.get("id")),
        "name": merged.get("name") or merged.get("title") or str(merged.get("id")),
        "description": merged.get("description") or "",
        "documentation": "\n\n".join(
            x for x in (entry.get("_body"), merged.get("documentation")) if x
        ),
        "tags": sorted({str(t) for t in _as_list(merged.get("tags")) if t}),
        "domain": merged.get("domain"),
        "owner": _owner(merged.get("owner")),
        "license": merged.get("license"),
        "classification": merged.get("classification"),
        "update_frequency": merged.get("update_frequency"),
        "status_jobs": [
            str(j)
            for j in _as_list(merged.get("status_job") or merged.get("status_jobs"))
        ],
        "temporal_coverage": merged.get("temporal_coverage"),
        "related": _as_list(merged.get("related")),
        "source": loc.store.type if loc else (merged.get("source") or "inline"),
        "store": loc.store.name if loc else None,
        "location": loc.location() if loc else merged.get("uri"),
        "web_url": (loc.web_url() if loc else None)
        or merged.get("homepage")
        or merged.get("uri"),
        "edit_url": f"{repo_url.rstrip('/')}/blob/main/{entry_file}"
        if repo_url and entry_file
        else None,
        "catalog_file": entry_file,
        "spec": merged.get("spec")
        or ("dataherb/v1" if "datapackage" in meta else None),
        "resources": resources,
        "hidden": bool(entry.get("hidden")),
    }


def resolve_entry(
    entry: dict, stores: dict[str, Store], cfg: Config
) -> tuple[dict, list[BuildIssue]]:
    issues: list[BuildIssue] = []
    did = str(entry.get("id"))
    loc = None
    meta: dict = {}
    error = None
    try:
        if entry.get("inline"):
            loc = (
                locate(entry, stores)
                if any(entry.get(k) for k in ("store", "repo", "url", "prefix"))
                else None
            )
        else:
            loc = locate(entry, stores)
            meta, _ = fetch_metadata(loc, entry.get("metadata_path"))
            if meta.get("id") and str(meta["id"]) != did:
                issues.append(
                    BuildIssue(
                        "warning",
                        did,
                        f"metadata id '{meta['id']}' differs from catalog id; using '{did}'",
                    )
                )
    except (FetchError, StoreError, ValueError) as e:
        error = str(e)
        issues.append(BuildIssue("error", did, f"metadata unavailable: {e}"))
    record = normalize(meta, entry, loc, stores, cfg)
    record["id"] = did
    record["error"] = error
    record["fetched_at"] = iso(utcnow())
    return record, issues


def discover(
    cfg: Config, stores: dict[str, Store]
) -> tuple[list[dict], list[BuildIssue]]:
    entries, issues = [], []
    names = ("dataherb.json", "dataherb.yml", "dataherb.yaml")
    for d in cfg.catalog.get("discover") or []:
        store = stores.get(d.get("store"))
        if store is None:
            issues.append(
                BuildIssue("error", None, f"discover: unknown store '{d.get('store')}'")
            )
            continue
        try:
            keys = store.list(d.get("prefix", ""))
        except (FetchError, StoreError) as e:
            issues.append(
                BuildIssue(
                    "error", None, f"discover {store.name}:{d.get('prefix', '')}: {e}"
                )
            )
            continue
        for key in keys:
            if posixpath.basename(key) not in names:
                continue
            prefix = posixpath.dirname(key)
            try:
                meta = load_structured(store.read(key), key)
            except Exception as e:
                issues.append(BuildIssue("error", None, f"{store.describe(key)}: {e}"))
                continue
            did = (meta or {}).get("id") or posixpath.basename(prefix)
            entries.append(
                {
                    "id": str(did),
                    "store": store.name,
                    "prefix": prefix,
                    "metadata_path": posixpath.basename(key),
                }
            )
    return entries, issues


def build_catalog(cfg: Config, workers: int = 8) -> CatalogResult:
    stores = make_stores(cfg.stores, cfg.root)
    result = CatalogResult()
    entries, issues = load_entries(cfg)
    result.issues.extend(issues)
    found, issues = discover(cfg, stores)
    result.issues.extend(issues)

    by_id: dict[str, dict] = {}
    for e in (
        found + entries
    ):  # catalog entries override discovered ones with the same id
        if e["id"] in by_id and "_file" in by_id[e["id"]] and "_file" in e:
            result.issues.append(
                BuildIssue(
                    "error",
                    e["id"],
                    f"duplicate id in {by_id[e['id']]['_file']} and {e['_file']}",
                )
            )
            continue
        by_id[e["id"]] = {**by_id.get(e["id"], {}), **e}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for record, issues in pool.map(
            lambda e: resolve_entry(e, stores, cfg), by_id.values()
        ):
            result.datasets.append(record)
            result.issues.extend(issues)
    result.datasets.sort(key=lambda d: d["name"].lower())
    return result
