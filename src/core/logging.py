import logging
import sys
from src.core.config import config

def setup_logging():
    """
    Configure logging to write to a file and stderr (if not in TUI mode).
    """
    logging.basicConfig(
        level=config.LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("scram.log"),
            logging.StreamHandler(sys.stderr)
        ]
    )
    logging.info("Logging initialized")
