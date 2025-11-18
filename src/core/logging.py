import logging
import sys
from src.core.config import config
from src.core.events import event_bus

class EventBusHandler(logging.Handler):
    """
    Custom logging handler that publishes logs to the event bus
    so they can be displayed in the TUI.
    """
    def emit(self, record):
        try:
            msg = self.format(record)
            event_bus.publish("log", message=msg)
        except Exception:
            self.handleError(record)

def setup_logging():
    """
    Configure logging to write to a file, stderr, and the event bus.
    """
    # Create handlers
    file_handler = logging.FileHandler("scram.log")
    stream_handler = logging.StreamHandler(sys.stderr)
    event_handler = EventBusHandler()
    
    # Set format
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    event_handler.setFormatter(formatter)

    logging.basicConfig(
        level=config.LOG_LEVEL,
        handlers=[
            file_handler,
            stream_handler,
            event_handler
        ]
    )
    logging.info("Logging initialized")
