"""
Production-ready application bootstrap with enterprise-grade lifecycle management.
This module provides comprehensive application startup framework featuring
environment validation, configuration management, logging setup, and graceful
error handling. Designed for production deployment with extensive monitoring
and debugging capabilities.

Example:
   Basic usage:
       python main.py
   
   With custom logging:
       python main.py --log-level DEBUG
   
   Programmatic usage:
       exit_code = main(['--log-level', 'INFO'])
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

from bootstrap.cli import parse_args
from bootstrap.errors import StartupError, make_exception_hook
from bootstrap.factory import create_simple_app
from bootstrap.logging_setup import setup_logging
from config import ConfigurationError, Settings

MIN_PYTHON_VERSION: Tuple[int, int] = (3, 9)
REQUIRED_PACKAGES: Tuple[str, ...] = ('pygame',)
TEST_FILE_NAME: str = 'write_test.tmp'
DEFAULT_ENV_FILE: str = '.env'
SUCCESS_EXIT_CODE: int = 0
APPLICATION_ERROR_EXIT_CODE: int = 1
STARTUP_ERROR_EXIT_CODE: int = 2

logger = logging.getLogger(__name__)


class ApplicationError(Exception):
    """Base exception for all application-level errors with enhanced context."""
    
    def __init__(self, message: str, cause: Optional[Exception] = None) -> None:
        """Initialize application error with detailed context information.
        
        Args:
            message: Human-readable error description for logging and debugging.
            cause: Optional underlying exception that triggered this error.
        """
        super().__init__(message)
        self.cause = cause
        self.context: Dict[str, Any] = {}


class EnvironmentValidationError(ApplicationError):
    """Raised when system environment validation fails critical requirements."""
    pass


class ApplicationStartupError(ApplicationError):
    """Raised when application fails to start properly during initialization."""
    pass


class PythonVersionValidator:
    """Validates Python interpreter version against minimum requirements."""
    
    def __init__(self, min_version: Tuple[int, int] = MIN_PYTHON_VERSION) -> None:
        """Initialize validator with version requirements.
        
        Args:
            min_version: Minimum Python version as (major, minor) tuple.
        """
        self._min_version = min_version
        logger.debug(f"Python version validator configured for {min_version}")
    
    def validate(self) -> None:
        """Validate current Python version meets minimum requirements.
        
        Raises:
            EnvironmentValidationError: If current version is insufficient.
        """
        current_version = sys.version_info[:2]
        
        if current_version < self._min_version:
            error_message = self._build_version_error_message(current_version)
            logger.error(error_message)
            raise EnvironmentValidationError(error_message)
        
        logger.debug(f"Python version {current_version} validated successfully")
    
    def _build_version_error_message(self, current: Tuple[int, int]) -> str:
        """Build descriptive version error message for user feedback.
        
        Args:
            current: Current Python version that failed validation.
            
        Returns:
            Formatted error message with upgrade instructions.
        """
        min_version_str = f"{self._min_version[0]}.{self._min_version[1]}"
        current_version_str = f"{current[0]}.{current[1]}"
        return f"Python {min_version_str}+ required, found {current_version_str}"


class PackageValidator:
    """Validates required Python packages are installed and importable."""
    
    def __init__(self, required_packages: Tuple[str, ...] = REQUIRED_PACKAGES) -> None:
        """Initialize validator with package requirements.
        
        Args:
            required_packages: Tuple of required package names to validate.
        """
        self._required_packages = required_packages
        logger.debug(f"Package validator configured for {required_packages}")
    
    def validate(self) -> None:
        """Validate all required packages are available for import.
        
        Raises:
            EnvironmentValidationError: If any required packages are missing.
        """
        missing_packages = self._find_missing_packages()
        
        if missing_packages:
            error_message = self._build_missing_packages_error(missing_packages)
            logger.error(f"Missing required packages: {missing_packages}")
            raise EnvironmentValidationError(error_message)
        
        logger.debug("All required packages validated successfully")
    
    def _find_missing_packages(self) -> List[str]:
        """Identify packages that cannot be imported successfully.
        
        Returns:
            List of package names that failed import validation.
        """
        missing_packages = []
        
        for package_name in self._required_packages:
            if not self._test_package_import(package_name):
                missing_packages.append(package_name)
        
        return missing_packages
    
    def _test_package_import(self, package_name: str) -> bool:
        """Test if a package can be imported without errors.
        
        Args:
            package_name: Name of package to test for import capability.
            
        Returns:
            True if package imports successfully, False otherwise.
        """
        try:
            __import__(package_name)
            logger.debug(f"Package '{package_name}' import validated")
            return True
        except ImportError:
            logger.debug(f"Package '{package_name}' not available for import")
            return False
    
    def _build_missing_packages_error(self, missing_packages: List[str]) -> str:
        """Build error message with installation instructions.
        
        Args:
            missing_packages: List of missing package names.
            
        Returns:
            Formatted error message with pip install commands.
        """
        packages_list = ', '.join(missing_packages)
        install_command = ' '.join(missing_packages)
        return (
            f"Missing required packages: {packages_list}. "
            f"Install with: pip install {install_command}"
        )


class FileSystemValidator:
    """Validates file system permissions and access requirements."""
    
    def __init__(self, test_file: str = TEST_FILE_NAME) -> None:
        """Initialize validator with test file configuration.
        
        Args:
            test_file: Name of temporary file for permission testing.
        """
        self._test_file_path = Path(test_file)
        logger.debug(f"File system validator configured with test file: {test_file}")
    
    def validate(self) -> None:
        """Validate write permissions in current directory.
        
        Raises:
            EnvironmentValidationError: If write permissions are insufficient.
        """
        try:
            self._execute_write_permission_test()
            logger.debug("File system write permissions validated successfully")
        except PermissionError as permission_error:
            self._handle_permission_denied(permission_error)
        except OSError as os_error:
            self._handle_filesystem_error(os_error)
    
    def _execute_write_permission_test(self) -> None:
        """Test write access by creating and removing temporary file.
        
        Raises:
            PermissionError: If write access is denied by system.
            OSError: If file system operation fails unexpectedly.
        """
        self._test_file_path.write_text("permission_test", encoding='utf-8')
        self._test_file_path.unlink()
    
    def _handle_permission_denied(self, error: PermissionError) -> None:
        """Handle permission-related errors with detailed logging.
        
        Args:
            error: Permission error that occurred during validation.
            
        Raises:
            EnvironmentValidationError: With user-friendly error message.
        """
        error_message = "Insufficient write permissions in current directory"
        logger.error(f"{error_message}: {error}")
        raise EnvironmentValidationError(error_message) from error
    
    def _handle_filesystem_error(self, error: OSError) -> None:
        """Handle OS-level errors with detailed logging and context.
        
        Args:
            error: OS error that occurred during validation.
            
        Raises:
            EnvironmentValidationError: With detailed error context.
        """
        error_message = f"File system access error: {error}"
        logger.error(error_message)
        raise EnvironmentValidationError(error_message) from error


class EnvironmentValidator:
    """Comprehensive system environment validator with detailed reporting."""
    
    def __init__(self) -> None:
        """Initialize validator with all required sub-validators."""
        self._python_validator = PythonVersionValidator()
        self._package_validator = PackageValidator()
        self._filesystem_validator = FileSystemValidator()
        self._validation_results: Dict[str, bool] = {}
        logger.debug("Environment validator initialized with all sub-validators")
    
    def validate_complete_environment(self) -> None:
        """Perform comprehensive environment validation with detailed tracking.
        
        Validates Python version, required packages, and file system permissions
        while maintaining validation state for debugging and reporting purposes.
        
        Raises:
            EnvironmentValidationError: If any validation check fails.
        """
        try:
            self._validate_python_version()
            self._validate_package_dependencies()
            self._validate_filesystem_access()
            
            logger.info("Complete environment validation successful")
            
        except EnvironmentValidationError:
            logger.error("Environment validation failed at critical checkpoint")
            raise
        except Exception as unexpected_error:
            self._handle_validation_failure(unexpected_error)
    
    def _validate_python_version(self) -> None:
        """Validate Python version and record successful result."""
        self._python_validator.validate()
        self._validation_results['python_version'] = True
    
    def _validate_package_dependencies(self) -> None:
        """Validate required packages and record successful result."""
        self._package_validator.validate()
        self._validation_results['required_packages'] = True
    
    def _validate_filesystem_access(self) -> None:
        """Validate file system permissions and record successful result."""
        self._filesystem_validator.validate()
        self._validation_results['file_permissions'] = True
    
    def _handle_validation_failure(self, error: Exception) -> None:
        """Handle unexpected errors during validation process.
        
        Args:
            error: Unexpected exception that occurred during validation.
            
        Raises:
            EnvironmentValidationError: With detailed error context.
        """
        error_message = f"Validation failed unexpectedly: {error}"
        logger.error(f"Unexpected error during environment validation: {error}")
        raise EnvironmentValidationError(error_message) from error


class EnvironmentLoader:
    """Manages loading and validation of environment variables from files."""
    
    def __init__(self, env_file_path: Optional[Path] = None) -> None:
        """Initialize loader with configurable environment file path.
        
        Args:
            env_file_path: Custom path to environment file, defaults to '.env'.
        """
        self._env_file_path = env_file_path or Path(DEFAULT_ENV_FILE)
        logger.debug(f"Environment loader configured with path: {self._env_file_path}")
    
    def load_environment_variables(self) -> bool:
        """Load environment variables from file if available.
        
        Returns:
            True if environment file was successfully loaded, False if not found.
            
        Raises:
            EnvironmentValidationError: If file exists but loading fails.
        """
        if not self._env_file_path.exists():
            logger.debug(f"Environment file {self._env_file_path} not found, skipping load")
            return False
        
        return self._load_existing_environment_file()
    
    def _load_existing_environment_file(self) -> bool:
        """Load environment file with comprehensive error handling.
        
        Returns:
            True if file loaded successfully without errors.
            
        Raises:
            EnvironmentValidationError: If file loading encounters errors.
        """
        try:
            load_dotenv(self._env_file_path)
            logger.info(f"Environment variables loaded from {self._env_file_path}")
            return True
        except Exception as loading_error:
            self._handle_loading_failure(loading_error)
    
    def _handle_loading_failure(self, error: Exception) -> None:
        """Handle errors that occur during environment file loading.
        
        Args:
            error: Exception that occurred during environment loading.
            
        Raises:
            EnvironmentValidationError: With detailed error context.
        """
        error_message = f"Failed to load environment file {self._env_file_path}: {error}"
        logger.error(error_message)
        raise EnvironmentValidationError(error_message) from error


class ConfigurationManager:
    """Manages application configuration loading with comprehensive validation."""
    
    def __init__(self) -> None:
        """Initialize configuration manager for application settings."""
        logger.debug("Configuration manager initialized for settings management")
    
    def load_application_settings(self) -> Settings:
        """Load and validate complete application configuration.
        
        Returns:
            Validated application settings object ready for use.
            
        Raises:
            ConfigurationError: If configuration loading or validation fails.
        """
        try:
            logger.debug("Starting application configuration loading process")
            settings = Settings.load()
            logger.info("Application configuration loaded and validated successfully")
            return settings
        except ConfigurationError:
            logger.error("Configuration loading failed validation")
            raise
        except Exception as unexpected_error:
            self._handle_configuration_failure(unexpected_error)
    
    def _handle_configuration_failure(self, error: Exception) -> None:
        """Handle unexpected errors during configuration loading.
        
        Args:
            error: Unexpected exception during configuration process.
            
        Raises:
            ConfigurationError: With detailed error context and cause.
        """
        error_message = f"Configuration loading failed unexpectedly: {error}"
        logger.error(f"Unexpected configuration error: {error}")
        raise ConfigurationError(error_message) from error


class LoggingManager:
    """Manages application logging configuration with enterprise-grade setup."""
    
    def __init__(self) -> None:
        """Initialize logging manager for application-wide logging control."""
        logger.debug("Logging manager initialized for application logging control")
    
    def setup_application_logging(self, settings: Settings, console_level: str) -> None:
        """Configure comprehensive application logging system.
        
        Args:
            settings: Application settings containing logging configuration.
            console_level: Console logging level as string specification.
            
        Raises:
            StartupError: If logging setup encounters configuration errors.
        """
        try:
            numeric_level = self._parse_log_level(console_level)
            setup_logging(settings, numeric_level)
            logger.info(f"Logging system configured with console level: {console_level}")
        except StartupError:
            logger.error("Logging setup failed during configuration")
            raise
        except Exception as setup_error:
            self._handle_logging_failure(setup_error)
    
    def _parse_log_level(self, level_string: str) -> int:
        """Convert string log level to numeric logging constant.
        
        Args:
            level_string: Logging level as string (DEBUG, INFO, WARNING, ERROR).
            
        Returns:
            Numeric logging level constant for configuration.
        """
        return getattr(logging, level_string.upper(), logging.INFO)
    
    def _handle_logging_failure(self, error: Exception) -> None:
        """Handle unexpected errors during logging setup process.
        
        Args:
            error: Exception that occurred during logging configuration.
            
        Raises:
            StartupError: With detailed error context and cause.
        """
        error_message = f"Logging configuration failed unexpectedly: {error}"
        logger.error(f"Unexpected logging setup error: {error}")
        raise StartupError(error_message) from error


class GlobalErrorHandler:
    """Manages global exception handling for unhandled application errors."""
    
    def __init__(self) -> None:
        """Initialize global error handler for application-wide error management."""
        logger.debug("Global error handler initialized for application error management")
    
    def install_exception_handler(self, settings: Settings) -> None:
        """Install global exception handler for unhandled application errors.
        
        Args:
            settings: Application settings for error handler configuration.
            
        Raises:
            StartupError: If exception handler installation fails.
        """
        try:
            sys.excepthook = make_exception_hook(settings)
            logger.debug("Global exception handler installed successfully")
        except Exception as installation_error:
            self._handle_installation_failure(installation_error)
    
    def _handle_installation_failure(self, error: Exception) -> None:
        """Handle errors during exception handler installation.
        
        Args:
            error: Exception that occurred during handler installation.
            
        Raises:
            StartupError: With detailed error context and cause.
        """
        error_message = f"Exception handler setup failed: {error}"
        logger.error(f"Failed to install global exception handler: {error}")
        raise StartupError(error_message) from error


class ApplicationLifecycleManager:
    """Manages complete application lifecycle with comprehensive error handling."""
    
    def __init__(self) -> None:
        """Initialize lifecycle manager with all required components."""
        self._environment_validator = EnvironmentValidator()
        self._environment_loader = EnvironmentLoader()
        self._configuration_manager = ConfigurationManager()
        self._logging_manager = LoggingManager()
        self._error_handler = GlobalErrorHandler()
        self._settings: Optional[Settings] = None
        logger.debug("Application lifecycle manager initialized with all components")
    
    def initialize_application_environment(self, console_log_level: str) -> Settings:
        """Initialize complete application environment with comprehensive setup.
        
        Performs environment validation, configuration loading, logging setup,
        and error handler installation in the correct dependency sequence.
        
        Args:
            console_log_level: Logging level for console output configuration.
            
        Returns:
            Fully configured application settings object.
            
        Raises:
            ApplicationStartupError: If initialization fails at any critical stage.
        """
        try:
            self._validate_system_environment()
            self._load_environment_variables()
            settings = self._load_configuration_settings()
            self._setup_logging_system(settings, console_log_level)
            self._install_error_handling(settings)
            
            self._settings = settings
            logger.info("Application environment initialization completed successfully")
            return settings
            
        except (EnvironmentValidationError, ConfigurationError) as known_error:
            self._handle_initialization_error(known_error)
        except Exception as unexpected_error:
            self._handle_unexpected_initialization_error(unexpected_error)
    
    def create_and_run_application(self, settings: Settings) -> None:
        """Create and execute the main application with comprehensive monitoring.
        
        Args:
            settings: Fully configured application settings.
            
        Raises:
            ApplicationStartupError: If application creation or execution fails.
        """
        try:
            application = self._create_application_instance(settings)
            self._log_startup_configuration(settings)
            self._execute_application_instance(application)
            
            logger.info("Application execution completed successfully")
            
        except StartupError as startup_error:
            self._handle_startup_failure(startup_error)
        except KeyboardInterrupt:
            logger.info("Application execution interrupted by user request")
            raise
        except Exception as execution_error:
            self._handle_execution_failure(execution_error)
    
    def _validate_system_environment(self) -> None:
        """Perform comprehensive system environment validation."""
        logger.debug("Starting comprehensive environment validation")
        self._environment_validator.validate_complete_environment()
    
    def _load_environment_variables(self) -> None:
        """Load environment variables from configuration files."""
        logger.debug("Loading environment variables from configuration")
        self._environment_loader.load_environment_variables()
    
    def _load_configuration_settings(self) -> Settings:
        """Load and validate application configuration settings.
        
        Returns:
            Loaded and validated application settings object.
        """
        return self._configuration_manager.load_application_settings()
    
    def _setup_logging_system(self, settings: Settings, console_level: str) -> None:
        """Configure comprehensive application logging system.
        
        Args:
            settings: Application settings for logging configuration.
            console_level: Console logging level specification.
        """
        self._logging_manager.setup_application_logging(settings, console_level)
    
    def _install_error_handling(self, settings: Settings) -> None:
        """Install global error handling for unhandled exceptions.
        
        Args:
            settings: Application settings for error handler configuration.
        """
        self._error_handler.install_exception_handler(settings)
    
    def _create_application_instance(self, settings: Settings) -> Any:
        """Create main application instance ready for execution.
        
        Args:
            settings: Application settings for instance creation.
            
        Returns:
            Configured application instance ready for execution.
        """
        application = create_simple_app(settings)
        logger.info("Application instance created successfully")
        return application
    
    def _execute_application_instance(self, application: Any) -> None:
        """Execute the configured application instance.
        
        Args:
            application: Configured application instance to execute.
        """
        application.run()
    
    def _log_startup_configuration(self, settings: Settings) -> None:
        """Log important application configuration for debugging and monitoring.
        
        Args:
            settings: Application settings to log for operational visibility.
        """
        logger.info("Starting InfiniteJournal (Simple Mode)")
        logger.info(
            "Application configuration: SIZE=%dx%d, FPS=%d, DEBUG=%s",
            settings.WIDTH,
            settings.HEIGHT,
            settings.FPS,
            settings.DEBUG
        )
    
    def _handle_initialization_error(self, error: Exception) -> None:
        """Handle known initialization errors with detailed logging.
        
        Args:
            error: Known initialization error with specific context.
            
        Raises:
            ApplicationStartupError: With detailed error context.
        """
        error_message = f"Application initialization failed: {error}"
        logger.error(error_message)
        raise ApplicationStartupError(error_message) from error
    
    def _handle_unexpected_initialization_error(self, error: Exception) -> None:
        """Handle unexpected initialization errors with comprehensive logging.
        
        Args:
            error: Unexpected error during initialization process.
            
        Raises:
            ApplicationStartupError: With detailed error context.
        """
        error_message = f"Unexpected initialization error: {error}"
        logger.error(f"Unexpected error during application initialization: {error}")
        raise ApplicationStartupError(error_message) from error
    
    def _handle_startup_failure(self, error: StartupError) -> None:
        """Handle application startup errors with detailed logging.
        
        Args:
            error: Startup error that occurred during application creation.
            
        Raises:
            ApplicationStartupError: With detailed error context.
        """
        error_message = f"Application startup failed: {error}"
        logger.error(error_message)
        raise ApplicationStartupError(error_message) from error
    
    def _handle_execution_failure(self, error: Exception) -> None:
        """Handle application execution errors with comprehensive logging.
        
        Args:
            error: Exception that occurred during application execution.
            
        Raises:
            ApplicationStartupError: With detailed error context.
        """
        logger.exception("Unexpected error during application execution")
        error_message = f"Application execution failed: {error}"
        raise ApplicationStartupError(error_message) from error


class ArgumentProcessor:
    """Processes and validates command-line arguments for application configuration."""
    
    def __init__(self) -> None:
        """Initialize argument processor for command-line parameter handling."""
        logger.debug("Argument processor initialized for command-line handling")
    
    def parse_command_arguments(self, argv: Optional[List[str]] = None) -> Any:
        """Parse and validate command-line arguments with comprehensive error handling.
        
        Args:
            argv: Optional command-line arguments, uses sys.argv if not provided.
            
        Returns:
            Parsed arguments object with validated parameters.
            
        Raises:
            ApplicationStartupError: If argument parsing fails or exits abnormally.
        """
        try:
            logger.debug("Starting command-line argument parsing process")
            arguments = parse_args(argv)
            logger.info("Command-line arguments parsed and validated successfully")
            return arguments
        except SystemExit as system_exit:
            self._handle_system_exit(system_exit)
        except Exception as parsing_error:
            self._handle_parsing_failure(parsing_error)
    
    def _handle_system_exit(self, exit_exception: SystemExit) -> None:
        """Handle system exit during argument parsing process.
        
        Args:
            exit_exception: SystemExit exception from argument parser.
            
        Raises:
            ApplicationStartupError: With exit code context information.
        """
        exit_code = exit_exception.code or 0
        error_message = f"Argument parsing exit: {exit_code}"
        
        if exit_code != 0:
            logger.error(f"Argument parsing failed with exit code: {exit_code}")
        
        raise ApplicationStartupError(error_message) from exit_exception
    
    def _handle_parsing_failure(self, error: Exception) -> None:
        """Handle unexpected errors during argument parsing.
        
        Args:
            error: Unexpected exception during argument parsing.
            
        Raises:
            ApplicationStartupError: With detailed error context.
        """
        error_message = f"Argument parsing failed unexpectedly: {error}"
        logger.error(f"Unexpected argument parsing error: {error}")
        raise ApplicationStartupError(error_message) from error


class ErrorRecoveryManager:
    """Manages error logging and recovery strategies with fallback mechanisms."""
    
    @staticmethod
    def log_startup_error(error: ApplicationStartupError) -> None:
        """Log startup error with stderr fallback if logging unavailable.
        
        Args:
            error: Application startup error requiring logging with recovery.
        """
        error_message = f"Application startup failed: {error}"
        
        try:
            logger.error(error_message)
        except Exception:
            print(error_message, file=sys.stderr)
    
    @staticmethod
    def log_keyboard_interrupt() -> None:
        """Log user interruption with stderr fallback for resilience."""
        try:
            logger.info("Application terminated by user request")
        except Exception:
            print("Application terminated by user request", file=sys.stderr)
    
    @staticmethod
    def log_unexpected_error(error: Exception) -> None:
        """Log unexpected error with stderr fallback and detailed context.
        
        Args:
            error: Unexpected exception requiring logging with recovery.
        """
        error_message = f"Unexpected application error: {error}"
        
        try:
            logger.exception("Unexpected error in main application execution")
        except Exception:
            print(error_message, file=sys.stderr)


def main(argv: Optional[List[str]] = None) -> int:
    """Production-ready application entry point with enterprise-grade error handling.
    
    Manages complete application lifecycle including environment validation,
    configuration loading, logging setup, and graceful error recovery with
    comprehensive monitoring capabilities for production deployment.
    
    Args:
        argv: Optional command-line arguments for testing, uses sys.argv if None.
        
    Returns:
        Exit code indicating application execution result:
        - 0: Successful execution without errors
        - 1: Application runtime error during execution
        - 2: Startup or initialization error before execution
        
    Example:
        Normal production execution:
            >>> exit_code = main()
            >>> print(f"Application exited with code: {exit_code}")
        
        Testing with custom arguments:
            >>> exit_code = main(['--log-level', 'DEBUG'])
            >>> assert exit_code == 0
    """
    try:
        argument_processor = ArgumentProcessor()
        parsed_arguments = argument_processor.parse_command_arguments(argv)
        
        lifecycle_manager = ApplicationLifecycleManager()
        application_settings = lifecycle_manager.initialize_application_environment(
            parsed_arguments.log_level or 'INFO'
        )
        
        lifecycle_manager.create_and_run_application(application_settings)
        
        return SUCCESS_EXIT_CODE
        
    except ApplicationStartupError as startup_error:
        ErrorRecoveryManager.log_startup_error(startup_error)
        return STARTUP_ERROR_EXIT_CODE
        
    except KeyboardInterrupt:
        ErrorRecoveryManager.log_keyboard_interrupt()
        return SUCCESS_EXIT_CODE
        
    except Exception as unexpected_error:
        ErrorRecoveryManager.log_unexpected_error(unexpected_error)
        return APPLICATION_ERROR_EXIT_CODE


if __name__ == '__main__':
    sys.exit(main())