"""
CLI regression tests using click's CliRunner.

These tests exercise the CLI layer without touching the network or requiring a
configured ``~/.dataherb/config.json`` file.
"""
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from dataherb.command import dataherb


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def flora_path():
    """Path to the demo flora used across integration tests."""
    return (
        Path(__file__).parent.parent
        / "integration"
        / "data"
        / "demo-flora"
    )


# ---------------------------------------------------------------------------
# version command
# ---------------------------------------------------------------------------

def test_version_command():
    runner = CliRunner()
    result = runner.invoke(dataherb, ["version"])
    assert result.exit_code == 0
    assert "dataherb version" in result.output


# ---------------------------------------------------------------------------
# search command
# ---------------------------------------------------------------------------

def test_search_by_keyword(flora_path):
    runner = CliRunner()
    result = runner.invoke(
        dataherb,
        ["search", "--flora", str(flora_path), "data science"],
    )
    assert result.exit_code == 0
    assert "git-data-science-job" in result.output


def test_search_by_id(flora_path):
    runner = CliRunner()
    result = runner.invoke(
        dataherb,
        ["search", "--flora", str(flora_path), "--id", "git-data-science-job"],
    )
    assert result.exit_code == 0
    assert "git-data-science-job" in result.output


def test_search_not_found(flora_path):
    runner = CliRunner()
    result = runner.invoke(
        dataherb,
        ["search", "--flora", str(flora_path), "zzznomatch"],
    )
    assert result.exit_code == 0
    assert "0 results" in result.output or "Could not find" in result.output


def test_search_by_id_full(flora_path):
    runner = CliRunner()
    result = runner.invoke(
        dataherb,
        [
            "search",
            "--flora",
            str(flora_path),
            "--id",
            "git-data-science-job",
            "--full",
        ],
    )
    assert result.exit_code == 0
    assert "git-data-science-job" in result.output


# ---------------------------------------------------------------------------
# validate command
# ---------------------------------------------------------------------------

def test_validate_missing_dataherb_json(tmp_path):
    """validate should emit an error when dataherb.json is absent."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(dataherb, ["validate"])
    # Should exit with non-zero or print an error message; must not raise
    # an unhandled exception (exit_code 1 from ClickException is acceptable).
    assert result.exit_code in (0, 1)
    # No raw Python tracebacks
    assert "Traceback" not in result.output


def test_validate_with_valid_dataherb_json(tmp_path):
    """validate should succeed and print a summary when dataherb.json exists."""
    metadata = {
        "id": "test-dataset",
        "name": "Test Dataset",
        "source": "git",
        "uri": "https://github.com/example/test.git",
        "metadata_uri": "https://raw.githubusercontent.com/example/test/main/dataherb.json",
        "datapackage": {
            "resources": [
                {
                    "name": "data",
                    "path": "dataset/data.csv",
                    "profile": "tabular-data-resource",
                    "schema": {"fields": [{"name": "col", "type": "string"}]},
                }
            ]
        },
    }
    dj = tmp_path / "dataherb.json"
    dj.write_text(json.dumps(metadata))

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import os
        os.chdir(tmp_path)
        result = runner.invoke(dataherb, ["validate"])

    assert result.exit_code == 0
    assert "Summary" in result.output


# ---------------------------------------------------------------------------
# upload command – abort path
# ---------------------------------------------------------------------------

def test_upload_aborts_on_no(tmp_path):
    """upload should exit cleanly when the user declines the confirmation."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import os
        os.chdir(tmp_path)
        result = runner.invoke(dataherb, ["upload"], input="n\n")
    assert result.exit_code == 0
    assert "aborted" in result.output.lower()


# ---------------------------------------------------------------------------
# Flora Flora string path acceptance
# ---------------------------------------------------------------------------

def test_flora_accepts_string_path(flora_path):
    """Flora should accept a plain str in addition to pathlib.Path."""
    from dataherb.flora import Flora

    fl = Flora(flora_path=str(flora_path))
    assert len(fl.flora) > 0
