"""
Error Handling for InfiniteJournal Bootstrap
Provides exception handling and error reporting.
"""

import logging
import sys
import traceback
from typing import Any, Type, Optional, Callable
from pathlib import Path


class StartupError(Exception):
    """
    Exception raised during application startup.
    
    This exception is used for errors that occur during the initialization
    phase of the application before the main loop starts.
    """
    
    def __init__(self, message: str, cause: Optional[Exception] = None):
        """
        Initialize startup error.
        
        Args:
            message: Error description
            cause: Optional underlying exception that caused this error
        """
        super().__init__(message)
        self.cause = cause
        self.message = message
    
    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


class ConfigurationError(StartupError):
    """Exception raised for configuration-related startup errors."""
    pass


class DependencyError(StartupError):
    """Exception raised for missing dependency errors."""
    pass


class InitializationError(StartupError):
    """Exception raised for general initialization errors."""
    pass


def make_exception_hook(settings=None) -> Callable:
    """
    Create a custom exception hook for unhandled exceptions.
    
    Args:
        settings: Application settings (optional)
        
    Returns:
        Exception hook function suitable for sys.excepthook
    """
    logger = logging.getLogger('exception_handler')
    
    def exception_hook(exc_type: Type[BaseException], exc_value: BaseException, exc_traceback):
        """
        Handle unhandled exceptions.
        
        Args:
            exc_type: Exception type
            exc_value: Exception instance
            exc_traceback: Traceback object
        """
        # Don't log KeyboardInterrupt
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Format the exception
        exception_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        
        # Log the exception
        logger.error("Unhandled exception occurred:")
        logger.error(f"Exception Type: {exc_type.__name__}")
        logger.error(f"Exception Message: {exc_value}")
        logger.error(f"Traceback:\n{exception_msg}")
        
        # Additional context if settings available
        if settings:
            debug_mode = getattr(settings, 'DEBUG', True)
            data_path = getattr(settings, 'DATA_PATH', None)
            
            logger.error(f"Debug Mode: {debug_mode}")
            if data_path:
                logger.error(f"Data Directory: {data_path}")
        
        # Save crash report if possible
        try:
            save_crash_report(exc_type, exc_value, exc_traceback, settings)
        except Exception as crash_save_error:
            logger.error(f"Failed to save crash report: {crash_save_error}")
        
        # Print to stderr for immediate visibility
        print(f"\nFATAL ERROR: {exc_type.__name__}: {exc_value}", file=sys.stderr)
        print("Check the logs for detailed information.", file=sys.stderr)
        
        # Exit gracefully
        sys.exit(1)
    
    return exception_hook


def save_crash_report(exc_type: Type[BaseException], exc_value: BaseException, 
                     exc_traceback, settings=None) -> Optional[Path]:
    """
    Save a crash report to disk.
    
    Args:
        exc_type: Exception type
        exc_value: Exception instance  
        exc_traceback: Traceback object
        settings: Application settings (optional)
        
    Returns:
        Path to saved crash report, or None if save failed
    """
    try:
        # Determine save location
        if settings and hasattr(settings, 'DATA_PATH'):
            crash_dir = Path(settings.DATA_PATH) / 'crashes'
        else:
            crash_dir = Path('./crashes')
        
        crash_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate crash report filename
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        crash_file = crash_dir / f'crash_report_{timestamp}.txt'
        
        # Generate crash report content
        report_lines = []
        report_lines.append("InfiniteJournal Crash Report")
        report_lines.append("=" * 50)
        report_lines.append(f"Timestamp: {datetime.datetime.now().isoformat()}")
        report_lines.append(f"Python Version: {sys.version}")
        report_lines.append(f"Platform: {sys.platform}")
        report_lines.append("")
        
        # Exception information
        report_lines.append("Exception Information:")
        report_lines.append("-" * 30)
        report_lines.append(f"Type: {exc_type.__name__}")
        report_lines.append(f"Message: {exc_value}")
        report_lines.append("")
        
        # Full traceback
        report_lines.append("Full Traceback:")
        report_lines.append("-" * 30)
        traceback_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        report_lines.extend(traceback_lines)
        report_lines.append("")
        
        # Settings information
        if settings:
            report_lines.append("Application Settings:")
            report_lines.append("-" * 30)
            for attr in dir(settings):
                if not attr.startswith('_'):
                    try:
                        value = getattr(settings, attr)
                        if not callable(value):
                            report_lines.append(f"{attr}: {value}")
                    except Exception:
                        report_lines.append(f"{attr}: <unable to access>")
            report_lines.append("")
        
        # System information
        report_lines.append("System Information:")
        report_lines.append("-" * 30)
        try:
            import platform
            report_lines.append(f"System: {platform.system()}")
            report_lines.append(f"Release: {platform.release()}")
            report_lines.append(f"Machine: {platform.machine()}")
            report_lines.append(f"Processor: {platform.processor()}")
        except Exception:
            report_lines.append("System information unavailable")
        
        # Write crash report
        with crash_file.open('w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        return crash_file
        
    except Exception as save_error:
        # If crash report saving fails, log but don't raise
        logger = logging.getLogger('crash_reporter')
        logger.error(f"Failed to save crash report: {save_error}")
        return None


def handle_startup_error(error: StartupError) -> None:
    """
    Handle startup errors with appropriate logging and user feedback.
    
    Args:
        error: The startup error to handle
    """
    logger = logging.getLogger('startup_error_handler')
    
    # Log the error
    logger.error(f"Startup failed: {error.message}")
    if error.cause:
        logger.error(f"Underlying cause: {error.cause}")
        logger.debug("Full traceback:", exc_info=error.cause)
    
    # Print user-friendly message
    print(f"\nStartup Error: {error.message}", file=sys.stderr)
    
    if isinstance(error, ConfigurationError):
        print("Please check your configuration settings.", file=sys.stderr)
    elif isinstance(error, DependencyError):
        print("Please install missing dependencies.", file=sys.stderr)
    elif isinstance(error, InitializationError):
        print("Please check the application logs for details.", file=sys.stderr)
    
    print("See logs for detailed error information.", file=sys.stderr)


def create_error_reporter(debug_mode: bool = False) -> Callable:
    """
    Create an error reporting function.
    
    Args:
        debug_mode: Whether to include debug information
        
    Returns:
        Error reporting function
    """
    def report_error(error: Exception, context: str = ""):
        """Report an error with context."""
        logger = logging.getLogger('error_reporter')
        
        if context:
            logger.error(f"Error in {context}: {error}")
        else:
            logger.error(f"Error: {error}")
        
        if debug_mode:
            logger.debug("Full traceback:", exc_info=True)
    
    return report_error


# Export main functions and classes
__all__ = [
    'StartupError',
    'ConfigurationError', 
    'DependencyError',
    'InitializationError',
    'make_exception_hook',
    'save_crash_report',
    'handle_startup_error',
    'create_error_reporter'
]