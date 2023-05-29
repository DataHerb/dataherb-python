from dataherb.cmd.search import HerbTable
from dataherb.flora import Flora


def test_herb_table(flora_path):
    id = "git-data-science-job"
    fl = Flora(flora_path=flora_path)

    herbs = fl.search(id)
    ht = HerbTable(herbs[0]["herb"])
    ht.table()
    ht.resource_tree()
