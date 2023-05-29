import json
import sys
from pathlib import Path

from loguru import logger
from typing import cast, Optional

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)


class Config:
    """Config system for Dataherb"""

    def __init__(
        self,
        is_aggregated: bool = False,
        config_path: Optional[Path] = None,
        no_config_error: bool = False,
    ):
        self.is_aggregated = is_aggregated

        self.config_path = config_path
        self.no_config_error = no_config_error
        if self.config_path is None:
            home = Path.home()
            self.config_path = home / ".dataherb/config.json"

        if not self.config_path.exists():
            if self.no_config_error:
                logger.error(
                    f"Config file {self.config_path} does not exist.\n"
                    f"If this is the first time you use dataherb, please run `dataherb configure` to config dataherb."
                )

        # self.config = self.get_config(no_config_error=self.no_config_error)

    def _flora_path(self, flora, workdir: Optional[str] = None) -> Path:
        """Get the full path to the specified flora"""

        if workdir is None:
            workdir = self.config["WD"]

        if self.is_aggregated:
            which_flora_path = Path(workdir) / "flora" / Path(flora + ".json")
        else:
            which_flora_path = Path(workdir) / "flora" / Path(flora)
        logger.debug(f"Using flora path: {which_flora_path}")
        if not which_flora_path.exists():
            raise Exception(f"flora config {which_flora_path} does not exist")

        return which_flora_path

    @property
    def config(self):
        """Loads the dataherb config file.

        Load the content from the specified file as the config. The config file has to be json.
        """
        return self._config()

    def _config(self) -> dict:
        """Loads the dataherb config file."""

        config_path = cast(Path, self.config_path)

        logger.debug(f"Using {config_path} as config file for dataherb")
        try:
            with config_path.open(mode="r") as f:
                conf = json.load(f)

            if not conf.get("workdir"):
                logger.error(
                    f"Please specify working directory in the config file using the key workdir"
                )
            elif conf.get("workdir", "").startswith("~"):
                home = Path.home()
                conf["workdir"] = str(home / conf["workdir"][2:])
        except json.decoder.JSONDecodeError:
            logger.error(
                f"Config file {config_path} is not valid json.\n"
                f"Please rerun `dataherb configure` to reconfi dataherb or manually fix it."
            )
            conf = {}

        return conf

    @property
    def workdir(self):
        return self.config["workdir"]

    @property
    def flora_path(self):
        return self._flora_path(
            self.config.get("default", {}).get("flora"), self.config["workdir"]
        )

    @property
    def flora(self):
        return self.config.get("default", {}).get("flora")
