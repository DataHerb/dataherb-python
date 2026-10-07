"""Scaffold dataset metadata from data files.

Uses DuckDB (pip install duckdb) when available, which handles CSV, Parquet
and JSON and gives exact row counts. Falls back to a small CSV sniffer.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .resolve import FORMAT_BY_EXT
from .util import slugify

DATA_EXTS = set(FORMAT_BY_EXT) | {".gz"}

_DUCK_TYPES = {
    "BIGINT": "integer",
    "INTEGER": "integer",
    "SMALLINT": "integer",
    "TINYINT": "integer",
    "HUGEINT": "integer",
    "UBIGINT": "integer",
    "DOUBLE": "number",
    "FLOAT": "number",
    "REAL": "number",
    "BOOLEAN": "boolean",
    "DATE": "date",
    "TIMESTAMP": "datetime",
    "TIMESTAMP WITH TIME ZONE": "datetime",
    "TIME": "time",
    "VARCHAR": "string",
}


def _duck_type(t: str) -> str:
    t = t.upper()
    if t.startswith("DECIMAL"):
        return "number"
    return _DUCK_TYPES.get(t, "string" if "CHAR" in t else "any")


def _with_duckdb(path: Path, fmt: str) -> tuple[list[dict], int] | None:
    try:
        import duckdb  # type: ignore
    except ImportError:
        return None
    reader = {
        "csv": "read_csv_auto",
        "tsv": "read_csv_auto",
        "parquet": "read_parquet",
        "json": "read_json_auto",
        "ndjson": "read_json_auto",
    }.get(fmt)
    if not reader:
        return None
    con = duckdb.connect()
    rel = f"{reader}('{str(path).replace(chr(39), chr(39) * 2)}')"
    cols = con.execute(f"DESCRIBE SELECT * FROM {rel}").fetchall()
    rows = con.execute(f"SELECT count(*) FROM {rel}").fetchone()[0]
    return [
        {"name": c[0], "type": _duck_type(c[1]), "description": ""} for c in cols
    ], int(rows)


def _guess(values: list[str]) -> str:
    vals = [v for v in values if v not in ("", "NA", "null", "NULL")]
    if not vals:
        return "string"
    for typ, conv in (("integer", int), ("number", float)):
        try:
            for v in vals:
                conv(v)
            return typ
        except ValueError:
            continue
    if all(v.lower() in ("true", "false") for v in vals):
        return "boolean"
    return "string"


def _with_csv(path: Path, fmt: str) -> tuple[list[dict], int]:
    delim = "\t" if fmt == "tsv" else ","
    with open(path, newline="", encoding="utf-8", errors="replace") as fp:
        reader = csv.reader(fp, delimiter=delim)
        header: list[str] = next(reader, [])
        sample: list[list[str]] = []
        rows = 0
        for row in reader:
            rows += 1
            if len(sample) < 1000:
                sample.append(row)
    fields = []
    for i, name in enumerate(header):
        col = [r[i] for r in sample if i < len(r)]
        fields.append({"name": name, "type": _guess(col), "description": ""})
    return fields, rows


def describe_file(path: Path, rel: str) -> dict:
    fmt = FORMAT_BY_EXT.get(path.suffix.lower(), path.suffix.lstrip(".").lower())
    res = {
        "name": slugify(path.stem),
        "path": rel,
        "format": fmt,
        "bytes": path.stat().st_size,
        "description": "",
    }
    inferred = _with_duckdb(path, fmt)
    if inferred is None and fmt in ("csv", "tsv"):
        inferred = _with_csv(path, fmt)
    if inferred:
        res["rows"] = inferred[1]
        res["schema"] = {"fields": inferred[0]}
    return res


def scaffold(
    folder: Path, dataset_id: str | None = None, name: str | None = None
) -> dict:
    """Build a dataherb.yml dict for every data file under folder."""
    files = sorted(
        p
        for p in folder.rglob("*")
        if p.is_file()
        and p.suffix.lower() in FORMAT_BY_EXT
        and not any(part.startswith(".") for part in p.relative_to(folder).parts)
    )
    resources = [
        describe_file(p, str(p.relative_to(folder)).replace("\\", "/")) for p in files
    ]
    did = dataset_id or slugify(folder.resolve().name)
    return {
        "spec": "dataherb/v2",
        "id": did,
        "name": name or did.replace("-", " ").replace("_", " ").title(),
        "description": "",
        "owner": {"team": "", "email": ""},
        "tags": [],
        "license": "",
        "classification": "internal",
        "update_frequency": "",
        "status_job": "",
        "datapackage": {"resources": resources},
    }
