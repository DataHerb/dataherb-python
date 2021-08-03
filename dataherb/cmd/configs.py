from loguru import logger
import json
from pathlib import Path


def load_dataherb_config(config_path=None):
    """Loads the dataherb config file.

    Load the content from the specified file as the config. The config file has to be json.
    """

    if config_path is None:
        home = Path.home()
        config_path = home / ".dataherb/config.json"

    logger.debug(f"Using {config_path} as config file for dataherb")
    with open(config_path, 'r') as f:
        conf = json.load(f)

    if not conf.get("workdir"):
        logger.error(f"Please specify working directory in the config file using the key workdir")
    elif conf.get("workdir", "").startswith("~"):
        home = Path.home()
        conf["workdir"] = str(home / conf["workdir"][2:])

    return conf