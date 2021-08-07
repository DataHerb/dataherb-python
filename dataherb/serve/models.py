from abc import abstractclassmethod
import sys
from loguru import logger
from dataherb.flora import Flora

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)


class SourceModel:
    """
    Model is the base class for
    """

    def __init__(self, path_to_datasets: str) -> None:
        self.path_to_datasets = path_to_datasets
        self.metas = []

    @abstractclassmethod
    def fetch_metadata(self):
        raise NotImplementedError(f"Please implement this method")


class SaveModel:
    """
    SaveModel take the models and save them as files to serve as the database.
    """

    def __init__(self, flora, workdir, **kargs) -> None:

        if isinstance(flora, str):
            flora = Flora(flora)

        self.flora = flora
        self.workdir = workdir
        self.kargs = kargs

    @abstractclassmethod
    def save_json(self) -> None:
        raise NotImplementedError("Please implement save_json method")

    @abstractclassmethod
    def save_markdown(self) -> None:
        raise NotImplementedError("Please implement save_markdown method")

    @abstractclassmethod
    def save_all(self) -> None:
        raise NotImplementedError("Please implement save_all method")
