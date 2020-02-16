import logging
from dataherb.fetch.remote import get_data_from_url as _get_data_from_url
from dataherb.core.base import Herb
from dataherb.core.search import search_by_keywords_in_flora as _search_by_keywords_in_flora
from dataherb.core.search import search_by_ids_in_flora as _search_by_ids_in_flora

logging.basicConfig()
logger = logging.getLogger("dataherb.dataherb")

_DATAHERB_API_URL = "https://dataherb.github.io/api/flora.json"

class Flora(object):
    """
    DataHerb is the container of datasets.
    """
    def __init__(self, api_url=None, flora=None):
        """
        :param api_url: API of the DataHerb service, defaults to dataherb official
        :type api_url: str, optional
        :param flora: list of Herbs, defaults to everything from the API
        :type flora: list, optional
        """
        if api_url is None:
            api_url = _DATAHERB_API_URL
        self.api_url = api_url

        self.website = "https://dataherb.github.io/flora"

        if flora is None:
            flora = self._get_flora()
        self.flora = flora

    def _get_flora(self):
        """
        _get_flora fetch flora from the provided API.
        """
        flora_request = _get_data_from_url(self.api_url)

        if not flora_request.status_code == 200:
            raise Exception(
                "Could not download dataherb flora from remote. status code: {}".format(
                    flora_request.status_code
                )
            )
        else:
            flora = flora_request.json()

        # Convert herbs to objects
        flora = [Herb(herb) for herb in flora]

        return flora

    def search(self, keywords):
        """
        search finds the datasets that matches the keywords

        :param keywords: [description]
        :type keywords: [type]
        :return: [description]
        :rtype: [type]
        """
        if isinstance(keywords, str):
            keywords = [keywords]

        return _search_by_keywords_in_flora(self.flora, keywords)

    def herb_meta(self, id):
        """
        herb loads the dataset

        :param id: herb id of the dataset
        :type id: str
        """

        herbs = _search_by_ids_in_flora(self.flora, id)

        if herbs:
            herb = herbs[0]

            herb = herb.get("herb")

            return herb.metadata()
        else:
            return

    def herb(self, id):
        """
        herb loads the dataset as dataframes.

        :param id: herb id
        :type id: str
        """

        herbs = _search_by_ids_in_flora(self.flora, id)

        herb_meta = self.herb_meta(id)

        if herbs:
            herb = herbs[0]

            herb = herb.get("herb")

            return herb
        else:
            logger.error(f"Could not find herb {id}")
            return


if __name__ == "__main__":

    dataherb = Flora()
    geo_datasets = _search_by_keywords_in_flora(dataherb.flora, keywords=["geo"])

    print(geo_datasets)

    print(
        dataherb.herb("geonames_timezone").leaves.get("dataset/geonames_timezone.csv").data
    )

    logger.debug("End of Game")