import json
import shutil
import sys
import validators
from pathlib import Path
from yarl import URL

from loguru import logger

from dataherb.core.base import Herb
from dataherb.core.search import search_by_ids_in_flora as _search_by_ids_in_flora
from dataherb.core.search import search_by_keywords_in_flora
from dataherb.fetch.remote import get_data_from_url
from dataherb.parse.model_json import MetaData
from typing import List, Union, Optional
from dataherb.core.base import Herb


logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)


class Flora:
    """
    A container of datasets. It loads a local folder of dataset metadata and
    forms a list of dataset objects.

    The provided local path or remote resource will then be converted to a list
    of dataherb objects.

    :param flora: path to the flora database. Either an URL or a local path.
    :param is_aggregated: if True, the flora is aggregated into one json file.
    """

    def __init__(self, flora_path: Union[Path, URL], is_aggregated: bool = False):

        self.is_aggregated = is_aggregated

        if not isinstance(flora_path, (Path, URL)):
            raise Exception(f"flora must be a path or a url. ({flora_path})")

        if isinstance(flora_path, URL):
            self.flora = self._get_remote_flora(flora_path)

        if isinstance(flora_path, Path):
            if flora_path.suffix == ".json":
                self.is_aggregated = True
            self.workdir = flora_path.parent.parent
            self.flora_path = flora_path
            self.flora = self._get_local_flora(flora_path)

        if is_aggregated != self.is_aggregated:
            logger.warning(
                f"flora has is_aggregated={self.is_aggregated}, "
                "but was specified as is_aggregated={is_aggregated}."
            )

        logger.debug(f"flora workdir {self.workdir}")

    def _get_local_flora(self, flora_config: Path) -> List[Herb]:
        """
        _get_local_flora fetch flora from the local folder or file.

        There are two scenarios:

        - The flora is one aggregated local json file.
        - The flora is a folder that contains folders of dataset ids.
        """
        if self.is_aggregated:
            with open(flora_config, "r") as f:
                json_flora = json.load(f)
        else:
            flora_folder = Path(flora_config)
            herb_paths = [f for f in flora_folder.iterdir() if f.is_dir()]
            json_flora = [
                json.load(open(f.joinpath("dataherb.json"), "r")) for f in herb_paths
            ]

        return [
            Herb(herb, base_path=self.workdir / f'{herb.get("id", "")}')
            for herb in json_flora
        ]

    def _get_remote_flora(self, flora_config: URL) -> List[Herb]:
        """
        _get_remote_flora fetch flora from the remote API.

        !!! warning
            Currently, this mode only works for aggregated json flora.
        """
        flora_request = get_data_from_url(flora_config)

        if not flora_request.status_code == 200:
            raise Exception(
                "Could not download dataherb flora from remote. status code: {}".format(
                    flora_request.status_code
                )
            )
        else:
            json_flora = flora_request.json()

        return [
            Herb(herb, base_path=self.workdir / f'{herb.get("id", "")}')
            for herb in json_flora
        ]

    def add(self, herb: Union[Herb, dict, MetaData]) -> None:
        """
        Add a herb to the flora.
        """

        herb = self._convert_to_herb(herb)

        logger.debug(f"adding herb with metadata: {herb.metadata}")

        for h_exist in self.flora:
            if herb.id == h_exist.id:
                raise Exception(f"herb id = {herb.id} already exists")

        self.flora.append(herb)
        if self.is_aggregated:
            self.save(path=self.flora_path)
        else:
            self.save(herb=herb)

    def _convert_to_herb(self, herb: Union[Herb, dict, MetaData]) -> Herb:
        if isinstance(herb, MetaData):
            herb = Herb(herb.metadata)
        elif isinstance(herb, dict):
            herb = Herb(herb)
        elif isinstance(herb, Herb):
            pass
        else:
            raise Exception(f"Input herb type ({type(herb)}) is not supported.")

        return herb

    def remove(self, herb_id: str) -> None:
        """
        Removes a herb from the flora.
        """
        for id in [i.id for i in self.flora]:
            if id == herb_id:
                logger.debug(f"found herb id = {herb_id}")

        self.flora = [h for h in self.flora if h.id != herb_id]

        if self.is_aggregated:
            self.save(path=self.flora_path)
        else:
            self.remove_herb_from_flora(herb_id)

    def save(self, path: Path = None, id: str = None, herb: Herb = None) -> None:
        """save flora metadata to json file"""

        if path is None:
            path = self.flora_path

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
                self.save_herb_meta(id=herb.id, path=path / f"{herb.id}")
            elif id:
                logger.debug(f"Saving herb using herb id")
                self.save_herb_meta(id, path / f"{id}")

    def save_herb_meta(self, id: str, path: Path = None) -> None:
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

    def remove_herb_from_flora(self, id: str, path: Path = None) -> None:
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

    def search(self, keywords: Union[str, List[str]]) -> List[dict]:
        """
        search finds the datasets that matches the keywords

        :param keywords: keywords to be searched
        """
        if isinstance(keywords, str):
            keywords = [keywords]

        return search_by_keywords_in_flora(flora=self.flora, keywords=keywords)

    def herb_meta(self, id: str) -> Optional[dict]:
        """
        herb loads the dataset

        :param id: herb id of the dataset
        """

        herbs = _search_by_ids_in_flora(self.flora, id)

        if herbs:
            herb = herbs[0].get("herb")
            if herb:
                return herb.metadata
            else:
                return None
        else:
            return None

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
            herb = herbs[0].get("herb")
            if herb:
                return herb
            else:
                return None
        else:
            logger.error(f"Could not find herb {id}")
            return None
