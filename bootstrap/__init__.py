"""
Bootstrap Package for InfiniteJournal
Handles application startup, configuration, and initialization.
"""

from .cli import parse_args, validate_args
from .errors import StartupError, ConfigurationError, DependencyError, make_exception_hook
from .logging_setup import setup_logging, create_logger
from .factory import create_simple_app, create_basic_pygame_app

__version__ = "1.0.0"
__author__ = "InfiniteJournal Bootstrap"

__all__ = [
    'parse_args',
    'validate_args', 
    'StartupError',
    'ConfigurationError',
    'DependencyError', 
    'make_exception_hook',
    'setup_logging',
    'create_logger',
    'create_simple_app',
    'create_basic_pygame_app'
]