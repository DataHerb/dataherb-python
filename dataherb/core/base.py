import io
import json
import logging
from collections import OrderedDict

import pandas as pd
from dataherb.fetch.remote import get_data_from_url as _get_data_from_url
from dataherb.utils.data import flatten_dict as _flatten_dict
from fuzzywuzzy import fuzz, process


logging.basicConfig()
logger = logging.getLogger("dataherb.core.base")


class Herb(object):
    """
    Herb is a collection of the dataset.
    """
    def __init__(self, herb_meta_json):
        """
        :param herb: the dictionary that specifies the herb
        :type herb: dict
        """
        if isinstance(herb_meta_json, dict):
            herb_meta_json = OrderedDict(herb_meta_json)
        self.herb_meta_json = herb_meta_json
        self.name = self.herb_meta_json.get("name")
        self.description = self.herb_meta_json.get("description")
        self.repository = self.herb_meta_json.get("repository")
        self.id = self.herb_meta_json.get("id")
        self._get_leaves()

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
            key:val for key, val in self.herb_meta_json.items()
            if key in keys
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

    def metadata(self, keys=None):
        """
        metadata formats the metadata of the herb
        """

        return self.herb_meta_json

    def download(self):
        """
        download downloads the dataset
        """

        data_files = []

        for leaf_meta in self.herb_meta_json.get("data"):
            leaf = Leaf(leaf_meta, self)
            data_files.append(leaf.download())

        return data_files

    def _get_leaves(self):
        """
        leaf fetches the leaf/leaves of the Herb.
        """
        self.leaves = {}

        for leaf_meta in self.herb_meta_json.get("data"):
            leaf_meta_path = leaf_meta.get("path")
            leaf = Leaf(leaf_meta, self)
            self.leaves[leaf_meta_path] = leaf

    def __str__(self):
        meta = self.metadata()
        authors = meta.get("contributors", [])
        authors = ", ".join([author.get("name") for author in authors])
        return (
            f"DataHerb ID: {meta.get('id')}\n"
            f"description: {meta.get('description')}\n"
            f"contributors: {authors}"
        )


class Leaf(object):
    """
    Leaf is a data file of the Herb.
    """

    def __init__(self, leaf_meta_json, herb):
        self.leaf_meta_json = leaf_meta_json
        self.herb = herb

        self.url = "https://raw.githubusercontent.com/{}/master/{}".format(
            self.herb.repository,
            self.leaf_meta_json.get("path")
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
                self.url,
                file_content.status_code
            )
            logger.error(
                file_error_msg
            )
            file_content = json.dumps([{
                "url": self.url,
                "error": file_error_msg
            }])
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

        self.downloaded = {
            "data": data,
            "content": file_content
        }

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
            self.metadata()
        )
