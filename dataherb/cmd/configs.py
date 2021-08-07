from loguru import logger
import json
import sys
from pathlib import Path

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)


def load_dataherb_config(config_path=None, no_config_error=True):
    """[Deprecated]
    Loads the dataherb config file.

    Load the content from the specified file as the config. The config file has to be json.
    """

    if config_path is None:
        home = Path.home()
        config_path = home / ".dataherb/config.json"

    if not config_path.exists():
        if no_config_error:
            logger.error(
                f"Config file {config_path} does not exist.\n"
                f"If this is the first time you use dataherb, please run `dataherb configure` to config dataherb."
            )
        else:
            pass
        return {}

    logger.debug(f"Using {config_path} as config file for dataherb")
    try:
        with open(config_path, "r") as f:
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
