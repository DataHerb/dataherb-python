import logging
from fetch.fetch import get_data_from_url as _get_data_from_url
__all__ = ["main"]

logging.basicConfig()
logger = logging.getLogger("dataherb.dataherb")

class DataHerb:
    def __init__(self, herb_formula):
        self.herb_formula = herb_formula


def main():

    return



if __name__ == "__main__":

    logger.debug("End of Game")