"""Load dataherb.config.yml and fill defaults."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .util import load_file

DEFAULTS: dict[str, Any] = {
    "site": {
        "title": "DataHerb Explorer",
        "description": "",
        "logo": None,
        "accent": "#2f7d4f",
        "links": [],
        "repository": None,
    },
    "stores": {
        "github": {
            "type": "git",
            "raw_url_template": "https://raw.githubusercontent.com/{repo}/{ref}/{path}",
            "web_url_template": "https://github.com/{repo}",
            "default_ref": "HEAD",
            "token_env": "GITHUB_TOKEN",
        },
        "local": {"type": "local", "path": "demo"},
    },
    "catalog": {"dirs": ["catalog"], "discover": []},
    "status": {"sources": [], "live": True, "stale_grace": 0.5, "history": 30},
    "explorer": {
        "enabled": True,
        "duckdb": {
            "mode": "cdn",
            "version": "1.29.0",
            "cdn_base": "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@{version}",
        },
        "preview_rows": 200,
        "max_browser_bytes": 500_000_000,
    },
    "snippets": [],
}


def _merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        out = dict(base)
        for k, v in override.items():
            out[k] = _merge(base.get(k), v) if k in base else v
        return out
    return copy.deepcopy(override) if override is not None else copy.deepcopy(base)


@dataclass
class Config:
    data: dict
    root: Path

    @property
    def site(self) -> dict:
        return self.data["site"]

    @property
    def stores(self) -> dict:
        return self.data["stores"]

    @property
    def catalog(self) -> dict:
        return self.data["catalog"]

    @property
    def status(self) -> dict:
        return self.data["status"]

    @property
    def explorer(self) -> dict:
        return self.data["explorer"]

    def path(self, p: str) -> Path:
        q = Path(p)
        return q if q.is_absolute() else self.root / q

    def public(self) -> dict:
        """The subset of the config the browser gets. Never includes store credentials."""
        stores = {}
        for name, s in self.stores.items():
            stores[name] = {
                k: v
                for k, v in s.items()
                if k in ("type", "web_url_template", "public_base_url")
            }
        return {
            "site": self.site,
            "stores": stores,
            "status": {k: self.status.get(k) for k in ("live", "stale_grace")},
            "explorer": self.explorer,
            "snippets": self.data.get("snippets", []),
        }


def load_config(path: str | Path = "dataherb.config.yml") -> Config:
    path = Path(path).resolve()
    raw = load_file(path) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected a mapping at the top level")
    # Stores are replaced wholesale when given, so a fork can drop the demo stores.
    data = _merge(DEFAULTS, {k: v for k, v in raw.items() if k != "stores"})
    data["stores"] = raw.get("stores") or copy.deepcopy(DEFAULTS["stores"])
    for name, store in data["stores"].items():
        if not isinstance(store, dict) or "type" not in store:
            raise ValueError(f"store '{name}' needs a type (git, s3, http, local)")
    return Config(data=data, root=path.parent)


def load_config_defaults(root: str | Path = ".") -> Config:
    """A Config with only the defaults, for checking a single dataset outside a catalog."""
    return Config(data=copy.deepcopy(DEFAULTS), root=Path(root).resolve())
