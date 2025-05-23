"""
Fixed main.py for Universal Services Framework Migration
======================================================

This replaces your existing main.py to work with the Universal Services Framework.
Eliminates service initialization errors and provides working drawing functionality.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# Import from new Universal Services Framework
try:
    from services import (
        create_working_application,  # Use working version instead
        ApplicationSettings,
        create_memory_storage,
        ValidationService
    )
    UNIVERSAL_SERVICES_AVAILABLE = True
except ImportError:
    # Fallback for gradual migration
    UNIVERSAL_SERVICES_AVAILABLE = False

# Keep existing imports for compatibility
from bootstrap.cli import parse_args
from bootstrap.errors import StartupError, make_exception_hook
from bootstrap.logging_setup import setup_logging

# Handle the deprecated Settings.load()
try:
    from config import load_application_configuration, Settings
    USE_NEW_CONFIG = True
except ImportError:
    from config import Settings
    USE_NEW_CONFIG = False

MIN_PYTHON_VERSION: Tuple[int, int] = (3, 9)
SUCCESS_EXIT_CODE: int = 0
APPLICATION_ERROR_EXIT_CODE: int = 1
STARTUP_ERROR_EXIT_CODE: int = 2

logger = logging.getLogger(__name__)


class ApplicationError(Exception):
    """Base exception for application-level errors."""
    pass


class ApplicationStartupError(ApplicationError):
    """Raised when application fails to start properly."""
    pass


def validate_environment() -> None:
    """Validate basic environment requirements."""
    # Check Python version
    current_version = sys.version_info[:2]
    if current_version < MIN_PYTHON_VERSION:
        raise ApplicationStartupError(
            f"Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+ required, "
            f"found {current_version[0]}.{current_version[1]}"
        )
    
    # Check required packages
    try:
        import pygame
        logger.debug(f"Pygame version: {pygame.version.ver}")
    except ImportError:
        raise ApplicationStartupError("Pygame not installed. Run: pip install pygame")


def load_environment_variables() -> None:
    """Load environment variables from .env file if present."""
    env_file = Path('.env')
    if env_file.exists():
        load_dotenv(env_file)
        logger.debug(f"Loaded environment from {env_file}")


def create_application_with_working_services(settings) -> Any:
    """Create application using Working Services Framework."""
    try:
        # Import pygame adapter
        from adapters.pygame_adapter import PygameEngineAdapter
        
        # Create backend
        backend = PygameEngineAdapter()
        
        # Create working application (bypasses service initialization issues)
        app = create_working_application(
            backend=backend,
            window_width=getattr(settings, 'WIDTH', 1280),
            window_height=getattr(settings, 'HEIGHT', 720),
            window_title=getattr(settings, 'TITLE', 'InfiniteJournal'),
            target_fps=getattr(settings, 'FPS', 60),
            debug_mode=getattr(settings, 'DEBUG', False)
        )
        
        logger.info("Created application with Working Services Framework")
        return app
        
    except Exception as error:
        logger.error(f"Failed to create Working Services application: {error}")
        raise ApplicationStartupError(f"Working Services creation failed: {error}") from error


def create_application_with_legacy_compatibility(settings) -> Any:
    """Create application with legacy compatibility layer."""
    try:
        # Create a compatibility bridge for the old services.app
        from bootstrap.factory import create_simple_app
        
        # This will work with your existing bootstrap system
        app = create_simple_app(settings)
        
        logger.info("Created application with legacy compatibility")
        return app
        
    except Exception as error:
        logger.error(f"Failed to create legacy compatible application: {error}")
        raise ApplicationStartupError(f"Legacy app creation failed: {error}") from error


def create_application_based_on_availability(settings) -> Any:
    """Create application based on what's available."""
    if UNIVERSAL_SERVICES_AVAILABLE:
        logger.info("Using Working Services Framework")
        return create_application_with_working_services(settings)
    else:
        logger.info("Using legacy compatibility mode")
        return create_application_with_legacy_compatibility(settings)


def load_application_settings(console_log_level: str):
    """Load application settings with proper handling."""
    try:
        if USE_NEW_CONFIG:
            # Use new configuration system
            logger.debug("Using new configuration system")
            config = load_application_configuration()
            settings = Settings(config)  # Convert to legacy Settings for compatibility
        else:
            # Use legacy Settings.load() but handle deprecation
            logger.debug("Using legacy configuration system")
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                settings = Settings.load()
        
        return settings
        
    except Exception as error:
        logger.error(f"Failed to load settings: {error}")
        raise ApplicationStartupError(f"Settings loading failed: {error}") from error


def initialize_application_environment(console_log_level: str):
    """Initialize complete application environment."""
    try:
        # Validate environment
        validate_environment()
        
        # Load environment variables
        load_environment_variables()
        
        # Load settings
        settings = load_application_settings(console_log_level)
        
        # Setup logging
        setup_logging(settings, console_log_level)
        
        # Install global error handler
        sys.excepthook = make_exception_hook(settings)
        
        logger.info("Application environment initialized successfully")
        return settings
        
    except Exception as error:
        logger.error(f"Environment initialization failed: {error}")
        raise ApplicationStartupError(f"Environment initialization failed: {error}") from error


def run_application(settings) -> None:
    """Create and run the application."""
    try:
        # Create application
        app = create_application_based_on_availability(settings)
        
        # Log startup information
        logger.info("Starting InfiniteJournal")
        logger.info(
            "Configuration: SIZE=%dx%d, FPS=%d, DEBUG=%s",
            getattr(settings, 'WIDTH', 1280),
            getattr(settings, 'HEIGHT', 720),
            getattr(settings, 'FPS', 60),
            getattr(settings, 'DEBUG', False)
        )
        
        # Run application
        if hasattr(app, 'initialize'):
            # Working Services Framework app
            app.initialize()
            app.run()
        else:
            # Legacy app
            app.run()
        
        logger.info("Application completed successfully")
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as error:
        logger.error(f"Application runtime error: {error}")
        raise ApplicationStartupError(f"Application execution failed: {error}") from error


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main application entry point with Working Services Framework support.
    
    This version handles proper service initialization and provides working drawing functionality.
    """
    try:
        # Parse command line arguments
        args = parse_args(argv)
        
        # Initialize environment
        settings = initialize_application_environment(args.log_level or 'INFO')
        
        # Run application
        run_application(settings)
        
        return SUCCESS_EXIT_CODE
        
    except ApplicationStartupError as startup_error:
        # Log startup errors
        try:
            logger.error(f"Application startup failed: {startup_error}")
        except:
            print(f"Application startup failed: {startup_error}", file=sys.stderr)
        return STARTUP_ERROR_EXIT_CODE
        
    except KeyboardInterrupt:
        try:
            logger.info("Application terminated by user request")
        except:
            print("Application terminated by user request", file=sys.stderr)
        return SUCCESS_EXIT_CODE
        
    except Exception as unexpected_error:
        try:
            logger.exception("Unexpected error in main application execution")
        except:
            print(f"Unexpected application error: {unexpected_error}", file=sys.stderr)
        return APPLICATION_ERROR_EXIT_CODE


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)