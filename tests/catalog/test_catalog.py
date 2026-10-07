from dataherb.catalog.resolve import build_catalog
from dataherb.catalog.config import load_config


def by_id(result):
    return {d["id"]: d for d in result.datasets}


def test_git_local_inline_and_legacy(project):
    res = build_catalog(load_config(project / "dataherb.config.yml"))
    ds = by_id(res)
    assert set(ds) == {"orders", "legacy", "regions", "broken", "inline-ds"}

    orders = ds["orders"]
    assert orders["source"] == "git"
    assert orders["tags"] == ["sales"]  # catalog override
    assert orders["status_jobs"] == ["orders-etl"]
    assert orders["resources"][0]["url"].endswith(
        "/git/acme/orders/main/data/orders.csv"
    )
    assert orders["resources"][0]["format"] == "csv"
    assert orders["web_url"] == "https://github.com/acme/orders"
    assert (
        orders["edit_url"]
        == "https://github.com/acme/catalog/blob/main/catalog/orders.yml"
    )

    legacy = ds["legacy"]
    assert legacy["resources"][0]["fields"] == [{"name": "x", "description": "the x"}]

    regions = ds["regions"]
    assert regions["resources"][0]["url"] == "files/local/datasets/regions/regions.csv"

    assert ds["inline-ds"]["resources"][0]["url"] == "https://example.com/x.parquet"
    assert ds["inline-ds"]["resources"][0]["format"] == "parquet"

    assert ds["broken"]["error"]
    assert any(i.dataset == "broken" and i.level == "error" for i in res.issues)


def test_discovered_and_catalog_entries_merge(project):
    res = build_catalog(load_config(project / "dataherb.config.yml"))
    # regions is both discovered (datasets/regions/dataherb.yml) and listed: one record.
    assert [d["id"] for d in res.datasets].count("regions") == 1
