"""
Unit tests for dataherb.parse.model_json.MetaData.
"""
import json
from pathlib import Path

import pytest

from dataherb.parse.model_json import MetaData
from dataherb.parse.utils import STATUS_CODE


@pytest.fixture()
def dataset_dir(tmp_path):
    """Create a minimal dataset folder with a dataherb.json."""
    meta = {
        "id": "test-validate",
        "name": "Test Validate Dataset",
        "source": "git",
        "uri": "https://github.com/example/test.git",
        "metadata_uri": "https://raw.githubusercontent.com/example/test/main/dataherb.json",
        "datapackage": {
            "resources": [
                {
                    "name": "exists_file",
                    "path": "dataset/present.csv",
                    "profile": "tabular-data-resource",
                    "schema": {"fields": [{"name": "col", "type": "string"}]},
                },
                {
                    "name": "missing_file",
                    "path": "dataset/absent.csv",
                    "profile": "tabular-data-resource",
                    "schema": {"fields": [{"name": "col", "type": "string"}]},
                },
            ]
        },
    }
    (tmp_path / "dataherb.json").write_text(json.dumps(meta))
    # Only create the first resource file
    (tmp_path / "dataset").mkdir()
    (tmp_path / "dataset" / "present.csv").write_text("col\nvalue\n")
    return tmp_path


class TestMetaDataLoad:
    def test_load_returns_dict(self, dataset_dir):
        md = MetaData(folder=dataset_dir)
        result = md.load()
        assert isinstance(result, dict)
        assert result["id"] == "test-validate"

    def test_load_missing_file_raises(self, tmp_path):
        md = MetaData(folder=tmp_path)
        with pytest.raises(Exception):
            md.load()


class TestMetaDataValidate:
    def test_validate_returns_data_key(self, dataset_dir):
        md = MetaData(folder=dataset_dir)
        result = md.validate()
        assert "data" in result
        assert isinstance(result["data"], list)

    def test_validate_success_for_existing_file(self, dataset_dir):
        md = MetaData(folder=dataset_dir)
        result = md.validate()
        present_entries = [
            entry
            for entry in result["data"]
            if entry.get("path", {}).get("value") == "dataset/present.csv"
        ]
        assert present_entries, "Expected entry for present.csv"
        assert present_entries[0]["path"]["status"] == STATUS_CODE["SUCCESS"]

    def test_validate_error_for_missing_file(self, dataset_dir):
        md = MetaData(folder=dataset_dir)
        result = md.validate()
        absent_entries = [
            entry
            for entry in result["data"]
            if entry.get("path", {}).get("value") == "dataset/absent.csv"
        ]
        assert absent_entries, "Expected entry for absent.csv"
        assert absent_entries[0]["path"]["status"] == STATUS_CODE["ERROR"]

    def test_validate_raises_when_no_dataherb_json(self, tmp_path):
        md = MetaData(folder=tmp_path)
        with pytest.raises(FileNotFoundError):
            md.validate()

    def test_validate_raises_when_folder_missing(self, tmp_path):
        md = MetaData(folder=tmp_path / "nonexistent")
        with pytest.raises(FileNotFoundError):
            md.validate()


class TestMetaDataCreate:
    def test_create_writes_json_file(self, tmp_path):
        new_dir = tmp_path / "new_dataset"
        new_dir.mkdir()
        md = MetaData(folder=new_dir)
        md.metadata = {"id": "new", "name": "New Dataset"}
        md.create()
        result_file = new_dir / "dataherb.json"
        assert result_file.exists()
        content = json.loads(result_file.read_text())
        assert content["id"] == "new"

    def test_create_raises_if_file_exists_no_overwrite(self, tmp_path):
        (tmp_path / "dataherb.json").write_text("{}")
        md = MetaData(folder=tmp_path)
        md.metadata = {"id": "duplicate"}
        with pytest.raises(FileExistsError):
            md.create(overwrite=False)

    def test_create_overwrites_when_flag_set(self, tmp_path):
        (tmp_path / "dataherb.json").write_text('{"id": "old"}')
        md = MetaData(folder=tmp_path)
        md.metadata = {"id": "new"}
        md.create(overwrite=True)
        content = json.loads((tmp_path / "dataherb.json").read_text())
        assert content["id"] == "new"
