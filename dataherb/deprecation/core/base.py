import io

import click
import pandas as pd
from loguru import logger

from dataherb.fetch.remote import get_data_from_url


class Leaf:
    """
    [Deprecated]

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
        file_content = get_data_from_url(self.url)
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
