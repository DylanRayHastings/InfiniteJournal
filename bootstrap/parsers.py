"""Parsing utilities with comprehensive validation."""

from typing import Any, Optional
import logging
from .errors import StartupError

logger = logging.getLogger(__name__)


def parse_positive_int(
    raw: Any, 
    name: str, 
    default: Optional[int] = None, 
    min_value: int = 1, 
    max_value: int = 5000
) -> Optional[int]:
    """
    Parse and validate a positive integer within bounds.
    
    Args:
        raw: Raw value to parse
        name: Parameter name for error messages
        default: Default value if raw is None
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Parsed integer value or None if raw is None and no default
        
    Raises:
        StartupError: If parsing or validation fails
    """
    logger.debug("Parsing positive int for %s: raw=%r, default=%r", name, raw, default)
    
    if raw is None:
        return default

    try:
        value = int(raw)
    except (TypeError, ValueError) as e:
        logger.error("Invalid integer for %s: %r", name, raw)
        raise StartupError(f"{name} must be an integer, got '{raw}'") from e

    if not (min_value <= value <= max_value):
        logger.error("Integer out of range for %s: %d (range: %d-%d)", name, value, min_value, max_value)
        raise StartupError(
            f"{name} must be between {min_value} and {max_value}, got {value}"
        )
    
    logger.debug("Successfully parsed %s: %d", name, value)
    return value


def parse_path(raw: Any, name: str, must_exist: bool = False) -> Optional[str]:
    """
    Parse and validate a file/directory path.
    
    Args:
        raw: Raw path value
        name: Parameter name for error messages  
        must_exist: Whether the path must already exist
        
    Returns:
        Validated path string or None if raw is None
        
    Raises:
        StartupError: If validation fails
    """
    if raw is None:
        return None
        
    if not isinstance(raw, str):
        raise StartupError(f"{name} must be a string path")
        
    path_str = raw.strip()
    if not path_str:
        raise StartupError(f"{name} cannot be empty")
        
    if must_exist:
        from pathlib import Path
        if not Path(path_str).exists():
            raise StartupError(f"{name} path does not exist: {path_str}")
    
    return path_str


def parse_bool(raw: Any, name: str, default: bool = False) -> bool:
    """
    Parse a boolean value from various formats.
    
    Args:
        raw: Raw value to parse
        name: Parameter name for error messages
        default: Default value if raw is None
        
    Returns:
        Parsed boolean value
    """
    if raw is None:
        return default
        
    if isinstance(raw, bool):
        return raw
        
    if isinstance(raw, str):
        lower = raw.lower().strip()
        if lower in ('true', '1', 'yes', 'on'):
            return True
        elif lower in ('false', '0', 'no', 'off'):
            return False
        else:
            raise StartupError(f"{name} must be a boolean value, got '{raw}'")
    
    raise StartupError(f"{name} must be a boolean, got {type(raw).__name__}")