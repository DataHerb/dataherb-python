import json
import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A self-contained fork: a git store served from file://, a local store and catalog entries."""
    # Fake git host: <tmp>/git/<owner>/<repo>/<ref>/<path>
    repo = tmp_path / "git" / "acme" / "orders" / "main"
    (repo / "data").mkdir(parents=True)
    (repo / "data" / "orders.csv").write_text(
        "order_id,region,amount\n1,DE,10.5\n2,FR,3\n"
    )
    (repo / "dataherb.json").write_text(
        json.dumps(
            {
                "id": "orders",
                "name": "Orders",
                "description": "All orders placed in the web shop, one row per order.",
                "datapackage": {
                    "resources": [
                        {
                            "name": "orders",
                            "path": "data/orders.csv",
                            "schema": {
                                "fields": [{"name": "order_id", "type": "integer"}]
                            },
                        }
                    ]
                },
            }
        )
    )
    legacy = tmp_path / "git" / "acme" / "legacy" / "main" / ".dataherb"
    legacy.mkdir(parents=True)
    (legacy / "metadata.yml").write_text(
        textwrap.dedent(
            """
            name: Legacy
            description: old style
            data:
              - name: a
                path: dataset/a.csv
                format: csv
                fields:
                  - name: x
                    description: the x
            """
        )
    )

    local = tmp_path / "demo" / "datasets" / "regions"
    local.mkdir(parents=True)
    (local / "regions.csv").write_text("code,name\nDE,Germany\n")
    (local / "dataherb.yml").write_text(
        "id: regions\nname: Regions\ndatapackage:\n  resources:\n    - path: regions.csv\n"
    )

    cat = tmp_path / "catalog"
    cat.mkdir()
    (cat / "orders.yml").write_text(
        "id: orders\nrepo: acme/orders\nref: main\ntags: [sales]\nstatus_job: orders-etl\n"
    )
    (cat / "legacy.yml").write_text("id: legacy\nrepo: acme/legacy\nref: main\n")
    (cat / "regions.yml").write_text(
        "id: regions\nstore: local\nprefix: datasets/regions\n"
    )
    (cat / "broken.yml").write_text("id: broken\nrepo: acme/missing\nref: main\n")
    (cat / "_ignored.yml").write_text("id: nope\n")
    (cat / "inline.yml").write_text(
        "id: inline-ds\ninline: true\nname: Inline\nresources:\n  - path: https://example.com/x.parquet\n"
    )

    (tmp_path / "dataherb.config.yml").write_text(
        textwrap.dedent(
            f"""
            site:
              title: Test
              repository: https://github.com/acme/catalog
            stores:
              github:
                type: git
                raw_url_template: "file://{tmp_path}/git/{{repo}}/{{ref}}/{{path}}"
                web_url_template: "https://github.com/{{repo}}"
              local:
                type: local
                path: demo
            catalog:
              dirs: [catalog]
              discover:
                - store: local
                  prefix: datasets
            status:
              sources:
                - store: local
                  prefix: status
            """
        )
    )
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "index.html").write_text("<!doctype html>")
    return tmp_path
