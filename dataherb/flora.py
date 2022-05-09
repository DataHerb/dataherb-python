import json
import shutil
import sys
from pathlib import Path

from loguru import logger

from dataherb.core.base import Herb
from dataherb.core.search import search_by_ids_in_flora as _search_by_ids_in_flora
from dataherb.core.search import (
    search_by_keywords_in_flora as _search_by_keywords_in_flora,
)
from dataherb.fetch.remote import get_data_from_url as _get_data_from_url
from dataherb.parse.model_json import MetaData
from typing import List, Union, Optional
from dataherb.core.base import Herb


logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)


class Flora:
    """
    A container of datasets. It loads a local folder of dataset metadata and
     forms a list of dataset objects.

    :param flora: path to the flora database. Either an URL or a local path.
    :param is_aggregated: if True, the flora is aggregated into one json file.
    """

    def __init__(self, flora: str, is_aggregated: bool = False):

        self.is_aggregated = is_aggregated

        if not isinstance(flora, str):
            raise Exception(f"flora must be a json file or a url. ({flora})")
        else:
            if flora.endswith(".json"):
                self.is_aggregated = True
            self.workdir = Path(flora).parent.parent
            self.flora_config: str = flora
            self.flora = self._get_flora(flora)

        logger.debug(f"flora workdir {self.workdir}")

    def _get_flora(self, flora_config: str) -> List[Herb]:
        """
        _get_flora fetch flora from the provided API or file path.

        This method will first assume the config is a local flora.
         If the local flora doesn't exist, this method will assume
         that the config is a url of a json.
         For now, the remote json has to return a list of dataherb metadata.

        The provided file or remote resource will then be converted to a list
        of dataherb objects.
        """
        if Path(flora_config).exists():
            json_flora = self._get_local_flora(flora_config)
        else:
            json_flora = self._get_remote_flora(flora_config)

        return [
            Herb(herb, base_path=self.workdir / f'{herb.get("id", "")}')
            for herb in json_flora
        ]

    def _get_local_flora(self, flora_config: str) -> List[dict]:
        """
        _get_local_flora fetch flora from the local folder or file.

        There are two scenarios:

        - The flora is one aggregated local json file.
        - The flora is a folder that contains folders of dataset ids.
        """
        if self.is_aggregated:
            with open(flora_config, "r") as f:
                flora = json.load(f)
        else:
            flora_folder = Path(flora_config)
            herb_paths = [f for f in flora_folder.iterdir() if f.is_dir()]
            flora = [
                json.load(open(f.joinpath("dataherb.json"), "r")) for f in herb_paths
            ]

        return flora

    def _get_remote_flora(self, flora_config: str) -> List[dict]:
        """
        _get_remote_flora fetch flora from the remote API.

        !!! warning
            Currently, this mode only works for aggregated json flora.
        """
        flora_request = _get_data_from_url(flora_config)

        if not flora_request.status_code == 200:
            raise Exception(
                "Could not download dataherb flora from remote. status code: {}".format(
                    flora_request.status_code
                )
            )
        else:
            flora = flora_request.json()

        return flora

    def add(self, herb: Union[Herb, dict, MetaData]) -> None:
        """
        Add a herb to the flora.
        """
        if isinstance(herb, MetaData):
            herb = Herb(herb.metadata)
        elif isinstance(herb, dict):
            herb = Herb(herb)
        elif isinstance(herb, Herb):
            pass
        else:
            raise Exception(f"Input herb type ({type(herb)}) is not supported.")

        logger.debug(f"metadata: {herb.metadata}")

        for id in [i.id for i in self.flora]:
            if id == herb.id:
                raise Exception(f"herb id = {herb.id} already exists")

        self.flora.append(herb)
        if self.is_aggregated:
            self.save()
        else:
            self.save(herb=herb)

    def remove(self, herb_id: str) -> None:
        """
        Removes a herb from the flora.
        """
        for id in [i.id for i in self.flora]:
            if id == herb_id:
                logger.debug(f"found herb id = {herb_id}")

        self.flora = [h for h in self.flora if h.id != herb_id]

        if self.is_aggregated:
            self.save()
        else:
            self.remove_herb_from_flora(herb_id)

    def save(self, path: str = None, id: str = None, herb: Herb = None) -> None:
        """save flora metadata to json file"""

        if path is None:
            path = self.flora_config

        if isinstance(path, str):
            path = Path(path)

        logger.debug(
            f"type of a herb in flora: {type(self.flora[0])}\n{self.flora[0].metadata}"
        )

        if self.is_aggregated:
            serialized_flora = []
            for h in self.flora:
                logger.debug(f"herb (type {type(h)}): {h}")
                serialized_flora.append(h.metadata)

            with open(path, "w") as fp:
                json.dump(
                    serialized_flora,
                    fp,
                    sort_keys=True,
                    indent=4,
                    separators=(",", ": "),
                )
        else:
            if (not id) and (not herb):
                raise Exception("dataherb id must be provided")
            elif herb:
                logger.debug(f"Saving herb using herb object")
                self.save_herb_meta(herb.id, path / f"{herb.id}")
            elif id:
                logger.debug(f"Saving herb using herb id")
                self.save_herb_meta(id, path / f"{id}")

    def save_herb_meta(self, id: str, path: str = None) -> None:
        """Save a herb metadata to json file"""
        if path is None:
            path = self.workdir / f"{id}"

        if not path.exists():
            path.mkdir(parents=True)

        logger.debug(f"Will replace dataherb id {id}")
        with open(path / "dataherb.json", "w") as fp:
            json.dump(
                self.herb_meta(id), fp, sort_keys=True, indent=4, separators=(",", ": ")
            )

    def remove_herb_from_flora(self, id: str, path: str = None) -> None:
        """Remove a herb metadata to json file"""
        if path is None:
            path = self.workdir / f"{id}"

        if not path.exists():
            logger.debug(f"dataherb {id} doesn't exist")
            return
        else:
            try:
                shutil.rmtree(path)
            except OSError as e:
                logger.error(
                    f"Can not remove herb id {id}: {e.filename} - {e.strerror}."
                )

    def search(self, keywords: Union[str, List[str]]) -> List[Herb]:
        """
        search finds the datasets that matches the keywords

        :param keywords: keywords to be searched
        """
        if isinstance(keywords, str):
            keywords = [keywords]

        return _search_by_keywords_in_flora(self.flora, keywords)

    def herb_meta(self, id: str) -> Optional[dict]:
        """
        herb loads the dataset

        :param id: herb id of the dataset
        """

        herbs = _search_by_ids_in_flora(self.flora, id)

        if herbs:
            herb = herbs[0]

            herb = herb.get("herb")

            return herb.metadata
        else:
            return

    def herb(self, id: str) -> Optional[Herb]:
        """
        herb loads the dataset as dataframes.

        :param id: herb id
        """

        herbs = _search_by_ids_in_flora(self.flora, id)
        if len(herbs) > 1:
            logger.error(
                f"Found multiple datasets with id {id}, please fix this in your flora data json file, e.g, WORKDIRECTORY/flora/flora.json."
            )

        if herbs:
            herb = herbs[0]
            herb = herb.get("herb")
            return herb
        else:
            logger.error(f"Could not find herb {id}")
            return
