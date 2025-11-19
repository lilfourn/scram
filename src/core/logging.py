import logging
import sys
import os
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


def redirect_std_streams(log_file="scram.log"):
    """
    Redirect stdout and stderr to a file to prevent TUI corruption
    from low-level library outputs (e.g. C++ extensions).
    """
    # Open the log file
    # We must keep the file object alive to prevent garbage collection from closing the FD
    # before we are done with dup2
    log_file_obj = open(log_file, "a")
    log_fd = log_file_obj.fileno()

    # Flush Python buffers
    sys.stdout.flush()
    sys.stderr.flush()

    # Redirect stderr (fd 2) to the log file
    # We do NOT redirect stdout (fd 1) because the TUI needs it to draw the interface.
    os.dup2(log_fd, 2)

    # Update sys.stderr to point to the new file handle
    sys.stderr = os.fdopen(2, "w")


def setup_logging():
    """
    Configure logging to write to a file and the event bus.
    """
    # Create handlers
    file_handler = logging.FileHandler("scram.log")
    event_handler = EventBusHandler()

    # Set format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    event_handler.setFormatter(formatter)

    logging.basicConfig(level=config.LOG_LEVEL, handlers=[file_handler, event_handler])
    logging.info("Logging initialized")
