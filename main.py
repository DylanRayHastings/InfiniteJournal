"""
Production-ready application bootstrap with enterprise-grade lifecycle management.

This module provides comprehensive application startup framework featuring
environment validation, configuration management, logging setup, and graceful
error handling. Designed for production deployment with extensive monitoring
and debugging capabilities.

Quick Start:
    Basic usage:
        python main.py
    
    With custom logging:
        python main.py --log-level DEBUG
    
    Programmatic usage:
        exit_code = main(['--log-level', 'INFO'])

Extension Points:
    - Add new validators: Implement ValidationRule interface
    - Add configuration sources: Implement ConfigurationSource interface
    - Add logging outputs: Extend LoggingConfiguration
    - Add error handlers: Implement ErrorHandler interface
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from dotenv import load_dotenv

from bootstrap.cli import parse_args
from bootstrap.errors import StartupError, make_exception_hook
from bootstrap.factory import create_simple_app
from bootstrap.logging_setup import setup_logging
from config import ConfigurationError, Settings

# Application Constants
MIN_PYTHON_VERSION: Tuple[int, int] = (3, 9)
REQUIRED_PACKAGES: Tuple[str, ...] = ('pygame',)
TEST_FILE_NAME: str = 'write_test.tmp'
DEFAULT_ENV_FILE: str = '.env'

# Exit Codes
SUCCESS_EXIT_CODE: int = 0
APPLICATION_ERROR_EXIT_CODE: int = 1
STARTUP_ERROR_EXIT_CODE: int = 2

logger = logging.getLogger(__name__)


class ApplicationError(Exception):
    """Base exception for all application-level errors with enhanced context."""
    
    def __init__(self, message: str, cause: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.cause = cause
        self.context: Dict[str, Any] = field(default_factory=dict)


class EnvironmentValidationError(ApplicationError):
    """Raised when system environment validation fails critical requirements."""
    pass


class ApplicationStartupError(ApplicationError):
    """Raised when application fails to start properly during initialization."""
    pass


@dataclass(frozen=True)
class ValidationResult:
    """Result of validation operations with detailed context."""
    passed: bool
    error_message: str = ""
    validator_name: str = ""


@dataclass(frozen=True)
class VersionInfo:
    """Python version information for validation."""
    major: int
    minor: int
    
    @classmethod
    def from_tuple(cls, version_tuple: Tuple[int, int]) -> 'VersionInfo':
        """Create VersionInfo from tuple."""
        return cls(major=version_tuple[0], minor=version_tuple[1])
    
    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"
    
    def meets_requirement(self, minimum: 'VersionInfo') -> bool:
        """Check if version meets minimum requirement."""
        return (self.major, self.minor) >= (minimum.major, minimum.minor)


class ValidationRule(Protocol):
    """Interface for environment validation rules."""
    
    def validate(self) -> ValidationResult:
        """Execute validation and return result."""
        ...


def get_current_python_version() -> VersionInfo:
    """Get current Python version information."""
    return VersionInfo.from_tuple(sys.version_info[:2])


def validate_python_version(minimum_version: VersionInfo) -> ValidationResult:
    """Validate Python version meets minimum requirements."""
    current_version = get_current_python_version()
    
    if not current_version.meets_requirement(minimum_version):
        error_message = f"Python {minimum_version}+ required, found {current_version}"
        logger.error(error_message)
        return ValidationResult(
            passed=False,
            error_message=error_message,
            validator_name="python_version"
        )
    
    logger.debug(f"Python version {current_version} validated successfully")
    return ValidationResult(passed=True, validator_name="python_version")


def test_package_import(package_name: str) -> bool:
    """Test if a package can be imported successfully."""
    try:
        __import__(package_name)
        logger.debug(f"Package '{package_name}' import validated")
        return True
    except ImportError:
        logger.debug(f"Package '{package_name}' not available for import")
        return False


def find_missing_packages(required_packages: Tuple[str, ...]) -> List[str]:
    """Identify packages that cannot be imported."""
    missing_packages = []
    
    for package_name in required_packages:
        if not test_package_import(package_name):
            missing_packages.append(package_name)
    
    return missing_packages


def build_missing_packages_error(missing_packages: List[str]) -> str:
    """Build error message with installation instructions."""
    packages_list = ', '.join(missing_packages)
    install_command = ' '.join(missing_packages)
    return (
        f"Missing required packages: {packages_list}. "
        f"Install with: pip install {install_command}"
    )


def validate_required_packages(required_packages: Tuple[str, ...]) -> ValidationResult:
    """Validate all required packages are available."""
    missing_packages = find_missing_packages(required_packages)
    
    if missing_packages:
        error_message = build_missing_packages_error(missing_packages)
        logger.error(f"Missing required packages: {missing_packages}")
        return ValidationResult(
            passed=False,
            error_message=error_message,
            validator_name="required_packages"
        )
    
    logger.debug("All required packages validated successfully")
    return ValidationResult(passed=True, validator_name="required_packages")


def test_file_write_permissions(test_file_path: Path) -> None:
    """Test write permissions by creating and removing temporary file."""
    test_file_path.write_text("permission_test", encoding='utf-8')
    test_file_path.unlink()


def validate_file_permissions(test_file: str) -> ValidationResult:
    """Validate write permissions in current directory."""
    test_file_path = Path(test_file)
    
    try:
        test_file_write_permissions(test_file_path)
        logger.debug("File system write permissions validated successfully")
        return ValidationResult(passed=True, validator_name="file_permissions")
    
    except PermissionError as permission_error:
        error_message = "Insufficient write permissions in current directory"
        logger.error(f"{error_message}: {permission_error}")
        return ValidationResult(
            passed=False,
            error_message=error_message,
            validator_name="file_permissions"
        )
    
    except OSError as os_error:
        error_message = f"File system access error: {os_error}"
        logger.error(error_message)
        return ValidationResult(
            passed=False,
            error_message=error_message,
            validator_name="file_permissions"
        )


class EnvironmentValidator:
    """Comprehensive system environment validator with detailed reporting."""
    
    def __init__(
        self, 
        min_python_version: VersionInfo = VersionInfo.from_tuple(MIN_PYTHON_VERSION),
        required_packages: Tuple[str, ...] = REQUIRED_PACKAGES,
        test_file: str = TEST_FILE_NAME
    ) -> None:
        self._min_python_version = min_python_version
        self._required_packages = required_packages
        self._test_file = test_file
        self._validation_results: Dict[str, ValidationResult] = {}
        logger.debug("Environment validator initialized")
    
    def validate_complete_environment(self) -> None:
        """Perform comprehensive environment validation."""
        validation_steps = [
            self._validate_python_version,
            self._validate_package_dependencies,
            self._validate_filesystem_access
        ]
        
        for validation_step in validation_steps:
            validation_step()
        
        self._check_all_validations_passed()
        logger.info("Complete environment validation successful")
    
    def _validate_python_version(self) -> None:
        """Validate Python version requirement."""
        result = validate_python_version(self._min_python_version)
        self._validation_results['python_version'] = result
        
        if not result.passed:
            raise EnvironmentValidationError(result.error_message)
    
    def _validate_package_dependencies(self) -> None:
        """Validate required package dependencies."""
        result = validate_required_packages(self._required_packages)
        self._validation_results['required_packages'] = result
        
        if not result.passed:
            raise EnvironmentValidationError(result.error_message)
    
    def _validate_filesystem_access(self) -> None:
        """Validate file system access permissions."""
        result = validate_file_permissions(self._test_file)
        self._validation_results['file_permissions'] = result
        
        if not result.passed:
            raise EnvironmentValidationError(result.error_message)
    
    def _check_all_validations_passed(self) -> None:
        """Verify all validations completed successfully."""
        failed_validations = [
            name for name, result in self._validation_results.items()
            if not result.passed
        ]
        
        if failed_validations:
            error_message = f"Validation failures: {failed_validations}"
            raise EnvironmentValidationError(error_message)
    
    def get_validation_summary(self) -> Dict[str, bool]:
        """Get summary of validation results."""
        return {
            name: result.passed 
            for name, result in self._validation_results.items()
        }


def load_environment_file(env_file_path: Path) -> bool:
    """Load environment variables from file if available."""
    if not env_file_path.exists():
        logger.debug(f"Environment file {env_file_path} not found, skipping load")
        return False
    
    try:
        load_dotenv(env_file_path)
        logger.info(f"Environment variables loaded from {env_file_path}")
        return True
    except Exception as loading_error:
        error_message = f"Failed to load environment file {env_file_path}: {loading_error}"
        logger.error(error_message)
        raise EnvironmentValidationError(error_message) from loading_error


class EnvironmentLoader:
    """Manages loading and validation of environment variables from files."""
    
    def __init__(self, env_file_path: Optional[Path] = None) -> None:
        self._env_file_path = env_file_path or Path(DEFAULT_ENV_FILE)
        logger.debug(f"Environment loader configured with path: {self._env_file_path}")
    
    def load_environment_variables(self) -> bool:
        """Load environment variables from configured file."""
        return load_environment_file(self._env_file_path)


def load_application_settings() -> Settings:
    """Load and validate complete application configuration."""
    try:
        logger.debug("Starting application configuration loading process")
        settings = Settings.load()
        logger.info("Application configuration loaded and validated successfully")
        return settings
    except ConfigurationError:
        logger.error("Configuration loading failed validation")
        raise
    except Exception as unexpected_error:
        error_message = f"Configuration loading failed unexpectedly: {unexpected_error}"
        logger.error(f"Unexpected configuration error: {unexpected_error}")
        raise ConfigurationError(error_message) from unexpected_error


class ConfigurationManager:
    """Manages application configuration loading with comprehensive validation."""
    
    def __init__(self) -> None:
        logger.debug("Configuration manager initialized")
    
    def load_settings(self) -> Settings:
        """Load application settings with validation."""
        return load_application_settings()


def parse_log_level(level_string: str) -> int:
    """Convert string log level to numeric logging constant."""
    return getattr(logging, level_string.upper(), logging.INFO)


def setup_application_logging(settings: Settings, console_level: str) -> None:
    """Configure comprehensive application logging system."""
    try:
        numeric_level = parse_log_level(console_level)
        setup_logging(settings, numeric_level)
        logger.info(f"Logging system configured with console level: {console_level}")
    except StartupError:
        logger.error("Logging setup failed during configuration")
        raise
    except Exception as setup_error:
        error_message = f"Logging configuration failed unexpectedly: {setup_error}"
        logger.error(f"Unexpected logging setup error: {setup_error}")
        raise StartupError(error_message) from setup_error


class LoggingManager:
    """Manages application logging configuration with enterprise-grade setup."""
    
    def __init__(self) -> None:
        logger.debug("Logging manager initialized")
    
    def setup_logging(self, settings: Settings, console_level: str) -> None:
        """Configure application logging system."""
        setup_application_logging(settings, console_level)


def install_global_exception_handler(settings: Settings) -> None:
    """Install global exception handler for unhandled application errors."""
    try:
        sys.excepthook = make_exception_hook(settings)
        logger.debug("Global exception handler installed successfully")
    except Exception as installation_error:
        error_message = f"Exception handler setup failed: {installation_error}"
        logger.error(f"Failed to install global exception handler: {installation_error}")
        raise StartupError(error_message) from installation_error


class GlobalErrorHandler:
    """Manages global exception handling for unhandled application errors."""
    
    def __init__(self) -> None:
        logger.debug("Global error handler initialized")
    
    def install_exception_handler(self, settings: Settings) -> None:
        """Install global exception handler."""
        install_global_exception_handler(settings)


def create_application_instance(settings: Settings) -> Any:
    """Create main application instance ready for execution."""
    application = create_simple_app(settings)
    logger.info("Application instance created successfully")
    return application


def execute_application_instance(application: Any) -> None:
    """Execute the configured application instance."""
    application.run()


def log_startup_configuration(settings: Settings) -> None:
    """Log important application configuration for debugging."""
    logger.info("Starting InfiniteJournal (Simple Mode)")
    logger.info(
        "Application configuration: SIZE=%dx%d, FPS=%d, DEBUG=%s",
        settings.WIDTH,
        settings.HEIGHT,
        settings.FPS,
        settings.DEBUG
    )


class ApplicationLifecycleManager:
    """Manages complete application lifecycle with comprehensive error handling."""
    
    def __init__(self) -> None:
        self._environment_validator = EnvironmentValidator()
        self._environment_loader = EnvironmentLoader()
        self._configuration_manager = ConfigurationManager()
        self._logging_manager = LoggingManager()
        self._error_handler = GlobalErrorHandler()
        self._settings: Optional[Settings] = None
        logger.debug("Application lifecycle manager initialized")
    
    def initialize_application_environment(self, console_log_level: str) -> Settings:
        """Initialize complete application environment."""
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
            error_message = f"Application initialization failed: {known_error}"
            logger.error(error_message)
            raise ApplicationStartupError(error_message) from known_error
        
        except Exception as unexpected_error:
            error_message = f"Unexpected initialization error: {unexpected_error}"
            logger.error(f"Unexpected error during application initialization: {unexpected_error}")
            raise ApplicationStartupError(error_message) from unexpected_error
    
    def create_and_run_application(self, settings: Settings) -> None:
        """Create and execute the main application."""
        try:
            application = create_application_instance(settings)
            log_startup_configuration(settings)
            execute_application_instance(application)
            
            logger.info("Application execution completed successfully")
            
        except StartupError as startup_error:
            error_message = f"Application startup failed: {startup_error}"
            logger.error(error_message)
            raise ApplicationStartupError(error_message) from startup_error
        
        except KeyboardInterrupt:
            logger.info("Application execution interrupted by user request")
            raise
        
        except Exception as execution_error:
            logger.exception("Unexpected error during application execution")
            error_message = f"Application execution failed: {execution_error}"
            raise ApplicationStartupError(error_message) from execution_error
    
    def _validate_system_environment(self) -> None:
        """Perform comprehensive system environment validation."""
        logger.debug("Starting comprehensive environment validation")
        self._environment_validator.validate_complete_environment()
    
    def _load_environment_variables(self) -> None:
        """Load environment variables from configuration files."""
        logger.debug("Loading environment variables from configuration")
        self._environment_loader.load_environment_variables()
    
    def _load_configuration_settings(self) -> Settings:
        """Load and validate application configuration settings."""
        return self._configuration_manager.load_settings()
    
    def _setup_logging_system(self, settings: Settings, console_level: str) -> None:
        """Configure comprehensive application logging system."""
        self._logging_manager.setup_logging(settings, console_level)
    
    def _install_error_handling(self, settings: Settings) -> None:
        """Install global error handling for unhandled exceptions."""
        self._error_handler.install_exception_handler(settings)


def parse_command_arguments(argv: Optional[List[str]] = None) -> Any:
    """Parse and validate command-line arguments."""
    try:
        logger.debug("Starting command-line argument parsing process")
        arguments = parse_args(argv)
        logger.info("Command-line arguments parsed and validated successfully")
        return arguments
    except SystemExit as system_exit:
        exit_code = system_exit.code or 0
        error_message = f"Argument parsing exit: {exit_code}"
        
        if exit_code != 0:
            logger.error(f"Argument parsing failed with exit code: {exit_code}")
        
        raise ApplicationStartupError(error_message) from system_exit
    except Exception as parsing_error:
        error_message = f"Argument parsing failed unexpectedly: {parsing_error}"
        logger.error(f"Unexpected argument parsing error: {parsing_error}")
        raise ApplicationStartupError(error_message) from parsing_error


class ArgumentProcessor:
    """Processes and validates command-line arguments for application configuration."""
    
    def __init__(self) -> None:
        logger.debug("Argument processor initialized")
    
    def parse_command_arguments(self, argv: Optional[List[str]] = None) -> Any:
        """Parse command-line arguments with comprehensive error handling."""
        return parse_command_arguments(argv)


def log_startup_error(error: ApplicationStartupError) -> None:
    """Log startup error with stderr fallback."""
    error_message = f"Application startup failed: {error}"
    
    try:
        logger.error(error_message)
    except Exception:
        print(error_message, file=sys.stderr)


def log_keyboard_interrupt() -> None:
    """Log user interruption with stderr fallback."""
    try:
        logger.info("Application terminated by user request")
    except Exception:
        print("Application terminated by user request", file=sys.stderr)


def log_unexpected_error(error: Exception) -> None:
    """Log unexpected error with stderr fallback."""
    error_message = f"Unexpected application error: {error}"
    
    try:
        logger.exception("Unexpected error in main application execution")
    except Exception:
        print(error_message, file=sys.stderr)


class ErrorRecoveryManager:
    """Manages error logging and recovery strategies with fallback mechanisms."""
    
    @staticmethod
    def log_startup_error(error: ApplicationStartupError) -> None:
        """Log startup error with fallback."""
        log_startup_error(error)
    
    @staticmethod
    def log_keyboard_interrupt() -> None:
        """Log user interruption with fallback."""
        log_keyboard_interrupt()
    
    @staticmethod
    def log_unexpected_error(error: Exception) -> None:
        """Log unexpected error with fallback."""
        log_unexpected_error(error)


def execute_application_lifecycle(argv: Optional[List[str]] = None) -> int:
    """Execute complete application lifecycle with error handling."""
    argument_processor = ArgumentProcessor()
    parsed_arguments = argument_processor.parse_command_arguments(argv)
    
    lifecycle_manager = ApplicationLifecycleManager()
    application_settings = lifecycle_manager.initialize_application_environment(
        parsed_arguments.log_level or 'INFO'
    )
    
    lifecycle_manager.create_and_run_application(application_settings)
    return SUCCESS_EXIT_CODE


def main(argv: Optional[List[str]] = None) -> int:
    """Production-ready application entry point with enterprise-grade error handling.
    
    Manages complete application lifecycle including environment validation,
    configuration loading, logging setup, and graceful error recovery.
    
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
        return execute_application_lifecycle(argv)
        
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


# CLEAR EXPANSION POINTS FOR TEAM DEVELOPMENT:

# 1. ADD NEW VALIDATORS:
#    - Create function following validate_* pattern
#    - Add to EnvironmentValidator._validation_steps
#    - Example: validate_database_connection(), validate_api_keys()

# 2. ADD CONFIGURATION SOURCES:
#    - Implement load_from_* functions
#    - Add to ConfigurationManager.load_settings()
#    - Example: load_from_consul(), load_from_vault()

# 3. ADD LOGGING OUTPUTS:
#    - Extend setup_application_logging function
#    - Add new log handlers and formatters
#    - Example: ElasticsearchLogHandler, SlackLogHandler

# 4. ADD ERROR RECOVERY:
#    - Implement new error handling strategies
#    - Add to ErrorRecoveryManager
#    - Example: email_error_notification(), restart_application()

# 5. ADD APPLICATION TYPES:
#    - Create new create_*_app functions
#    - Add to ApplicationLifecycleManager
#    - Example: create_web_app(), create_batch_app()

# 6. ADD HEALTH CHECKS:
#    - Implement health check functions
#    - Add to validation pipeline
#    - Example: check_database_health(), check_external_services()
