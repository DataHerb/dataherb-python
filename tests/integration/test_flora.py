from dataherb.flora import Flora
from datapackage import Resource


def test_flora(flora_path):

    fl = Flora(flora=flora_path)

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
