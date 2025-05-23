#!/usr/bin/env python3
"""
Main entry point for InfiniteJournal application.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv

from config import Settings, ConfigurationError
from bootstrap.cli import parse_args
from bootstrap.logging_setup import setup_logging
from bootstrap.errors import make_exception_hook, StartupError
from bootstrap.factory import compose_app

logger = logging.getLogger(__name__)


def main(argv: Optional[List[str]] = None) -> int:
    """
    Entry point for the application.
    
    Args:
        argv: Command line arguments (defaults to sys.argv)
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Load environment variables first
    env_file = Path('.env')
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment variables from {env_file}")

    # Parse command line arguments
    try:
        args = parse_args(argv)
    except SystemExit as e:
        return e.code or 0
    except Exception as e:
        print(f"Argument parsing error: {e}", file=sys.stderr)
        return 2

    # Load and validate configuration
    try:
        settings = Settings.load()
    except ConfigurationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        print("\nPlease check your environment variables or .env file:", file=sys.stderr)
        print("  IJ_WIDTH: Window width (100-5000)", file=sys.stderr)
        print("  IJ_HEIGHT: Window height (100-5000)", file=sys.stderr)
        print("  IJ_FPS: Target FPS (1-240)", file=sys.stderr)
        print("  IJ_BRUSH_MIN: Minimum brush size (1-200)", file=sys.stderr)
        print("  IJ_BRUSH_MAX: Maximum brush size (1-200)", file=sys.stderr)
        print(f"  IJ_DEFAULT_TOOL: Default tool ({', '.join(Settings.VALID_TOOLS)})", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Unexpected configuration error: {e}", file=sys.stderr)
        return 2

    # Setup logging
    console_level = getattr(logging, args.log_level or 'INFO', logging.INFO)
    try:
        setup_logging(settings, console_level)
    except StartupError as e:
        print(f"Logging setup error: {e}", file=sys.stderr)
        return 2

    # Install global exception handler
    sys.excepthook = make_exception_hook(settings)
    
    logger.info("Starting InfiniteJournal application")
    logger.info("Configuration: DEBUG=%s, SIZE=%dx%d, FPS=%d, TOOL=%s", 
               settings.DEBUG, settings.WIDTH, settings.HEIGHT, settings.FPS, settings.DEFAULT_TOOL)

    # Compose and run application
    try:
        app = compose_app(settings)
        logger.info("Application composed successfully")
        app.run()
        logger.info("Application exited normally")
        return 0
    except StartupError as e:
        logger.error("Startup failure: %s", e)
        if not settings.DEBUG:
            print(f"Startup failure: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 0
    except Exception as e:
        logger.exception("Unexpected error during application execution")
        if not settings.DEBUG:
            print(f"Unexpected error. Check logs in '{settings.LOG_DIR}/app.log'", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())