import sys
import asyncio
from src.core.logging import setup_logging
from src.tui.app import ScramApp


def main():
    setup_logging()
    app = ScramApp()
    app.run()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
