import sys

from loguru import logger


logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)

if __name__ == "__main__":
    logger.debug("End of Game")
