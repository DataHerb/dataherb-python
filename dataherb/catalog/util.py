"""Small helpers shared by the builder: IO, HTTP, time."""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger("dataherb.catalog")

USER_AGENT = "dataherb-python (+https://github.com/DataHerb/dataherb-python)"


def load_structured(text: str | bytes, name: str = "") -> Any:
    """Parse JSON or YAML. JSON is tried first for .json names."""
    if isinstance(text, bytes):
        text = text.decode("utf-8-sig")
    if name.endswith(".json"):
        return json.loads(text)
    return yaml.safe_load(text)


_FRONT_MATTER = re.compile(r"\A---[ \t]*\r?\n(.*?)^(?:---|\.\.\.)[ \t]*(?:\r?\n|\Z)", re.S | re.M)


def split_front_matter(text: str) -> tuple[Any, str]:
    """Split Markdown into (YAML front matter, body). Front matter is None when absent."""
    text = text.lstrip("\ufeff")
    m = _FRONT_MATTER.match(text)
    if not m:
        return None, text
    return yaml.safe_load(m.group(1)), text[m.end() :]


def front_matter_document(data: dict, body: str = "") -> str:
    """Markdown with data as YAML front matter."""
    head = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    return f"---\n{head}---\n" + (f"\n{body.strip()}\n" if body.strip() else "")


def load_file(path: Path) -> Any:
    return load_structured(path.read_text(encoding="utf-8"), path.name)


def dump_json(obj: Any, path: Path, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        if pretty:
            json.dump(obj, fp, indent=2, ensure_ascii=False, default=str)
        else:
            json.dump(obj, fp, separators=(",", ":"), ensure_ascii=False, default=str)


class FetchError(Exception):
    def __init__(self, url: str, status: int | None, reason: str):
        super().__init__(f"{url}: {status or ''} {reason}".strip())
        self.url = url
        self.status = status


def http_get(url: str, headers: dict | None = None, timeout: float = 20.0) -> bytes:
    """GET a URL (http, https or file). Raises FetchError."""
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, **(headers or {})}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise FetchError(url, e.code, e.reason) from e
    except (urllib.error.URLError, OSError) as e:
        raise FetchError(url, None, str(getattr(e, "reason", e))) from e


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso(ts: dt.datetime | None) -> str | None:
    if ts is None:
        return None
    return ts.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: Any) -> dt.datetime | None:
    if not value:
        return None
    if isinstance(value, dt.datetime):
        ts = value
    else:
        s = str(value).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            ts = dt.datetime.fromisoformat(s)
        except ValueError:
            return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    return ts


_DURATION = re.compile(
    r"^P(?:(?P<years>\d+)Y)?(?:(?P<months>\d+)M)?(?:(?P<weeks>\d+)W)?(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$"
)

_FREQUENCY_ALIASES = {
    "hourly": "PT1H",
    "daily": "P1D",
    "weekly": "P1W",
    "monthly": "P31D",
    "quarterly": "P92D",
    "yearly": "P366D",
    "annually": "P366D",
}


def parse_duration(value: Any) -> dt.timedelta | None:
    """ISO 8601 duration (or hourly/daily/... alias) to timedelta. Months = 30 days, years = 365."""
    if not value:
        return None
    s = str(value).strip()
    s = _FREQUENCY_ALIASES.get(s.lower(), s)
    m = _DURATION.match(s)
    if not m or s == "P":
        return None
    g = {k: float(v) if v else 0.0 for k, v in m.groupdict().items()}
    return dt.timedelta(
        days=g["years"] * 365 + g["months"] * 30 + g["weeks"] * 7 + g["days"],
        hours=g["hours"],
        minutes=g["minutes"],
        seconds=g["seconds"],
    )


def env_token(name: str | None) -> str | None:
    return os.environ.get(name) if name else None


def slugify(value: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-").lower()
    return s or "dataset"
