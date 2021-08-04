import csv
import json
import os
from collections import OrderedDict
from pathlib import Path

import ruamel.yaml
from loguru import logger
from ruamel.yaml.representer import RoundTripRepresenter

IGNORED_FOLDERS_AND_FILES = [".git", ".dataherb", ".vscode"]


MESSAGE_CODE = {
    "MISSING": lambda x: f"{x} is missing",
    "FILE_NOT_FOUND": lambda x: f"{x} was not found",
    "FILE_FOUND": lambda x: f"{x} was found",
    "EXISTS": lambda x: f"{x} exists",
    "FREE_MESSAGE": lambda x: f"{x}",
}

STATUS_CODE = {
    "UNKNOWN": "unknown",
    "SUCCESS": "success",
    "WARNING": "warning",
    "ERROR": "error",
}


class MetaData(object):
    def __init__(self, folder):
        self.dataherb_folder = folder
        self.metadata_file = "datapackage.json"
        self.metadata = {}

    def load(self):
        """load the existing metadata file"""

        logger.debug(f"Load metadata from file: {self.metadata_file}")
        with open(self.metadata_file, "r") as fp:
            self.metadata = json.load(fp)

    def create(self):
        """creates datapackage.json file"""
        # create .dataherb folder
        dataherb_folder = self.dataherb_folder
        try:
            os.mkdir(dataherb_folder)
            logger.info("Created ", dataherb_folder)
        except FileExistsError:
            logger.info(
                dataherb_folder,
                " already exists! Creating datapackage.json file inside.",
            )
            pass

        metadata_file = self.metadata_file

        if os.path.isfile(os.path.join(dataherb_folder, metadata_file)):
            logger.error(
                f"File {os.path.join(dataherb_folder, metadata_file)} already exists!"
            )
            raise SystemExit

        with open(os.path.join(dataherb_folder, metadata_file), "w") as fp:
            documents = json.dump(self.metadata, fp, indent=4)

    def validate(self):
        """validate the existing metadata file"""

        dataherb_folder = self.dataherb_folder
        metadata_file = self.metadata_file
        summary = {}

        try:
            if not os.path.exists(dataherb_folder):
                logger.error(f"Folder {dataherb_folder} does'nt exists!")
                raise Exception(f"Path {dataherb_folder} doesn't exist!")
            if not os.path.isfile(os.path.join(dataherb_folder, metadata_file)):
                logger.error(
                    f"File {os.path.join(dataherb_folder, metadata_file)} doesn'nt exists!"
                )
                raise SystemExit

            with open(os.path.join(dataherb_folder, metadata_file), "r") as fp:
                documents = json.load(fp)

            logger.info("loaded metadata ", dataherb_folder)
        except FileExistsError:
            logger.info(
                dataherb_folder, " already exists! Creating metadata.yml file inside."
            )
            pass

        data = self._parse_leaves(documents)

        data_summary = summary.get("data", [])

        summary["data"] = data_summary

        return summary
