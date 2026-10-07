import json

from click.testing import CliRunner

from dataherb.command import dataherb

from dataherb.catalog.build import build
from dataherb.catalog.config import load_config


def test_build_writes_site(project):
    cfg = load_config(project / "dataherb.config.yml")
    res = CliRunner().invoke(
        dataherb,
        [
            "status",
            "emit",
            "-c",
            str(project / "dataherb.config.yml"),
            "--job-id",
            "orders-etl",
            "--status",
            "success",
            "--expected-interval",
            "P1D",
            "--dataset",
            "orders:2",
        ],
    )
    assert res.exit_code == 0, res.output
    s = build(cfg, project / "dist")
    assert (project / "dist" / "index.html").exists()
    assert (
        project / "dist" / "files" / "local" / "datasets" / "regions" / "regions.csv"
    ).exists()
    cat = json.loads((project / "dist" / "data" / "catalog.json").read_text())
    orders = next(d for d in cat["datasets"] if d["id"] == "orders")
    assert orders["health"] == "healthy"
    assert orders["updated_at"]
    assert 0 <= orders["quality"]["score"] <= 100
    status = json.loads((project / "dist" / "data" / "status.json").read_text())
    assert (
        status["jobs"][0]["latest_url"] == "files/local/status/orders-etl/latest.json"
    )
    public = json.loads((project / "dist" / "data" / "config.json").read_text())
    assert "raw_url_template" not in json.dumps(
        public["stores"]
    )  # no internals leak to the browser
    assert s.errors == 1  # the broken entry


def test_catalog_validate_lint_check(project):
    cfg = str(project / "dataherb.config.yml")
    runner = CliRunner()
    assert runner.invoke(dataherb, ["catalog", "validate", "-c", cfg]).exit_code == 0
    res = runner.invoke(dataherb, ["catalog", "lint", "-c", cfg])
    assert res.exit_code == 0 and "broken" in res.output
    assert (
        runner.invoke(
            dataherb, ["catalog", "lint", "-c", cfg, "--min-score", "99"]
        ).exit_code
        == 1
    )
    assert (
        runner.invoke(dataherb, ["status", "check", "-c", cfg]).exit_code == 0
    )  # no jobs yet


def test_create_and_validate_dataset(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "orders.csv").write_text("order_id,amount\n1,2.5\n2,3\n")
    runner = CliRunner()
    res = runner.invoke(
        dataherb,
        [
            "create",
            str(tmp_path),
            "--no-input",
            "--no-add-to-flora",
            "--format",
            "yaml",
            "--id",
            "orders",
        ],
    )
    assert res.exit_code == 0, res.output
    meta = (tmp_path / "dataherb.yml").read_text()
    assert "data/orders.csv" in meta and "order_id" in meta
    res = runner.invoke(dataherb, ["validate", str(tmp_path)])
    assert res.exit_code == 0, res.output
    assert "Metadata quality" in res.output
    (tmp_path / "data" / "orders.csv").unlink()
    assert runner.invoke(dataherb, ["validate", str(tmp_path)]).exit_code == 1
