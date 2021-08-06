from loguru import logger
from dataherb.parse.model import MetaData
import sys

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)

if __name__ == "__main__":
    logger.debug("End of Game")
