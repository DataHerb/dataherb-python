from typing import Sequence, Union, List, Sequence

from dataherb.core.base import Herb


def search_by_keywords_in_flora(
    flora: List[Herb],
    keywords: List[str],
    keys: List[str] = None,
    min_score: float = 50,
) -> List[dict]:
    """
    search_in_flora calculates the match score of each herb and returns the top 10.

    :param flora: list of herbs
    :param keywords: search keywords
    :param keys: list of dictionary keys to look into
    :param min_score: minimum score of the dataset, default to 50
    """

    if not isinstance(keywords, List):
        keywords = [keywords]

    herb_scores = []

    for herb in flora:
        herb_search_score = {
            "id": herb.id,
            "herb": herb,
            "score": herb.search_score(keywords),
        }
        herb_scores.append(herb_search_score)

    ranked_herbs = sorted(herb_scores, key=lambda i: i["score"], reverse=True)

    ranked_herbs = [i for i in ranked_herbs if i.get("score", 0) >= min_score]

    return ranked_herbs


def search_by_ids_in_flora(flora: List[Herb], ids: Sequence[str]) -> List[dict]:
    """
    search_in_flora finds the herb with the corresponding ids

    :param flora: list of herbs
    :type flora: list
    :param ids: ids of the herbs to be located
    :type ids: list
    :return: herbs that matches the id
    :rtype: list
    """

    if not isinstance(ids, Sequence):
        ids = [ids]

    herbs = []
    for herb in flora:
        if herb.id in ids:
            herb_matched = {"herb": herb, "id": herb.id}
            herbs.append(herb_matched)

    return herbs
