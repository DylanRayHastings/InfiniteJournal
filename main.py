"""
Simple main entry point that uses the working drawing system.

This bypasses the complex enhanced systems and focuses on core functionality.
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
from bootstrap.factory import create_simple_app

logger = logging.getLogger(__name__)


def validate_environment() -> Optional[str]:
    """Validate the environment for running the application."""
    try:
        # Check Python version
        if sys.version_info < (3, 9):
            return f"Python 3.9+ required, found {sys.version_info.major}.{sys.version_info.minor}"
        
        # Check critical imports
        try:
            import pygame
        except ImportError:
            return "Pygame is not installed. Please install with: pip install pygame"
        
        # Check for write permissions in current directory
        try:
            test_file = Path("write_test.tmp")
            test_file.write_text("test")
            test_file.unlink()
        except Exception:
            return "No write permissions in current directory"
        
        return None  # Validation successful
        
    except Exception as e:
        return f"Environment validation failed: {e}"


def main(argv: Optional[List[str]] = None) -> int:
    """
    Simple entry point for the application.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Validate environment first
    env_error = validate_environment()
    if env_error:
        print(f"Environment validation failed: {env_error}", file=sys.stderr)
        return 2
    
    # Load environment variables
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
    
    logger.info("Starting InfiniteJournal (Simple Mode)")
    logger.info("Configuration: SIZE=%dx%d, FPS=%d", 
               settings.WIDTH, settings.HEIGHT, settings.FPS)

    # Create and run simple application
    try:
        app = create_simple_app(settings)
        logger.info("Simple application created successfully")
        
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