from typing import Sequence, Union, List, Optional

from dataherb.core.base import Herb


def search_by_keywords_in_flora(
    flora: List[Herb],
    keywords: Union[str, List[str]],
    keys: Optional[List[str]] = None,
    min_score: float = 50,
) -> List[dict]:
    """
    search_in_flora calculates the match score of each herb and returns the top 10.

    :param flora: list of herbs
    :param keywords: search keywords
    :param keys: list of dictionary keys to look into
    :param min_score: minimum score of the dataset, default to 50
    """

    if isinstance(keywords, str):
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


def search_by_ids_in_flora(flora: List[Herb], ids: Union[str, Sequence[str]]) -> List[dict]:
    """
    search_in_flora finds the herb with the corresponding ids

    :param flora: list of herbs
    :type flora: list
    :param ids: one or more herb ids to locate
    :type ids: str or list of str
    :return: herbs that matches the id
    :rtype: list
    """

    # Normalise: a plain string should be treated as a single ID, not a
    # character-by-character sequence.
    if isinstance(ids, str):
        ids = [ids]
    elif not isinstance(ids, (list, tuple, set)):
        ids = list(ids)

    herbs = []
    for herb in flora:
        if herb.id in ids:
            herb_matched = {"herb": herb, "id": herb.id}
            herbs.append(herb_matched)

    return herbs
