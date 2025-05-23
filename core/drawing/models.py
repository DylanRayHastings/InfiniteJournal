# core/drawing/models.py (Fixed Point width handling)
"""Data models for drawing primitives, with JSON persistence and proper width handling."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

from .config import validate_file_path
from .exceptions import InvalidColorError, PersistenceError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Point:
    """A point in 3D space with drawing attributes.

    Attributes:
        x: X-coordinate.
        y: Y-coordinate.
        z: Z-coordinate (depth), defaults to 0.0.
        width: Brush width at this point, defaults to 1.
    """

    x: float
    y: float
    z: float = 0.0
    width: int = 1

    def to_dict(self) -> dict:
        """Serialize this Point to a dict."""
        return {"x": self.x, "y": self.y, "z": self.z, "width": self.width}

    @staticmethod
    def from_dict(data: dict) -> "Point":
        """Create a Point from a dict.

        Args:
            data: Dictionary with keys 'x', 'y', 'z', 'width'.

        Returns:
            A new Point instance.

        Raises:
            KeyError: If required keys are missing.
            TypeError: If values cannot be cast to the right types.
        """
        return Point(
            x=float(data["x"]),
            y=float(data["y"]),
            z=float(data.get("z", 0.0)),
            width=int(data.get("width", 1)),
        )


@dataclass
class Stroke:
    """A sequence of Points sharing the same RGB color.

    Attributes:
        color: RGB tuple, each 0–255.
        points: Ordered list of Point instances.
        width: Default width for this stroke (used for rendering optimization).
    """

    color: Tuple[int, int, int]
    points: List[Point] = field(default_factory=list)
    width: int = 3  # Default stroke width

    def __post_init__(self) -> None:
        """Validate that color is a 3-tuple of ints in 0–255."""
        if (
            len(self.color) != 3
            or not all(isinstance(c, int) and 0 <= c <= 255 for c in self.color)
        ):
            raise InvalidColorError(f"Invalid color tuple: {self.color}")

    def add_point(self, point: Point) -> None:
        """Append a Point to this Stroke.

        Args:
            point: Point to append.
        """
        self.points.append(point)
        # Update stroke width to match the point width (for consistency)
        self.width = point.width
        logger.debug("Added Point to stroke %s: %s (width: %d)", self.color, point, point.width)

    def to_dict(self) -> dict:
        """Serialize this Stroke to a dict."""
        return {
            "color": self.color,
            "width": self.width,
            "points": [pt.to_dict() for pt in self.points],
        }

    @staticmethod
    def from_dict(data: dict) -> "Stroke":
        """Create a Stroke from its dict representation.

        Args:
            data: Dict with 'color', 'width', and 'points'.

        Returns:
            A new Stroke instance.
        """
        stroke = Stroke(color=tuple(data["color"]), width=data.get("width", 3))
        for pt_data in data["points"]:
            stroke.add_point(Point.from_dict(pt_data))
        return stroke


@dataclass
class Page:
    """A drawing page: collection of Strokes."""

    strokes: List[Stroke] = field(default_factory=list)

    def new_stroke(self, color: Tuple[int, int, int], width: int = 3) -> Stroke:
        """Start a new Stroke with the given color and width, add it to this Page.

        Args:
            color: RGB tuple.
            width: Default width for the stroke.

        Returns:
            The newly created Stroke.
        """
        stroke = Stroke(color=color, width=width)
        self.strokes.append(stroke)
        logger.info("Started new stroke with color %s, width %d", color, width)
        return stroke

    def to_dict(self) -> dict:
        """Serialize this Page to a dict."""
        return {"strokes": [s.to_dict() for s in self.strokes]}

    @staticmethod
    def from_dict(data: dict) -> "Page":
        """Create a Page from its dict form.

        Args:
            data: Dict with key 'strokes'.

        Returns:
            A new Page instance.
        """
        page = Page()
        for stroke_data in data["strokes"]:
            page.strokes.append(Stroke.from_dict(stroke_data))
        return page

    def save(self, file_path: Path) -> None:
        """Persist this Page as JSON to disk.

        Args:
            file_path: Path where to write.

        Raises:
            PersistenceError: On any I/O or validation failure.
        """
        try:
            validate_file_path(file_path)
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)
            logger.info("Page saved to %s", file_path)
        except Exception as e:
            logger.error("Error saving page to %s: %s", file_path, e)
            raise PersistenceError(f"Failed to save page: {e}")

    @staticmethod
    def load(file_path: Path) -> "Page":
        """Load a Page from a JSON file.

        Args:
            file_path: Path to read from.

        Returns:
            The loaded Page.

        Raises:
            PersistenceError: On any I/O or parse failure.
        """
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            page = Page.from_dict(data)
            logger.info("Page loaded from %s", file_path)
            return page
        except Exception as e:
            logger.error("Error loading page from %s: %s", file_path, e)
            raise PersistenceError(f"Failed to load page: {e}")