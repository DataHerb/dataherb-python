"""Storage backends: where metadata, data and status files live.

Every store answers four questions:

- read(key)         -> bytes        (build time; may use credentials)
- list(prefix)      -> [key, ...]   (discovery; not supported for git/http)
- write(key, data)                  (status emitters; local and s3 only)
- browser_url(key)  -> str          (the URL the browser will fetch)
"""

from __future__ import annotations

import posixpath
import shutil
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

from .util import FetchError, env_token, http_get


class StoreError(Exception):
    pass


class Store:
    type = "base"

    def __init__(self, name: str, conf: dict, root: Path):
        self.name = name
        self.conf = conf
        self.root = root

    def read(self, key: str) -> bytes:
        raise NotImplementedError

    def list(self, prefix: str) -> list[str]:
        raise StoreError(f"store '{self.name}' ({self.type}) cannot list files")

    def write(
        self, key: str, data: bytes, content_type: str = "application/json"
    ) -> None:
        raise StoreError(f"store '{self.name}' ({self.type}) is read-only")

    def browser_url(self, key: str) -> str:
        raise NotImplementedError

    def describe(self, key: str) -> str:
        return f"{self.name}:{key}"


class LocalStore(Store):
    """A folder in this repository. Its files are copied into the site under files/<store>/."""

    type = "local"

    @property
    def base(self) -> Path:
        p = Path(self.conf.get("path", "."))
        return p if p.is_absolute() else self.root / p

    def _path(self, key: str) -> Path:
        p = (self.base / key.lstrip("/")).resolve()
        if self.base.resolve() not in p.parents and p != self.base.resolve():
            raise StoreError(f"{key} escapes store '{self.name}'")
        return p

    def read(self, key: str) -> bytes:
        p = self._path(key)
        if not p.is_file():
            raise FetchError(str(p), 404, "not found")
        return p.read_bytes()

    def list(self, prefix: str) -> list[str]:
        base = self._path(prefix)
        if not base.exists():
            return []
        return sorted(
            str(p.relative_to(self.base)).replace("\\", "/")
            for p in base.rglob("*")
            if p.is_file()
        )

    def write(
        self, key: str, data: bytes, content_type: str = "application/json"
    ) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def browser_url(self, key: str) -> str:
        # Relative to the site root; the builder copies the folder there.
        return f"files/{self.name}/{key.lstrip('/')}"

    def publish(self, dist: Path) -> None:
        if self.base.exists():
            shutil.copytree(self.base, dist / "files" / self.name, dirs_exist_ok=True)


class GitStore(Store):
    """A git host reached through raw file URLs (GitHub, GitHub Enterprise, Gitea, GitLab)."""

    type = "git"

    def raw_url(self, repo: str, path: str, ref: str | None = None) -> str:
        tmpl = self.conf.get(
            "raw_url_template", "https://raw.githubusercontent.com/{repo}/{ref}/{path}"
        )
        return tmpl.format(
            repo=repo,
            ref=ref or self.conf.get("default_ref", "HEAD"),
            path=path.lstrip("/"),
        )

    def web_url(self, repo: str) -> str | None:
        tmpl = self.conf.get("web_url_template")
        return tmpl.format(repo=repo) if tmpl else None

    def read(self, key: str) -> bytes:
        # key = "<owner>/<repo>@<ref>:<path>"
        repo, ref, path = parse_git_key(key)
        url = self.raw_url(repo, path, ref)
        token = env_token(self.conf.get("token_env"))
        if not token:
            return http_get(url)
        try:
            return http_get(url, headers={"Authorization": f"token {token}"})
        except FetchError as e:
            # A token scoped to other repos (e.g. Actions' GITHUB_TOKEN) can hide public ones.
            if e.status in (401, 403, 404):
                return http_get(url)
            raise

    def browser_url(self, key: str) -> str:
        repo, ref, path = parse_git_key(key)
        return self.raw_url(repo, path, ref)


def git_key(repo: str, path: str, ref: str | None = None) -> str:
    return f"{repo}@{ref or ''}:{path}"


def parse_git_key(key: str) -> tuple[str, str | None, str]:
    head, _, path = key.partition(":")
    repo, _, ref = head.partition("@")
    return repo, ref or None, path


class HttpStore(Store):
    """Any static file server. Read-only, no listing."""

    type = "http"

    def _url(self, key: str) -> str:
        if key.startswith(("http://", "https://", "file://")):
            return key
        base = self.conf.get("base_url", "")
        return urllib.parse.urljoin(
            base if base.endswith("/") else base + "/", key.lstrip("/")
        )

    def read(self, key: str) -> bytes:
        return http_get(self._url(key))

    def browser_url(self, key: str) -> str:
        return self._url(key)


class S3Store(Store):
    """An S3 or S3-compatible bucket.

    Uses boto3 (with the usual AWS credential chain) when installed. Without
    boto3, or with `anonymous: true`, it falls back to unsigned HTTP requests,
    which works for buckets readable from the build machine's network.
    """

    type = "s3"

    def __init__(self, name: str, conf: dict, root: Path):
        super().__init__(name, conf, root)
        if not conf.get("bucket"):
            raise StoreError(f"s3 store '{name}' needs a bucket")
        self._client = None

    @property
    def bucket(self) -> str:
        return self.conf["bucket"]

    @property
    def region(self) -> str:
        return self.conf.get("region", "us-east-1")

    def client(self):
        if self._client is None:
            try:
                import boto3  # type: ignore
                from botocore import UNSIGNED  # type: ignore
                from botocore.config import Config as BotoConfig  # type: ignore
            except ImportError:
                self._client = False
                return None
            kwargs = {"region_name": self.region}
            if self.conf.get("endpoint_url"):
                kwargs["endpoint_url"] = self.conf["endpoint_url"]
            if self.conf.get("anonymous"):
                kwargs["config"] = BotoConfig(signature_version=UNSIGNED)
            self._client = boto3.client("s3", **kwargs)
        return self._client or None

    def object_url(self, key: str) -> str:
        key = urllib.parse.quote(key.lstrip("/"))
        if self.conf.get("endpoint_url"):
            return f"{self.conf['endpoint_url'].rstrip('/')}/{self.bucket}/{key}"
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"

    def read(self, key: str) -> bytes:
        c = self.client()
        if c is not None:
            try:
                return c.get_object(Bucket=self.bucket, Key=key.lstrip("/"))[
                    "Body"
                ].read()
            except Exception as e:  # botocore raises many types
                raise FetchError(f"s3://{self.bucket}/{key}", None, str(e)) from e
        return http_get(self.object_url(key))

    def list(self, prefix: str) -> list[str]:
        prefix = prefix.lstrip("/")
        c = self.client()
        keys: list[str] = []
        if c is not None:
            for page in c.get_paginator("list_objects_v2").paginate(
                Bucket=self.bucket, Prefix=prefix
            ):
                keys.extend(o["Key"] for o in page.get("Contents", []))
            return keys
        token = None
        while True:
            q = {"list-type": "2", "prefix": prefix}
            if token:
                q["continuation-token"] = token
            base = self.object_url("").rstrip("/")
            body = http_get(f"{base}/?{urllib.parse.urlencode(q)}")
            root = ET.fromstring(body)
            ns = (
                {"s3": root.tag.split("}")[0].strip("{")}
                if root.tag.startswith("{")
                else {}
            )
            find = (
                (lambda el, tag: el.findall(f"s3:{tag}", ns))
                if ns
                else (lambda el, tag: el.findall(tag))
            )
            for c_el in find(root, "Contents"):
                k = find(c_el, "Key")
                if k:
                    keys.append(k[0].text or "")
            trunc = find(root, "IsTruncated")
            nxt = find(root, "NextContinuationToken")
            if trunc and trunc[0].text == "true" and nxt:
                token = nxt[0].text
            else:
                return keys

    def write(
        self, key: str, data: bytes, content_type: str = "application/json"
    ) -> None:
        c = self.client()
        if c is None:
            raise StoreError("writing to S3 needs boto3: pip install 'dataherb[s3]'")
        c.put_object(
            Bucket=self.bucket,
            Key=key.lstrip("/"),
            Body=data,
            ContentType=content_type,
            CacheControl="no-cache, max-age=0",
        )

    def browser_url(self, key: str) -> str:
        key = key.lstrip("/")
        if self.conf.get("presign"):
            c = self.client()
            if c is None:
                raise StoreError("presign needs boto3")
            hours = float(self.conf.get("presign_expiry_hours", 72))
            return c.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=int(hours * 3600),
            )
        if self.conf.get("public_base_url"):
            return (
                f"{self.conf['public_base_url'].rstrip('/')}/{urllib.parse.quote(key)}"
            )
        return self.object_url(key)

    def describe(self, key: str) -> str:
        return f"s3://{self.bucket}/{key.lstrip('/')}"


STORE_TYPES = {"local": LocalStore, "git": GitStore, "http": HttpStore, "s3": S3Store}


def make_stores(conf: dict, root: Path) -> dict[str, Store]:
    out = {}
    for name, sc in conf.items():
        cls = STORE_TYPES.get(sc.get("type"))
        if cls is None:
            raise StoreError(f"store '{name}': unknown type {sc.get('type')!r}")
        out[name] = cls(name, sc, root)
    return out


def join(prefix: str, path: str) -> str:
    if not prefix:
        return path.lstrip("/")
    return posixpath.normpath(posixpath.join(prefix, path)).lstrip("/")
