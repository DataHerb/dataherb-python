"""JSON Schema validation for config, catalog entries, dataset metadata and status files."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any


@lru_cache(maxsize=None)
def schema(name: str) -> dict:
    return json.loads(
        resources.files("dataherb.catalog")
        .joinpath("schemas")
        .joinpath(f"{name}.schema.json")
        .read_text()
    )


def errors(name: str, doc: Any) -> list[str]:
    """Return human-readable validation errors ([] when valid)."""
    try:
        import jsonschema  # type: ignore
    except ImportError:  # validation is best effort without jsonschema
        return []
    validator = jsonschema.Draft202012Validator(schema(name))
    out = []
    for e in sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path)):
        where = "/".join(str(p) for p in e.absolute_path) or "(root)"
        out.append(f"{where}: {e.message}")
    return out
