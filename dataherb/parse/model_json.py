import json
import sys
from pathlib import Path

from loguru import logger
from dataherb.parse.utils import STATUS_CODE

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

    def validate(self) -> dict:
        """Validate the existing metadata file and return a structured summary.

        Loads the dataherb.json in the configured folder and checks whether
        each declared resource file exists on disk.

        :return: dict with a ``"data"`` key containing a list of per-resource
            validation summaries.  Each summary maps field names to dicts with
            ``"value"``, ``"status"``, and ``"message"`` keys, matching the
            format consumed by the ``dataherb validate`` CLI command.
        """

        self._validate_paths()
        self.load()

        resources = self.metadata.get("datapackage", {}).get("resources", [])
        data_summary = []

        for r in resources:
            resource_path = r.get("path", "")
            resource_name = r.get("name", "")
            full_path = self.dataherb_folder / resource_path if resource_path else None

            # --- path check ---
            if not resource_path:
                path_entry = {
                    "value": resource_path,
                    "status": STATUS_CODE["ERROR"],
                    "message": "path field is missing",
                }
            elif full_path and not full_path.exists():
                path_entry = {
                    "value": resource_path,
                    "status": STATUS_CODE["ERROR"],
                    "message": f"{resource_path} was not found",
                }
            else:
                path_entry = {
                    "value": resource_path,
                    "status": STATUS_CODE["SUCCESS"],
                    "message": f"{resource_path} was found",
                }

            # --- name check ---
            if not resource_name:
                name_entry = {
                    "value": resource_name,
                    "status": STATUS_CODE["WARNING"],
                    "message": "name field is missing",
                }
            else:
                name_entry = {
                    "value": resource_name,
                    "status": STATUS_CODE["SUCCESS"],
                    "message": f"{resource_name} exists",
                }

            data_summary.append({"path": path_entry, "name": name_entry})

        return {"data": data_summary}

    def _validate_paths(self) -> None:
        """Check if the metadata path exists"""

        metadata_full_path = self.dataherb_folder / self.metadata_file

        if not self.dataherb_folder.exists():
            raise FileNotFoundError(f"Path {self.dataherb_folder} doesn't exist!")
        else:
            logger.info(f"Path {self.dataherb_folder} exists.")

        if not metadata_full_path.is_file():
            raise FileNotFoundError(f"File {metadata_full_path} doesn't exist!")
        else:
            logger.info(f"File {metadata_full_path} exists!")
