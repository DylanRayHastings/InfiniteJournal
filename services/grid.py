"""
Module grid: utilities for drawing a configurable grid background.
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Tuple, Any, Dict

LOGGER = logging.getLogger(__name__)

DEFAULT_GRID_SPACING = 25
DEFAULT_GRID_COLOR = (40, 40, 40)
DEFAULT_CONFIG_PATH = Path("config/grid_config.json")


class GridConfigError(Exception):
    """Exception raised for errors in grid configuration."""


@dataclass
class GridConfig:
    """Configuration for grid drawing."""
    spacing: int = DEFAULT_GRID_SPACING
    color: Tuple[int, int, int] = DEFAULT_GRID_COLOR

    def __post_init__(self) -> None:
        validate_spacing(self.spacing)
        validate_color(self.color)

    @classmethod
    def load_from_file(cls, path: Path) -> "GridConfig":
        """Load grid configuration from a JSON file.

        Args:
            path: Path to JSON config.

        Returns:
            A GridConfig instance (defaults if file missing or invalid).

        Logs:
            INFO if file not found, ERROR on parse/validation failure.
        """
        if not path.exists():
            LOGGER.info("Config file %s not found; using defaults.", path)
            return cls()
        try:
            with path.open("r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
            return cls(
                spacing=data.get("spacing", DEFAULT_GRID_SPACING),
                color=tuple(data.get("color", DEFAULT_GRID_COLOR)),
            )
        except (json.JSONDecodeError, TypeError, GridConfigError) as exc:
            LOGGER.error("Failed to load config %s: %s; using defaults.", path, exc)
            return cls()

    def save_to_file(self, path: Path) -> None:
        """Save grid configuration to a JSON file.

        Args:
            path: Destination path for JSON config.

        Raises:
            IOError on failure to write file.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4)


def validate_spacing(spacing: int) -> None:
    """Validate that spacing is a positive integer.

    Args:
        spacing: Value to validate.

    Raises:
        GridConfigError: If spacing is not a positive int.
    """
    if not isinstance(spacing, int) or spacing <= 0:
        raise GridConfigError(f"Invalid spacing {spacing}: must be a positive integer.")


def validate_color(color: Tuple[int, int, int]) -> None:
    """Validate that color is an RGB tuple of three ints between 0 and 255.

    Args:
        color: Value to validate.

    Raises:
        GridConfigError: If color is not a proper RGB tuple.
    """
    if (
        not isinstance(color, tuple)
        or len(color) != 3
        or not all(isinstance(c, int) and 0 <= c <= 255 for c in color)
    ):
        raise GridConfigError(
            f"Invalid color {color}: must be a tuple of three ints 0–255."
        )


class GridDrawer:
    """Draws a mathematical grid on a given engine."""

    def __init__(self, engine: Any, config: GridConfig = None) -> None:
        """
        Initialize the grid drawer.

        Args:
            engine: Engine instance used for drawing.
            config: GridConfig instance (if None, loaded from default path).

        Raises:
            AttributeError: If engine lacks required methods.
        """
        self.engine = engine
        self.config = config or GridConfig.load_from_file(DEFAULT_CONFIG_PATH)
        self._validate_engine()

    def _validate_engine(self) -> None:
        """Ensure the engine has screen.get_size and draw_line methods.

        Raises:
            AttributeError: If required methods/attributes are missing.
        """
        if not hasattr(self.engine, "screen"):
            raise AttributeError("Engine must have a 'screen' attribute.")
        if not callable(getattr(self.engine.screen, "get_size", None)):
            raise AttributeError("Engine.screen must provide get_size().")
        if not callable(getattr(self.engine, "draw_line", None)):
            raise AttributeError("Engine must provide draw_line().")

    def draw(self) -> None:
        """Draw the grid using configured spacing and color."""
        width, height = self.engine.screen.get_size()
        self._draw_vertical_lines(width, height)
        self._draw_horizontal_lines(width, height)

    def _draw_vertical_lines(self, width: int, height: int) -> None:
        """
        Draw vertical grid lines.

        Args:
            width: Total drawing width.
            height: Total drawing height.
        """
        for x in range(0, width, self.config.spacing):
            self._safe_draw_line((x, 0), (x, height))

    def _draw_horizontal_lines(self, width: int, height: int) -> None:
        """
        Draw horizontal grid lines.

        Args:
            width: Total drawing width.
            height: Total drawing height.
        """
        for y in range(0, height, self.config.spacing):
            self._safe_draw_line((0, y), (width, y))

    def _safe_draw_line(
        self, start: Tuple[int, int], end: Tuple[int, int]
    ) -> None:
        """
        Draw a line with error handling.

        Args:
            start: Starting coordinate (x, y).
            end: Ending coordinate (x, y).
        """
        try:
            self.engine.draw_line(start, end, 1, self.config.color)
        except Exception as exc:
            LOGGER.error("Failed to draw line from %s to %s: %s", start, end, exc)
