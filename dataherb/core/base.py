import logging
import io
import json
from fuzzywuzzy import fuzz, process
from utils.data import flatten_dict as _flatten_dict
from fetch.remote import get_data_from_url as _get_data_from_url
import yaml
import pandas as pd

logging.basicConfig()
logger = logging.getLogger("dataherb.core.base")


class Herb:
    """
    Herb is the base class for a dataset.
    """
    def __init__(self, herb_meta_json):
        """
        :param herb: the dictionary that specifies the herb
        :type herb: dict
        """
        self.herb_meta_json = herb_meta_json
        self.name = self.herb_meta_json.get("name")
        self.description = self.herb_meta_json.get("description")
        self.repsitory = self.herb_meta_json.get("repsitory")
        self.id = self.herb_meta_json.get("id")

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

    def metadata(self):
        """
        metadata formats the metadata of the herb
        """

        return yaml.dump(self.herb_meta_json)

    def download(self):
        """
        download downloads the dataset
        """

        data_files = []

        for file in self.herb_meta_json.get("data"):
            file_path = "https://raw.githubusercontent.com/{}/master/{}".format(
                self.repsitory,
                file.get("path")
            )
            file_format = file.get("format")
            # decode the file content using file_decode
            file_decode = file.get("decode", "utf-8")

            # Fetch data from remote
            file_content = _get_data_from_url(file_path)
            if not file_content.status_code == 200:
                file_error_msg = "Could not fetch remote file: {}; {}".format(
                    file_path,
                    file_content.status_code
                )
                logger.error(
                    file_error_msg
                )
                file_content = json.dumps([{
                    "path": file_path,
                    "error": file_error_msg
                }])
            else:
                file_content = file_content.content

            if file_format.lower() == "csv":
                if isinstance(file_content, bytes):
                    file_string_io = io.StringIO(file_content.decode(file_decode))
                else:
                    file_string_io = file_content
                # csv files may have comment rows
                file_comment = file.get("comment")
                # csv files may have different separators
                file_separator = file.get("seperator", ",")
                try:
                    data = pd.read_csv(
                        file_string_io, comment=file_comment, sep=file_separator
                    )
                except Exception as e:
                    logger.error(f"Error loading remote file: {file_path}")
                    data = file_string_io
            if file_format.lower() == "json":
                if isinstance(file_content, bytes):
                    file_string_io = io.StringIO(file_content.decode(file_decode))
                else:
                    file_string_io = file_content

                try:
                    data = pd.read_csv(file_path)
                except Exception as e:
                    logger.error(f"Error loading remote file: {file_path}")
                    data = file_string_io
            else:
                logger.error(f"data file format {file_format} is not supported!")

            data_files.append({
                "name": file.get("name"),
                "description": file.get("description"),
                "path": file_path,
                "df": data
            })

        return data_files

    def __str__(self):
        return self.metadata()