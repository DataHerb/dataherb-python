import io
from pathlib import Path

import click
import pandas as pd
from dataherb.cmd.configs import load_dataherb_config
from dataherb.fetch.remote import get_data_from_url as _get_data_from_url
from dataherb.parse.model_json import MetaData
from dataherb.utils.data import flatten_dict as _flatten_dict
from datapackage import Package, Resource
from loguru import logger
from rapidfuzz import fuzz
import sys

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)


class Herb(object):
    """
    Herb is a collection of the dataset.
    """

    def __init__(self, meta_dict, base_path=None, with_resources=True):
        """
        :param herb_meta_json: the dictionary that specifies the herb
        :type herb_meta_json: dict
        """
        if base_path is None:
            CONFIG = load_dataherb_config()
            self.base_path = CONFIG["workdir"]
        else:
            self.base_path = base_path
        if isinstance(self.base_path, str):
            self.base_path = Path(self.base_path)

        self.with_resources = with_resources

        if isinstance(meta_dict, dict):
            self.herb_meta_json = meta_dict
        elif isinstance(meta_dict, MetaData):
            logger.debug("get herb_meta_json from MetaData ...")
            self.herb_meta_json = meta_dict.metadata
        else:
            logger.debug(f"input meta type ({type(meta_dict)}) is not supported.")
            click.BadParameter(
                f"input meta type ({type(meta_dict)}) is not supported.",
                param=meta_dict,
            )

        self._from_meta_dict(self.herb_meta_json)

    @property
    def is_local(self):
        is_local = False
        if self.base_path.exists():
            is_local = True

        return is_local

    def _from_meta_dict(self, meta_dict):
        """Build properties from meta dict"""
        self.name = meta_dict.get("name")
        self.description = meta_dict.get("description")
        self.repository = meta_dict.get("repository")  # Deprecated
        self.id = meta_dict.get("id")

        self.source = meta_dict.get("source")
        self.metadata_uri = meta_dict.get("metadata_uri")
        self.uri = meta_dict.get("uri")
        self.datapackage = Package(meta_dict.get("datapackage"))
        if not self.datapackage:
            self.update_datapackage()

        if self.with_resources:
            self.resources = [
                self.get_resource(i, source_only=False)
                for i in range(len(self.datapackage.resources))
            ]

    def get_resource(self, idx=None, path=None, name=None, source_only=True):
        if idx is None:
            if path:
                all_paths = [
                    r.descriptor.get("path") for r in self.datapackage.resources
                ]
                if path in all_paths:
                    idx = all_paths.index(path)
                else:
                    logger.error(f"path = {path} is not in resources.")
            elif name:
                all_names = [
                    r.descriptor.get("name") for r in self.datapackage.resources
                ]
                if name in all_names:
                    idx = all_names.index(name)
                else:
                    logger.error(f"name = {name} is not in resources.")
            else:
                raise Exception(
                    f"Please specify at least one of the keywords: idx, path, name."
                )

        if self.is_local:
            logger.debug(
                f"Using local dataset for {self.id}, sync it if you need the updated version."
            )
            r = self.datapackage.resources[idx]
            logger.debug(f"using base_path: {str(self.base_path)}")
            logger.debug(f"using descriptor: {r.descriptor}")
            resource = Resource(r.descriptor, base_path=str(self.base_path))
            logger.debug(f"base_path of r_1: {resource._Resource__base_path}")
        elif (not self.is_local) and (self.source == "git"):
            logger.debug(f"Using remote data")
            self.remote_path = f"{self.metadata_uri[:-16]}"
            r = self.datapackage.resources[idx]
            resource = Resource(
                {
                    **(r.descriptor),
                    **{"path": self.remote_path + r.descriptor.get("path", "")},
                }
            )
        elif (not self.is_local) and (self.source == "s3"):
            logger.debug(f"Using remote data")
            logger.debug(
                f"Direct resource from S3 is not supported yet. "
                f"Please sync the dataset to local using the command line first.\n"
                f"TODO: Sync S3 to local after confirmation from here."
            )
            resource = self.datapackage.resources[idx]
        else:
            logger.error("Resource is not supported. Currently supporting S3 and git.")
            resource = self.datapackage.resources[idx]

        if source_only:
            return resource.source
        else:
            return resource

    def update_datapackage(self):
        """
        update_datapackage gets the datapackage metadata from the metadata_uri
        """

        if self.source == "git":
            file_content = _get_data_from_url(self.metadata_uri)

            if not file_content.status_code == 200:
                file_error_msg = "Could not fetch remote file: {}; {}".format(
                    self.url, file_content.status_code
                )
                click.ClickException(file_error_msg)
                # file_content = json.dumps([{"url": self.url, "error": file_error_msg}])
            else:
                file_content = file_content.json()  # .decode(self.decode)
        elif self.source == "s3":
            raise NotImplementedError(
                "Directly get dataherb.json from S3 is not yet implemented."
            )

        self.datapackage_meta = file_content

        self.herb_meta_json["datapackage"] = self.datapackage_meta

        self.datapackage = Package(self.datapackage_meta)

        return self.datapackage

    def search_score(self, keywords, keys=None):
        """
        search_score calcualtes the matching score of the herb for any given keyword

        :param key_word: keyword for the search
        :type key_word: list
        :param keys: list of keys in the dictionary to look into.
        :type keys: list, optional
        """

        if keys is None:
            keys = ["name", "id", "repository", "tags", "description"]

        if not isinstance(keywords, (list, tuple, set)):
            keywords = [keywords]

        herb_for_search = {
            key: val for key, val in self.herb_meta_json.items() if key in keys
        }

        herb_for_search = _flatten_dict(herb_for_search)

        keywords_scores = []
        for keyword in keywords:
            for key, val in herb_for_search.items():
                score = fuzz.token_set_ratio(val, keyword)
                keywords_scores.append(score)

        max_score = 0
        if keywords_scores:
            max_score = max(keywords_scores)

        return max_score

    @property
    def metadata(self, keys=None):
        """
        metadata formats the metadata of the herb
        """

        return self.herb_meta_json.copy()

    def download(self):
        """
        download downloads the dataset
        """

        raise NotImplementedError("Not implemented")

        # data_files = []

        # for leaf_meta in self.herb_meta_json.get("data"):
        #     leaf = Leaf(leaf_meta, self)
        #     data_files.append(leaf.download())

        # return data_files

    def __str__(self):
        meta = self.metadata
        authors = meta.get("contributors", [])
        authors = ", ".join([author.get("name") for author in authors])
        return (
            f"DataHerb ID: {meta.get('id')}\n"
            f"name: {meta.get('name')}"
            f"description: {meta.get('description')}\n"
            f"contributors: {authors}"
        )


class Leaf(object):
    """
    Deprecated

    Leaf is a data file of the Herb.
    """

    def __init__(self, leaf_meta_json, herb):
        self.leaf_meta_json = leaf_meta_json
        self.herb = herb

        self.url = "https://raw.githubusercontent.com/{}/master/{}".format(
            self.herb.repository, self.leaf_meta_json.get("path")
        )
        self.format = self.leaf_meta_json.get("format")
        # decode the file content using decode
        self.decode = self.leaf_meta_json.get("decode", "utf-8")
        self.name = self.leaf_meta_json.get("name")
        self.description = self.leaf_meta_json.get("description")
        self.path = self.leaf_meta_json.get("path")
        self.downloaded = {}

    def download(self):
        """
        download downloads the data
        """

        # Fetch data from remote
        file_content = _get_data_from_url(self.url)
        if not file_content.status_code == 200:
            file_error_msg = "Could not fetch remote file: {}; {}".format(
                self.url, file_content.status_code
            )
            click.ClickException(file_error_msg)
            # file_content = json.dumps([{"url": self.url, "error": file_error_msg}])
        else:
            file_content = file_content.content

        if self.format.lower() == "csv":
            if isinstance(file_content, bytes):
                file_string_io = io.StringIO(file_content.decode(self.decode))
            else:
                file_string_io = file_content
            # csv files may have comment rows
            file_comment = self.leaf_meta_json.get("comment")
            # csv files may have different separators
            file_separator = self.leaf_meta_json.get("seperator", ",")
            try:
                data = pd.read_csv(
                    file_string_io, comment=file_comment, sep=file_separator
                )
            except Exception as e:
                logger.error(f"Error loading remote file: {self.url}")
                data = file_string_io
        elif self.format.lower() == "json":
            if isinstance(file_content, bytes):
                file_string_io = io.StringIO(file_content.decode(self.decode))
            else:
                file_string_io = file_content

            try:
                data = pd.read_json(self.url)
            except Exception as e:
                logger.error(f"Error loading remote file: {self.url}")
                data = file_string_io
        else:
            logger.error(f"data file format {self.format} is not supported!")

        self.downloaded = {"data": data, "content": file_content}

    @property
    def data(self):
        if not self.downloaded:
            self.download()

        return self.downloaded.get("data")

    @property
    def content(self):
        if not self.downloaded:
            self.download()

        return self.downloaded.get("content")

    def metadata(self, format=None):
        """
        metadata formats the metadata of the herb
        """
        if format is None:
            format = "json"

        if format == "json":
            return self.leaf_meta_json
        else:
            logger.error(f"format {format} is not support for metadata!")

    def __str__(self):
        return """{} from {} with size {}, the remote file is located at {};\n\n{}
        """.format(
            self.leaf_meta_json.get("path"),
            self.herb.id,
            self.leaf_meta_json.get("size"),
            self.path,
            self.metadata(),
        )
