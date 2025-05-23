"""
Abstract engine-agnostic interfaces for windowing, input, rendering, and timing.
Defines core types and contracts with comprehensive type safety.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Tuple, TypeAlias, Mapping, Protocol, Union, Optional

logger = logging.getLogger(__name__)

# Type aliases for better clarity
Point: TypeAlias = Tuple[int, int]
Color: TypeAlias = Tuple[int, int, int]
Stroke: TypeAlias = List[Point]
Size: TypeAlias = Tuple[int, int]


class ValidationError(ValueError):
    """Raised when validation of interface parameters fails."""
    pass


def validate_non_empty_str(value: Any, name: str) -> None:
    """Validate that a value is a non-empty string."""
    if not isinstance(value, str) or not value.strip():
        logger.error("%s must be a non-empty string: %r", name, value)
        raise ValidationError(f"{name} must be a non-empty string")


def validate_positive_int(value: Any, name: str) -> None:
    """Validate that a value is a positive integer."""
    if not isinstance(value, int) or value <= 0:
        logger.error("%s must be a positive integer: %r", name, value)
        raise ValidationError(f"{name} must be a positive integer")


def validate_non_negative_int(value: Any, name: str) -> None:
    """Validate that a value is a non-negative integer."""
    if not isinstance(value, int) or value < 0:
        logger.error("%s must be a non-negative integer: %r", name, value)
        raise ValidationError(f"{name} must be a non-negative integer")


def validate_point(value: Any, name: str) -> None:
    """Validate that a value is a Point (tuple of two ints)."""
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or not all(isinstance(c, int) for c in value)
    ):
        logger.error("%s must be a tuple of two ints: %r", name, value)
        raise ValidationError(f"{name} must be a tuple[int, int]")


def validate_color(value: Any, name: str) -> None:
    """Validate that a value is a valid RGB color tuple."""
    if (
        not isinstance(value, tuple)
        or len(value) != 3
        or not all(isinstance(c, int) and 0 <= c <= 255 for c in value)
    ):
        logger.error("%s must be an RGB tuple (r, g, b) with values 0-255: %r", name, value)
        raise ValidationError(f"{name} must be a valid RGB color tuple")


@dataclass(frozen=True)
class Event:
    """Represents a normalized input or system event."""
    type: str = field(metadata={"description": "Type identifier for the event"})
    data: Any = field(default=None, metadata={"description": "Event payload"})

    def __post_init__(self) -> None:
        validate_non_empty_str(self.type, "Event.type")
        logger.debug("Event created: type=%s, data=%r", self.type, self.data)


class Engine(ABC):
    """Interface for window management and primitive drawing operations."""

    @abstractmethod
    def init_window(self, width: int, height: int, title: str) -> None:
        """Initialize the rendering window."""
        validate_positive_int(width, "width")
        validate_positive_int(height, "height")
        validate_non_empty_str(title, "title")
        logger.debug("init_window called: %dx%d, title=%s", width, height, title)

    @abstractmethod
    def poll_events(self) -> List[Event]:
        """Poll engine events and return normalized Event objects."""
        logger.debug("poll_events called")

    @abstractmethod
    def clear(self, color: Optional[Color] = None) -> None:
        """Clear the rendering target."""
        if color is not None:
            validate_color(color, "color")
        logger.debug("clear called")

    @abstractmethod
    def present(self) -> None:
        """Present the rendered frame to the display."""
        logger.debug("present called")

    @abstractmethod
    def draw_line(self, start: Point, end: Point, width: int, color: Optional[Color] = None) -> None:
        """Draw a line between two points."""
        validate_point(start, "start")
        validate_point(end, "end")
        validate_non_negative_int(width, "width")
        if color is not None:
            validate_color(color, "color")
        logger.debug("draw_line called: start=%s, end=%s, width=%d", start, end, width)

    @abstractmethod
    def draw_circle(self, center: Point, radius: int, color: Optional[Color] = None) -> None:
        """Draw a circle."""
        validate_point(center, "center")
        validate_non_negative_int(radius, "radius")
        if color is not None:
            validate_color(color, "color")
        logger.debug("draw_circle called: center=%s, radius=%d", center, radius)

    @abstractmethod
    def draw_text(self, text: str, pos: Point, font_size: int, color: Optional[Color] = None) -> None:
        """Render text at the given position."""
        validate_non_empty_str(text, "text")
        validate_point(pos, "pos")
        validate_positive_int(font_size, "font_size")
        if color is not None:
            validate_color(color, "color")
        logger.debug("draw_text called: text=%r, pos=%s, font_size=%d", text, pos, font_size)

    @abstractmethod
    def get_size(self) -> Size:
        """Get the current window/screen size."""
        logger.debug("get_size called")


class Clock(ABC):
    """Interface for frame timing and elapsed time management."""

    @abstractmethod
    def tick(self, target_fps: int) -> float:
        """Delay to enforce target FPS and return actual frame time."""
        validate_positive_int(target_fps, "target_fps")
        logger.debug("tick called with target_fps=%d", target_fps)

    @abstractmethod
    def get_time(self) -> float:
        """Get the current time in seconds."""
        logger.debug("get_time called")

    @abstractmethod
    def get_fps(self) -> float:
        """Get the current frames per second."""
        logger.debug("get_fps called")


class InputAdapter(ABC):
    """Interface for translating raw engine events into domain-specific Events."""

    @abstractmethod
    def translate(self, events: List[Event]) -> List[Event]:
        """Translate raw engine events to application Events."""
        logger.debug("translate called with %d raw events", len(events))


class Renderer(ABC):
    """Interface for high-level rendering: strokes, cursor, and UI overlays."""

    @abstractmethod
    def draw_stroke(self, points: Stroke, width: int, color: Optional[Color] = None) -> None:
        """Draw a freehand stroke."""
        if not isinstance(points, list):
            raise ValidationError("points must be a list")
        validate_non_negative_int(width, "width")
        if color is not None:
            validate_color(color, "color")
        logger.debug("draw_stroke called with %d points, width=%d", len(points), width)

    @abstractmethod
    def draw_cursor(self, pos: Point, radius: int, color: Optional[Color] = None) -> None:
        """Draw a circular cursor at the given position."""
        validate_point(pos, "pos")
        validate_non_negative_int(radius, "radius")
        if color is not None:
            validate_color(color, "color")
        logger.debug("draw_cursor called: pos=%s, radius=%d", pos, radius)

    @abstractmethod
    def draw_ui(self, mode: str, timestamp: str, color: Optional[Color] = None) -> None:
        """Draw the user interface overlay."""
        validate_non_empty_str(mode, "mode")
        validate_non_empty_str(timestamp, "timestamp")
        if color is not None:
            validate_color(color, "color")
        logger.debug("draw_ui called: mode=%s, timestamp=%s", mode, timestamp)


class DataStore(ABC):
    """Interface for data persistence operations."""

    @abstractmethod
    def save(self, key: str, data: Any) -> None:
        """Save data under a given key."""
        validate_non_empty_str(key, "key")

    @abstractmethod
    def load(self, key: str) -> Any:
        """Load data associated with a given key."""
        validate_non_empty_str(key, "key")

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete data associated with a given key."""
        validate_non_empty_str(key, "key")

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if data exists for a given key."""
        validate_non_empty_str(key, "key")

    @abstractmethod
    def list_keys(self) -> List[str]:
        """List all available keys."""

    @abstractmethod
    def close(self) -> None:
        """Close the data store and release resources."""


class ConfigValidator(ABC):
    """Interface for configuration validation."""

    @abstractmethod
    def validate(self, config: Mapping[str, Any]) -> None:
        """Validate provided configuration."""
        if not isinstance(config, Mapping):
            raise ValidationError("config must be a mapping")


# Legacy compatibility - keep original validation functions with old names
def _validate_non_empty_str(value: Any, name: str) -> None:
    """Legacy validation function for backward compatibility."""
    validate_non_empty_str(value, name)


def _validate_positive_int(value: Any, name: str) -> None:
    """Legacy validation function for backward compatibility."""
    validate_positive_int(value, name)


def _validate_non_negative_int(value: Any, name: str) -> None:
    """Legacy validation function for backward compatibility."""
    validate_non_negative_int(value, name)


def _validate_point(value: Any, name: str) -> None:
    """Legacy validation function for backward compatibility."""
    validate_point(value, name)


def _validate_stroke(value: Any, name: str) -> None:
    """Legacy validation function for backward compatibility."""
    if not isinstance(value, list) or any(
        not (isinstance(p, tuple) and len(p) == 2 and
             all(isinstance(c, int) for c in p))
        for p in value
    ):
        logger.error("%s must be a list of Point: %r", name, value)
        raise ValidationError(f"{name} must be a list[tuple[int, int]]")