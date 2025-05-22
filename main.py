#!/usr/bin/env python3
from dotenv import load_dotenv
import sys
import logging

from config import Settings
from bootstrap.cli import parse_args
from bootstrap.logging_setup import setup_logging
from bootstrap.errors import make_exception_hook, StartupError
from bootstrap.factory import compose_app


def main(argv=None) -> int:
    """Entry point for the application."""
    load_dotenv()
    args = parse_args(argv)

    try:
        settings = Settings.load()
    except Exception as e:
        print(f"Startup error: {e}", file=sys.stderr)
        return 2

    console_level = getattr(logging, args.log_level or 'INFO')
    try:
        setup_logging(settings, console_level)
    except StartupError as e:
        print(f"Logging error: {e}", file=sys.stderr)
        return 2

    sys.excepthook = make_exception_hook(settings)
    logging.info("Starting application composition...")

    try:
        app = compose_app(settings)
        app.run()
        logging.info("Application exited normally.")
        return 0
    except StartupError as e:
        logging.error(f"Startup failure: {e}")
        print(f"Startup failure: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        logging.info("Shutdown via KeyboardInterrupt.")
        return 0


if __name__ == '__main__':
    sys.exit(main())
