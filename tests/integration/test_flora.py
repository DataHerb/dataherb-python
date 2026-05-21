from dataherb.flora import Flora


def test_flora_herbmeta(flora_path):
    id = "git-data-science-job"
    fl = Flora(flora_path=flora_path)

    fl.herb_meta(id)


def test_flora_search(flora_path):
    keyword = "data science"
    fl = Flora(flora_path=flora_path)

    fl.search(keywords=keyword)


def test_flora_herb_by_id(flora_path):
    fl = Flora(flora_path=flora_path)

    hb = fl.herb("git-data-science-job")

    assert hb.id == "git-data-science-job"

    rs = hb.resources[0]

    assert rs.tabular == True

    assert {i.name for i in rs.schema.fields} == {
        "title",
        "location",
        "company",
        "description",
        "salary",
        "url",
        "published_at",
        "id",
    }


def test_flora_search_returns_list(flora_path):
    fl = Flora(flora_path=flora_path)
    results = fl.search("data science")
    assert isinstance(results, list)
    assert len(results) > 0
    assert all("herb" in r for r in results)
    assert all("score" in r for r in results)


def test_flora_herb_meta_unknown_id_returns_none(flora_path):
    fl = Flora(flora_path=flora_path)
    result = fl.herb_meta("this-id-does-not-exist")
    assert result is None


def test_flora_herb_unknown_id_returns_none(flora_path):
    fl = Flora(flora_path=flora_path)
    result = fl.herb("this-id-does-not-exist")
    assert result is None


def test_flora_add_and_remove(flora_path, tmp_path):
    """Adding and then removing a herb leaves the flora in its original state."""
    import shutil

    # Work in a temporary copy so we don't mutate the fixture data
    tmp_flora = tmp_path / "flora"
    shutil.copytree(str(flora_path), str(tmp_flora))

    fl = Flora(flora_path=tmp_flora)
    original_count = len(fl.flora)

    new_herb_meta = {
        "id": "test-new-herb",
        "name": "Test Herb",
        "description": "Temporary test herb",
        "source": "git",
        "uri": "https://github.com/example/test.git",
        "metadata_uri": "https://raw.githubusercontent.com/example/test/main/dataherb.json",
        "datapackage": {"resources": []},
    }
    fl.add(new_herb_meta)
    assert len(fl.flora) == original_count + 1
    assert fl.herb("test-new-herb") is not None

    fl.remove("test-new-herb")
    assert len(fl.flora) == original_count
    assert fl.herb("test-new-herb") is None


def test_flora_accepts_string_path(flora_path):
    """Flora should accept a plain string as flora_path."""
    fl = Flora(flora_path=str(flora_path))
    assert len(fl.flora) > 0


def test_flora_add_duplicate_raises(flora_path, tmp_path):
    """Adding a herb whose id already exists should raise a ValueError."""
    import shutil

    tmp_flora = tmp_path / "flora"
    shutil.copytree(str(flora_path), str(tmp_flora))

    fl = Flora(flora_path=tmp_flora)

    # Try to add a herb with a duplicate ID
    duplicate_meta = {
        "id": "git-data-science-job",
        "name": "Duplicate",
        "description": "",
        "source": "git",
        "uri": "",
        "metadata_uri": "",
        "datapackage": {"resources": []},
    }
    import pytest
    with pytest.raises(ValueError, match="already exists"):
        fl.add(duplicate_meta)

