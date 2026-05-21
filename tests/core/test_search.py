"""
Unit tests for dataherb.core.search functions.
"""
from pathlib import Path

import pytest

from dataherb.core.base import Herb
from dataherb.core.search import search_by_ids_in_flora, search_by_keywords_in_flora

# ---------------------------------------------------------------------------
# Minimal fixture data – a small synthetic flora so tests stay offline
# ---------------------------------------------------------------------------

_HERB_META_A = {
    "id": "geo-nuts",
    "name": "EU NUTS Regions",
    "description": "Geographic boundaries of EU NUTS regions",
    "source": "git",
    "uri": "https://github.com/example/geo-nuts.git",
    "metadata_uri": "https://raw.githubusercontent.com/example/geo-nuts/main/dataherb.json",
    "datapackage": {
        "resources": [
            {
                "name": "nuts",
                "path": "dataset/nuts.csv",
                "profile": "tabular-data-resource",
                "schema": {"fields": [{"name": "id", "type": "string"}]},
            }
        ]
    },
}

_HERB_META_B = {
    "id": "climate-co2",
    "name": "Global CO2 Levels",
    "description": "Monthly atmospheric CO2 concentration",
    "source": "git",
    "uri": "https://github.com/example/climate-co2.git",
    "metadata_uri": "https://raw.githubusercontent.com/example/climate-co2/main/dataherb.json",
    "datapackage": {
        "resources": [
            {
                "name": "co2",
                "path": "dataset/co2.csv",
                "profile": "tabular-data-resource",
                "schema": {"fields": [{"name": "date", "type": "string"}, {"name": "ppm", "type": "number"}]},
            }
        ]
    },
}


@pytest.fixture()
def synthetic_flora(tmp_path):
    """Return a small list of Herb objects (no network access required)."""
    return [
        Herb(_HERB_META_A, base_path=tmp_path / "geo-nuts", with_resources=False),
        Herb(_HERB_META_B, base_path=tmp_path / "climate-co2", with_resources=False),
    ]


# ---------------------------------------------------------------------------
# search_by_ids_in_flora
# ---------------------------------------------------------------------------

class TestSearchByIds:
    def test_finds_existing_id_as_string(self, synthetic_flora):
        results = search_by_ids_in_flora(synthetic_flora, "geo-nuts")
        assert len(results) == 1
        assert results[0]["id"] == "geo-nuts"

    def test_finds_existing_id_as_list(self, synthetic_flora):
        results = search_by_ids_in_flora(synthetic_flora, ["geo-nuts"])
        assert len(results) == 1
        assert results[0]["id"] == "geo-nuts"

    def test_finds_multiple_ids(self, synthetic_flora):
        results = search_by_ids_in_flora(synthetic_flora, ["geo-nuts", "climate-co2"])
        assert len(results) == 2

    def test_returns_empty_for_unknown_id(self, synthetic_flora):
        results = search_by_ids_in_flora(synthetic_flora, "does-not-exist")
        assert results == []

    def test_string_not_treated_as_char_sequence(self, synthetic_flora):
        """A short ID must NOT match partial characters of a longer query string.
        Before the fix, passing the string "geo-nuts" as ids would check whether
        each herb.id is a *substring* of the string "geo-nuts", so e.g. "geo"
        would falsely match.  Ensure only exact IDs match.
        """
        # Craft a herb whose id is a substring of the query string
        substring_herb = Herb(
            {**_HERB_META_A, "id": "geo"},
            base_path=Path("/tmp/geo"),
            with_resources=False,
        )
        flora = [substring_herb]
        # When passing the full ID as a string, "geo" != "geo-nuts"
        results = search_by_ids_in_flora(flora, "geo-nuts")
        assert results == []

    def test_returns_herb_object(self, synthetic_flora):
        results = search_by_ids_in_flora(synthetic_flora, "climate-co2")
        assert "herb" in results[0]
        assert results[0]["herb"].id == "climate-co2"


# ---------------------------------------------------------------------------
# search_by_keywords_in_flora
# ---------------------------------------------------------------------------

class TestSearchByKeywords:
    def test_finds_by_single_keyword(self, synthetic_flora):
        results = search_by_keywords_in_flora(synthetic_flora, "geo")
        assert any(r["id"] == "geo-nuts" for r in results)

    def test_finds_by_keyword_list(self, synthetic_flora):
        results = search_by_keywords_in_flora(synthetic_flora, ["co2", "climate"])
        assert any(r["id"] == "climate-co2" for r in results)

    def test_no_match_below_min_score(self, synthetic_flora):
        results = search_by_keywords_in_flora(
            synthetic_flora, "zzznomatch", min_score=99
        )
        assert results == []

    def test_results_sorted_by_score_descending(self, synthetic_flora):
        results = search_by_keywords_in_flora(synthetic_flora, "co2")
        if len(results) > 1:
            scores = [r["score"] for r in results]
            assert scores == sorted(scores, reverse=True)
