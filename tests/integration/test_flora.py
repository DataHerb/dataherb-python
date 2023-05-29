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
