"""
InfiniteJournal Application Entry Point

Clean, modular main.py with Universal Services Framework support.
Eliminates duplication and provides clear, readable application startup.
"""

import logging
import sys
from pathlib import Path
from typing import Any, List, Optional, Protocol, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

MIN_PYTHON_VERSION: Tuple[int, int] = (3, 9)
SUCCESS_EXIT_CODE: int = 0
ERROR_EXIT_CODE: int = 1


class ApplicationError(Exception):
    """Base exception for application errors."""
    pass


class EnvironmentError(ApplicationError):
    """Environment validation failed."""
    pass


class ConfigurationError(ApplicationError):
    """Configuration loading failed."""
    pass


class ApplicationInterface(Protocol):
    """Interface for application instances."""
    
    def run(self) -> None:
        """Run the application."""
        pass
    
    def initialize(self) -> None:
        """Initialize the application if needed."""
        pass


@dataclass
class ApplicationConfig:
    """Application configuration container."""
    width: int = 1280
    height: int = 720
    title: str = 'InfiniteJournal'
    fps: int = 60
    debug: bool = True
    log_level: str = 'INFO'


class EnvironmentValidator:
    """Validates runtime environment requirements."""
    
    @staticmethod
    def validate_python_version() -> None:
        """Ensure Python version meets requirements."""
        current_version = sys.version_info[:2]
        if current_version < MIN_PYTHON_VERSION:
            required = f"{MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}"
            current = f"{current_version[0]}.{current_version[1]}"
            raise EnvironmentError(f"Python {required}+ required, found {current}")
    
    @staticmethod
    def validate_pygame_available() -> None:
        """Ensure pygame is installed."""
        try:
            import pygame
            logger.debug(f"Pygame version: {pygame.version.ver}")
        except ImportError:
            raise EnvironmentError("Pygame not installed. Run: pip install pygame")
    
    @staticmethod
    def validate_environment() -> None:
        """Validate complete environment."""
        EnvironmentValidator.validate_python_version()
        EnvironmentValidator.validate_pygame_available()


class ConfigurationLoader:
    """Loads and manages application configuration."""
    
    @staticmethod
    def load_environment_variables() -> None:
        """Load environment variables from .env file."""
        env_file = Path('.env')
        if env_file.exists():
            load_dotenv(env_file)
            logger.debug(f"Loaded environment from {env_file}")
    
    @staticmethod
    def load_settings(log_level: str) -> Any:
        """Load application settings with fallback support."""
        try:
            return ConfigurationLoader._load_new_config()
        except ImportError:
            return ConfigurationLoader._load_legacy_config()
    
    @staticmethod
    def _load_new_config() -> Any:
        """Load using new configuration system."""
        from config import load_application_configuration, Settings
        logger.debug("Using new configuration system")
        config = load_application_configuration()
        return Settings(config)
    
    @staticmethod
    def _load_legacy_config() -> Any:
        """Load using legacy configuration system."""
        from config import Settings
        logger.debug("Using legacy configuration system")
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            return Settings.load()


class ApplicationFactory:
    """Creates application instances with appropriate framework."""
    
    @staticmethod
    def create_application(settings: Any) -> ApplicationInterface:
        """Create application using best available framework."""
        if ApplicationFactory._universal_services_available():
            return ApplicationFactory._create_modern_application(settings)
        return ApplicationFactory._create_legacy_application(settings)
    
    @staticmethod
    def _universal_services_available() -> bool:
        """Check if Universal Services Framework is available."""
        try:
            from services import create_working_application
            return True
        except ImportError:
            return False
    
    @staticmethod
    def _create_modern_application(settings: Any) -> ApplicationInterface:
        """Create application using Universal Services Framework."""
        from services import create_working_application
        from adapters.pygame_adapter import PygameEngineAdapter
        
        backend = PygameEngineAdapter()
        app = create_working_application(
            backend=backend,
            window_width=getattr(settings, 'WIDTH', 1280),
            window_height=getattr(settings, 'HEIGHT', 720),
            window_title=getattr(settings, 'TITLE', 'InfiniteJournal'),
            target_fps=getattr(settings, 'FPS', 60),
            debug_mode=getattr(settings, 'DEBUG', True)
        )
        
        logger.info("Created application with Universal Services Framework")
        return app
    
    @staticmethod
    def _create_legacy_application(settings: Any) -> ApplicationInterface:
        """Create application using legacy compatibility layer."""
        from bootstrap.factory import create_simple_app
        
        app = create_simple_app(settings)
        logger.info("Created application with legacy compatibility")
        return app


class ApplicationRunner:
    """Orchestrates application startup and execution."""
    
    def __init__(self):
        self.settings: Optional[Any] = None
        self.app: Optional[ApplicationInterface] = None
    
    def initialize_environment(self, log_level: str) -> None:
        """Initialize complete application environment."""
        EnvironmentValidator.validate_environment()
        ConfigurationLoader.load_environment_variables()
        self.settings = ConfigurationLoader.load_settings(log_level)
        self._setup_logging_and_errors()
    
    def _setup_logging_and_errors(self) -> None:
        """Configure logging and error handling."""
        from bootstrap.logging_setup import setup_logging
        from bootstrap.errors import make_exception_hook
        
        setup_logging(self.settings, getattr(self.settings, 'LOG_LEVEL', 'INFO'))
        sys.excepthook = make_exception_hook(self.settings)
        logger.info("Application environment initialized")
    
    def create_application(self) -> None:
        """Create application instance."""
        if not self.settings:
            raise ConfigurationError("Settings not loaded")
        
        self.app = ApplicationFactory.create_application(self.settings)
        self._log_startup_info()
    
    def _log_startup_info(self) -> None:
        """Log application startup information."""
        logger.info("Starting InfiniteJournal")
        logger.info(
            "Configuration: SIZE=%dx%d, FPS=%d, DEBUG=%s",
            getattr(self.settings, 'WIDTH', 1280),
            getattr(self.settings, 'HEIGHT', 720),
            getattr(self.settings, 'FPS', 60),
            getattr(self.settings, 'DEBUG', True)
        )
    
    def run_application(self) -> None:
        """Execute the application."""
        if not self.app:
            raise ApplicationError("Application not created")
        
        if hasattr(self.app, 'initialize'):
            self.app.initialize()
        
        self.app.run()
        logger.info("Application completed successfully")


def parse_command_line_arguments(argv: Optional[List[str]] = None) -> Any:
    """Parse command line arguments."""
    from bootstrap.cli import parse_args
    return parse_args(argv)


def execute_application_startup(log_level: str) -> None:
    """Execute complete application startup sequence."""
    runner = ApplicationRunner()
    runner.initialize_environment(log_level)
    runner.create_application()
    runner.run_application()


def handle_application_error(error: Exception) -> int:
    """Handle application errors with appropriate logging and exit codes."""
    error_message = f"Application failed: {error}"
    
    try:
        logger.error(error_message)
    except:
        print(error_message, file=sys.stderr)
    
    return ERROR_EXIT_CODE


def handle_user_interruption() -> int:
    """Handle user interruption gracefully."""
    message = "Application terminated by user request"
    
    try:
        logger.info(message)
    except:
        print(message, file=sys.stderr)
    
    return SUCCESS_EXIT_CODE


def main(argv: Optional[List[str]] = None) -> int:
    """
    InfiniteJournal application entry point.
    
    Provides clean startup with Universal Services Framework support
    and graceful error handling.
    """
    try:
        args = parse_command_line_arguments(argv)
        log_level = args.log_level or 'INFO'
        execute_application_startup(log_level)
        return SUCCESS_EXIT_CODE
        
    except KeyboardInterrupt:
        return handle_user_interruption()
    
    except Exception as error:
        return handle_application_error(error)


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)