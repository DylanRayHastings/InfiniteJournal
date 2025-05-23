"""
Fixed main.py for Universal Services Framework Migration
======================================================

This replaces your existing main.py to work with the Universal Services Framework.
Eliminates the 'No module named services.app' error and modernizes the bootstrap process.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# Import from new Universal Services Framework
try:
    from services import (
        create_complete_application,
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


def create_application_with_universal_services(settings) -> Any:
    """Create application using Universal Services Framework."""
    try:
        # Import pygame adapter
        from adapters.pygame_adapter import PygameEngineAdapter
        
        # Create backend
        backend = PygameEngineAdapter()
        
        # Convert old settings to new ApplicationSettings
        app_settings = ApplicationSettings(
            window_width=getattr(settings, 'WIDTH', 1280),
            window_height=getattr(settings, 'HEIGHT', 720),
            window_title=getattr(settings, 'TITLE', 'InfiniteJournal'),
            target_fps=getattr(settings, 'FPS', 60),
            debug_mode=getattr(settings, 'DEBUG', False),
            default_brush_size=getattr(settings, 'BRUSH_SIZE_MIN', 5),
            stroke_smoothing=getattr(settings, 'STROKE_SMOOTHING', True),
            data_directory=Path(getattr(settings, 'DATA_PATH', './data'))
        )
        
        # Create storage
        storage = create_memory_storage("main_app")
        
        # Create validation service
        validation_service = ValidationService()
        
        # Create complete application
        app = create_complete_application(
            backend=backend,
            window_width=app_settings.window_width,
            window_height=app_settings.window_height,
            window_title=app_settings.window_title,
            target_fps=app_settings.target_fps,
            debug_mode=app_settings.debug_mode
        )
        
        logger.info("Created application with Universal Services Framework")
        return app
        
    except Exception as error:
        logger.error(f"Failed to create Universal Services application: {error}")
        raise ApplicationStartupError(f"Universal Services creation failed: {error}") from error


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
        logger.info("Using Universal Services Framework")
        return create_application_with_universal_services(settings)
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
            # Universal Services Framework app
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
    Main application entry point with Universal Services Framework support.
    
    This version handles both the new Universal Services Framework and
    legacy compatibility for gradual migration.
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