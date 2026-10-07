from pathlib import Path

from dataherb.catalog import stores
from dataherb.catalog.stores import S3Store

LISTING = b"""<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Name>lake</Name><IsTruncated>false</IsTruncated>
  <Contents><Key>datasets/a/dataherb.yml</Key></Contents>
  <Contents><Key>datasets/a/a.parquet</Key></Contents>
</ListBucketResult>"""


def test_unsigned_listing_and_urls(monkeypatch):
    seen = []

    def fake_get(url, headers=None, timeout=20.0):
        seen.append(url)
        return LISTING

    monkeypatch.setattr(stores, "http_get", fake_get)
    s = S3Store(
        "lake",
        {"type": "s3", "bucket": "lake", "region": "eu-central-1", "anonymous": True},
        Path("."),
    )
    s._client = False  # force the boto3-free path
    assert s.list("datasets/") == ["datasets/a/dataherb.yml", "datasets/a/a.parquet"]
    assert seen[0].startswith(
        "https://lake.s3.eu-central-1.amazonaws.com/?list-type=2&prefix=datasets%2F"
    )
    assert (
        s.browser_url("datasets/a/a b.parquet")
        == "https://lake.s3.eu-central-1.amazonaws.com/datasets/a/a%20b.parquet"
    )

    cdn = S3Store(
        "lake",
        {
            "type": "s3",
            "bucket": "lake",
            "public_base_url": "https://data.example.com/",
        },
        Path("."),
    )
    assert (
        cdn.browser_url("/datasets/a/a.parquet")
        == "https://data.example.com/datasets/a/a.parquet"
    )

    minio = S3Store(
        "m",
        {"type": "s3", "bucket": "b", "endpoint_url": "https://minio.local"},
        Path("."),
    )
    assert minio.object_url("k/x.csv") == "https://minio.local/b/k/x.csv"
