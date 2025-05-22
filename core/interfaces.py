"""
Abstract engine-agnostic interfaces for windowing, input, rendering, and timing.
Defines core types and contracts; configure logging and persistence at the application level.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Tuple, TypeAlias, Mapping

logger = logging.getLogger(__name__)

Point: TypeAlias = Tuple[int, int]
Stroke: TypeAlias = List[Point]


def _validate_non_empty_str(value: Any, name: str) -> None:
    """Validate that a value is a non-empty string.

    Args:
        value: The value to validate.
        name: Name of the parameter, used in error messages.

    Raises:
        ValueError: If value is not a string or is empty.
    """
    if not isinstance(value, str) or not value.strip():
        logger.error("%s must be a non-empty string: %r", name, value)
        raise ValueError(f"{name} must be a non-empty string")


def _validate_positive_int(value: Any, name: str) -> None:
    """Validate that a value is a positive integer.

    Args:
        value: The value to validate.
        name: Name of the parameter, used in error messages.

    Raises:
        ValueError: If value is not an int or <= 0.
    """
    if not isinstance(value, int) or value <= 0:
        logger.error("%s must be a positive integer: %r", name, value)
        raise ValueError(f"{name} must be a positive integer")


def _validate_non_negative_int(value: Any, name: str) -> None:
    """Validate that a value is a non-negative integer.

    Args:
        value: The value to validate.
        name: Name of the parameter, used in error messages.

    Raises:
        ValueError: If value is not an int or < 0.
    """
    if not isinstance(value, int) or value < 0:
        logger.error("%s must be a non-negative integer: %r", name, value)
        raise ValueError(f"{name} must be a non-negative integer")


def _validate_point(value: Any, name: str) -> None:
    """Validate that a value is a Point (tuple of two ints).

    Args:
        value: The value to validate.
        name: Name of the parameter, used in error messages.

    Raises:
        ValueError: If value is not a tuple of two ints.
    """
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or not all(isinstance(c, int) for c in value)
    ):
        logger.error("%s must be a tuple of two ints: %r", name, value)
        raise ValueError(f"{name} must be a tuple[int, int]")


def _validate_stroke(value: Any, name: str) -> None:
    """Validate that a value is a Stroke (list of Points).

    Args:
        value: The value to validate.
        name: Name of the parameter, used in error messages.

    Raises:
        ValueError: If value is not a list of Points.
    """
    if not isinstance(value, list) or any(
        not (isinstance(p, tuple) and len(p) == 2 and
             all(isinstance(c, int) for c in p))
        for p in value
    ):
        logger.error("%s must be a list of Point: %r", name, value)
        raise ValueError(f"{name} must be a list[tuple[int, int]]")


@dataclass(frozen=True)
class Event:
    """Represents a normalized input or system event.

    Attributes:
        type: Identifier for the event type.
        data: Payload associated with the event.
    """
    type: str = field(metadata={"description": "Type identifier for the event"})
    data: Any = field(default=None, metadata={"description": "Event payload"})

    def __post_init__(self) -> None:
        _validate_non_empty_str(self.type, "Event.type")
        logger.debug("Event created: type=%s, data=%r", self.type, self.data)


class Engine(ABC):
    """Interface for window management and primitive drawing operations."""

    @abstractmethod
    def init_window(self, width: int, height: int, title: str) -> None:
        """Initialize the rendering window.

        Args:
            width: Window width in pixels.
            height: Window height in pixels.
            title: Window title.

        Raises:
            ValueError: If width/height are non-positive or title is empty.
            NotImplementedError: Always in base class.
        """
        _validate_positive_int(width, "width")
        _validate_positive_int(height, "height")
        _validate_non_empty_str(title, "title")
        logger.debug("init_window called: %dx%d, title=%s", width, height, title)
        raise NotImplementedError("init_window() must be implemented by subclasses")

    @abstractmethod
    def poll_events(self) -> List[Event]:
        """Poll engine events and return normalized Event objects.

        Returns:
            A list of normalized Event objects.

        Raises:
            NotImplementedError: Always in base class.
        """
        logger.debug("poll_events called")
        raise NotImplementedError("poll_events() must be implemented by subclasses")

    @abstractmethod
    def clear(self) -> None:
        """Clear the rendering target in preparation for the next frame.

        Raises:
            NotImplementedError: Always in base class.
        """
        logger.debug("clear called")
        raise NotImplementedError("clear() must be implemented by subclasses")

    @abstractmethod
    def present(self) -> None:
        """Present the rendered frame to the display.

        Raises:
            NotImplementedError: Always in base class.
        """
        logger.debug("present called")
        raise NotImplementedError("present() must be implemented by subclasses")

    @abstractmethod
    def draw_line(self, start: Point, end: Point, width: int) -> None:
        """Draw a line between two points.

        Args:
            start: Starting point of the line.
            end: End point of the line.
            width: Line width in pixels.

        Raises:
            ValueError: If width is negative.
            NotImplementedError: Always in base class.
        """
        _validate_point(start, "start")
        _validate_point(end, "end")
        _validate_non_negative_int(width, "width")
        logger.debug(
            "draw_line called: start=%s, end=%s, width=%d", start, end, width
        )
        raise NotImplementedError("draw_line() must be implemented by subclasses")

    @abstractmethod
    def draw_circle(self, center: Point, radius: int) -> None:
        """Draw a circle.

        Args:
            center: Center of the circle.
            radius: Radius in pixels.

        Raises:
            ValueError: If radius is negative.
            NotImplementedError: Always in base class.
        """
        _validate_point(center, "center")
        _validate_non_negative_int(radius, "radius")
        logger.debug("draw_circle called: center=%s, radius=%d", center, radius)
        raise NotImplementedError("draw_circle() must be implemented by subclasses")

    @abstractmethod
    def draw_text(self, text: str, pos: Point, font_size: int) -> None:
        """Render text at the given position.

        Args:
            text: Text to render.
            pos: Position for the text baseline.
            font_size: Font size in points.

        Raises:
            ValueError: If text is empty or font_size <= 0.
            NotImplementedError: Always in base class.
        """
        _validate_non_empty_str(text, "text")
        _validate_point(pos, "pos")
        _validate_positive_int(font_size, "font_size")
        logger.debug(
            "draw_text called: text=%r, pos=%s, font_size=%d", text, pos,
            font_size
        )
        raise NotImplementedError("draw_text() must be implemented by subclasses")


class Clock(ABC):
    """Interface for frame timing and elapsed time management."""

    @abstractmethod
    def tick(self, target_fps: int) -> None:
        """Delay to enforce the target frames per second.

        Args:
            target_fps: Desired frames per second.

        Raises:
            ValueError: If target_fps <= 0.
            NotImplementedError: Always in base class.
        """
        _validate_positive_int(target_fps, "target_fps")
        logger.debug("tick called with target_fps=%d", target_fps)
        raise NotImplementedError("tick() must be implemented by subclasses")

    @abstractmethod
    def get_time(self) -> float:
        """Get the time elapsed since the last tick.

        Returns:
            Time in seconds since last tick.

        Raises:
            NotImplementedError: Always in base class.
        """
        logger.debug("get_time called")
        raise NotImplementedError("get_time() must be implemented by subclasses")


class InputAdapter(ABC):
    """Interface for translating raw engine events into domain-specific Events."""

    @abstractmethod
    def translate(self, events: List[Event]) -> List[Event]:
        """Translate raw engine events to application Events.

        Args:
            events: Raw events from the Engine.

        Returns:
            Domain Events for the application.

        Raises:
            NotImplementedError: Always in base class.
        """
        logger.debug("translate called with %d raw events", len(events))
        raise NotImplementedError("translate() must be implemented by subclasses")


class Renderer(ABC):
    """Interface for high-level rendering: strokes, cursor, and UI overlays."""

    @abstractmethod
    def draw_stroke(self, points: Stroke, width: int) -> None:
        """Draw a freehand stroke.

        Args:
            points: Sequence of (x, y) points.
            width: Stroke width in pixels.

        Raises:
            ValueError: If width is negative.
            NotImplementedError: Always in base class.
        """
        _validate_stroke(points, "points")
        _validate_non_negative_int(width, "width")
        logger.debug(
            "draw_stroke called with %d points, width=%d",
            len(points),
            width,
        )
        raise NotImplementedError("draw_stroke() must be implemented by subclasses")

    @abstractmethod
    def draw_cursor(self, pos: Point, radius: int) -> None:
        """Draw a circular cursor at the given position.

        Args:
            pos: Center of the cursor.
            radius: Cursor radius in pixels.

        Raises:
            ValueError: If radius is negative.
            NotImplementedError: Always in base class.
        """
        _validate_point(pos, "pos")
        _validate_non_negative_int(radius, "radius")
        logger.debug("draw_cursor called: pos=%s, radius=%d", pos, radius)
        raise NotImplementedError("draw_cursor() must be implemented by subclasses")

    @abstractmethod
    def draw_ui(self, mode: str, timestamp: str) -> None:
        """Draw the user interface overlay.

        Args:
            mode: Current mode or tool.
            timestamp: Formatted timestamp.

        Raises:
            ValueError: If mode or timestamp is empty.
            NotImplementedError: Always in base class.
        """
        _validate_non_empty_str(mode, "mode")
        _validate_non_empty_str(timestamp, "timestamp")
        logger.debug("draw_ui called: mode=%s, timestamp=%s", mode, timestamp)
        raise NotImplementedError("draw_ui() must be implemented by subclasses")


class DataStore(ABC):
    """Interface for data persistence operations.

    Methods save and load should be implemented for application data.
    """

    @abstractmethod
    def save(self, key: str, data: Any) -> None:
        """Save data under a given key.

        Args:
            key: Unique identifier for the data.
            data: Object to be persisted.

        Raises:
            IOError: If saving fails.
        """
        raise NotImplementedError("save() must be implemented by subclasses")

    @abstractmethod
    def load(self, key: str) -> Any:
        """Load data associated with a given key.

        Args:
            key: Unique identifier for the data.

        Returns:
            The loaded data.

        Raises:
            KeyError: If no data exists for the key.
            IOError: If loading fails.
        """
        raise NotImplementedError("load() must be implemented by subclasses")


class ConfigValidator(ABC):
    """Interface for configuration validation."""

    @abstractmethod
    def validate(self, config: Mapping[str, Any]) -> None:
        """Validate provided configuration.

        Args:
            config: Mapping of configuration values.

        Raises:
            ValueError: If any configuration value is invalid.
        """
        raise NotImplementedError("validate() must be implemented by subclasses")
