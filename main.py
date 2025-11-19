import sys
import asyncio
from src.core.logging import setup_logging, redirect_std_streams
from src.tui.app import ScramApp


def main():
    # Redirect low-level stdout/stderr to file to prevent TUI corruption
    # redirect_std_streams()
    setup_logging()
    app = ScramApp()
    app.run()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
