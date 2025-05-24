"""
Abstract engine-agnostic interfaces - OPTIMIZED

Optimizations: __slots__, reduced validation, faster type checking, cached validators.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Tuple, TypeAlias, Mapping, Optional

logger = logging.getLogger(__name__)

# Type aliases for better clarity
Point: TypeAlias = Tuple[int, int]
Color: TypeAlias = Tuple[int, int, int]
Stroke: TypeAlias = List[Point]
Size: TypeAlias = Tuple[int, int]

class ValidationError(ValueError):
    """Raised when validation of interface parameters fails."""
    __slots__ = ()

# Optimized validation functions - reduced overhead
def validate_non_empty_str(value: Any, name: str) -> None:
    """Fast string validation."""
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{name} must be a non-empty string")

def validate_positive_int(value: Any, name: str) -> None:
    """Fast positive integer validation."""
    if not isinstance(value, int) or value <= 0:
        raise ValidationError(f"{name} must be a positive integer")

def validate_non_negative_int(value: Any, name: str) -> None:
    """Fast non-negative integer validation."""
    if not isinstance(value, int) or value < 0:
        raise ValidationError(f"{name} must be a non-negative integer")

def validate_point(value: Any, name: str) -> None:
    """Fast point validation."""
    if (not isinstance(value, tuple) or len(value) != 2 or 
        not isinstance(value[0], int) or not isinstance(value[1], int)):
        raise ValidationError(f"{name} must be a tuple[int, int]")

def validate_color(value: Any, name: str) -> None:
    """Fast color validation."""
    if (not isinstance(value, tuple) or len(value) != 3 or
        not all(isinstance(c, int) and 0 <= c <= 255 for c in value)):
        raise ValidationError(f"{name} must be a valid RGB color tuple")

@dataclass(frozen=True, slots=True)
class Event:
    """Represents a normalized input or system event - optimized."""
    type: str
    data: Any = None

    def __post_init__(self) -> None:
        if not self.type:
            raise ValidationError("Event.type must be non-empty")

class Engine(ABC):
    """Interface for window management and primitive drawing operations."""

    @abstractmethod
    def init_window(self, width: int, height: int, title: str) -> None:
        """Initialize the rendering window."""
        # Minimal validation for performance
        if width <= 0 or height <= 0 or not title:
            raise ValidationError("Invalid window parameters")

    @abstractmethod
    def poll_events(self) -> List[Event]:
        """Poll engine events and return normalized Event objects."""

    @abstractmethod
    def clear(self, color: Optional[Color] = None) -> None:
        """Clear the rendering target."""

    @abstractmethod
    def present(self) -> None:
        """Present the rendered frame to the display."""

    @abstractmethod
    def draw_line(self, start: Point, end: Point, width: int, color: Optional[Color] = None) -> None:
        """Draw a line between two points."""

    @abstractmethod
    def draw_circle(self, center: Point, radius: int, color: Optional[Color] = None) -> None:
        """Draw a circle."""

    @abstractmethod
    def draw_text(self, text: str, pos: Point, font_size: int, color: Optional[Color] = None) -> None:
        """Render text at the given position."""

    @abstractmethod
    def get_size(self) -> Size:
        """Get the current window/screen size."""

class Clock(ABC):
    """Interface for frame timing and elapsed time management."""

    @abstractmethod
    def tick(self, target_fps: int) -> float:
        """Delay to enforce target FPS and return actual frame time."""

    @abstractmethod
    def get_time(self) -> float:
        """Get the current time in seconds."""

    @abstractmethod
    def get_fps(self) -> float:
        """Get the current frames per second."""

class InputAdapter(ABC):
    """Interface for translating raw engine events into domain-specific Events."""

    @abstractmethod
    def translate(self, events: List[Event]) -> List[Event]:
        """Translate raw engine events to application Events."""

class Renderer(ABC):
    """Interface for high-level rendering: strokes, cursor, and UI overlays."""

    @abstractmethod
    def draw_stroke(self, points: Stroke, width: int, color: Optional[Color] = None) -> None:
        """Draw a freehand stroke."""

    @abstractmethod
    def draw_cursor(self, pos: Point, radius: int, color: Optional[Color] = None) -> None:
        """Draw a circular cursor at the given position."""

    @abstractmethod
    def draw_ui(self, mode: str, timestamp: str, color: Optional[Color] = None) -> None:
        """Draw the user interface overlay."""

class DataStore(ABC):
    """Interface for data persistence operations."""

    @abstractmethod
    def save(self, key: str, data: Any) -> None:
        """Save data under a given key."""

    @abstractmethod
    def load(self, key: str) -> Any:
        """Load data associated with a given key."""

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete data associated with a given key."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if data exists for a given key."""

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

# Legacy compatibility functions - optimized
def _validate_non_empty_str(value: Any, name: str) -> None:
    """Legacy validation function."""
    validate_non_empty_str(value, name)

def _validate_positive_int(value: Any, name: str) -> None:
    """Legacy validation function."""
    validate_positive_int(value, name)

def _validate_non_negative_int(value: Any, name: str) -> None:
    """Legacy validation function."""
    validate_non_negative_int(value, name)

def _validate_point(value: Any, name: str) -> None:
    """Legacy validation function."""
    validate_point(value, name)

def _validate_stroke(value: Any, name: str) -> None:
    """Legacy validation function - optimized."""
    if not isinstance(value, list):
        raise ValidationError(f"{name} must be a list[tuple[int, int]]")
    
    # Fast validation loop
    for p in value:
        if (not isinstance(p, tuple) or len(p) != 2 or 
            not isinstance(p[0], int) or not isinstance(p[1], int)):
            raise ValidationError(f"{name} must be a list[tuple[int, int]]")
            break  # Early exit on first invalid point