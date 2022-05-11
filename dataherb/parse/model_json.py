import json
import sys
from pathlib import Path

from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)


class MetaData:
    """
    JSON metadata object

    :param folder: path to the dataherb folder
    """

    def __init__(self, folder: Path):
        self.dataherb_folder = folder
        self.metadata_file = "dataherb.json"
        self.metadata: dict = {}

    def load(self) -> dict:
        """load the existing datapackage file"""
        metadata_full_path = self.dataherb_folder / self.metadata_file
        logger.debug(f"Load metadata from file: {metadata_full_path}")
        with open(metadata_full_path, "r") as fp:
            self.metadata = json.load(fp)

        logger.debug(f"Loaded metadata: {self.metadata}")

        return self.metadata

    def create(self, overwrite: bool = False) -> None:
        """creates .dataherb folder"""

        try:
            self.dataherb_folder.mkdir(parents=True, exist_ok=False)
            logger.info("Created ", self.dataherb_folder)
        except FileExistsError:
            logger.warning(
                f"{self.dataherb_folder} already exists! Will use the folder."
                "Pass the flag `overwrite=True` to recreate it, if one desires."
            )

        metadata_full_path = self.dataherb_folder / self.metadata_file

        if metadata_full_path.is_file():
            if not overwrite:
                raise FileExistsError(f"File {metadata_full_path} already exists!")
            else:
                logger.warning(f"Will overwrite {metadata_full_path}")

        with open(metadata_full_path, "w") as fp:
            json.dump(self.metadata, fp, indent=4)

        logger.debug(f"written to {metadata_full_path}")

    def validate(self) -> None:
        """validate the existing metadata file"""

        metadata_full_path = self.dataherb_folder / self.metadata_file

        self._validate_paths()

        with open(metadata_full_path, "r") as fp:
            metadata = json.load(fp)
        logger.info("loaded metadata ", self.dataherb_folder)
        logger.debug(f"loaded metadata {metadata}")

    def _validate_paths(self) -> None:
        """Check if the metadata path exists"""

        metadata_full_path = self.dataherb_folder / self.metadata_file

        if not self.dataherb_folder.exists():
            raise Exception(f"Path {self.dataherb_folder} doesn't exist!")
        else:
            logger.info(f"Path {self.dataherb_folder} exists.")

        if not metadata_full_path.is_file():
            raise FileNotFoundError(f"File {metadata_full_path} doesn't exist!")
        else:
            logger.info(f"File {metadata_full_path} exists!")
