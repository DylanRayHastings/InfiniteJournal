from typing import Any
import logging
from .errors import StartupError

logger = logging.getLogger(__name__)

def parse_positive_int(
    raw: Any, name: str, default: int, min_value: int = 1, max_value: int = 5000
) -> int:
    """Parse and validate a positive integer within bounds."""
    logger.debug("Parsing positive int for %s: raw=%r", name, raw)
    if raw is None:
        value = default
    else:
        try:
            value = int(raw)
        except (TypeError, ValueError) as e:
            logger.error("Invalid integer for %s: %r", name, raw)
            raise StartupError(f"{name} must be an integer, got '{raw}'") from e

    if not (min_value <= value <= max_value):
        logger.error("Integer out of range for %s: %d", name, value)
        raise StartupError(
            f"{name} must be between {min_value} and {max_value}, got {value}"
        )
    return value
