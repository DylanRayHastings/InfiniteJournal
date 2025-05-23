"""
Enhanced Grid Drawing System.

Production-ready grid drawing utilities with comprehensive configuration,
multiple grid styles, and unified drawing interface for any engine.

Quick start:
    drawer = GridDrawer(engine)
    drawer.draw()

Advanced usage:
    config = GridConfig(spacing=30, color=(50, 50, 50), style=GridStyle.DOTS)
    drawer = GridDrawer(engine, config)
    drawer.draw()

Extension points:
    - Add grid styles: Extend GridStyle enum and implement draw methods
    - Add validation rules: Create new validate_* functions
    - Add configuration sources: Implement ConfigurationSource interface
    - Add drawing engines: Ensure engine has required interface methods
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Tuple, Any, Dict, Optional, List, Protocol
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

DEFAULT_GRID_SPACING = 25
DEFAULT_GRID_COLOR = (40, 40, 40)
DEFAULT_LINE_WIDTH = 1
DEFAULT_CONFIG_PATH = Path("config/grid_config.json")
MIN_SPACING = 1
MAX_SPACING = 1000
MAX_COLOR_VALUE = 255
MIN_COLOR_VALUE = 0
COLOR_TUPLE_LENGTH = 3


class GridConfigError(Exception):
    """Exception raised for errors in grid configuration."""


class GridDrawingError(Exception):
    """Exception raised for errors during grid drawing."""


class GridStyle(Enum):
    """Grid drawing style options."""
    LINES = "lines"
    DOTS = "dots"
    CROSSES = "crosses"
    DASHED_LINES = "dashed_lines"


class DrawingEngine(Protocol):
    """Protocol defining required drawing engine interface."""
    
    @property
    def screen(self) -> Any:
        """Screen object with get_size method."""
        ...
    
    def draw_line(self, start: Tuple[int, int], end: Tuple[int, int], width: int, color: Tuple[int, int, int]) -> None:
        """Draw line from start to end with specified width and color."""
        ...
    
    def draw_circle(self, center: Tuple[int, int], radius: int, color: Tuple[int, int, int]) -> None:
        """Draw circle at center with specified radius and color."""
        ...


class ConfigurationSource(ABC):
    """Abstract base for configuration loading sources."""
    
    @abstractmethod
    def load_config(self) -> Dict[str, Any]:
        """Load configuration data from source."""
        pass
    
    @abstractmethod
    def save_config(self, config_data: Dict[str, Any]) -> None:
        """Save configuration data to source."""
        pass


@dataclass
class GridConfig:
    """Configuration for grid drawing with comprehensive validation."""
    spacing: int = DEFAULT_GRID_SPACING
    color: Tuple[int, int, int] = DEFAULT_GRID_COLOR
    line_width: int = DEFAULT_LINE_WIDTH
    style: GridStyle = GridStyle.LINES
    opacity: float = 1.0
    offset_x: int = 0
    offset_y: int = 0

    def __post_init__(self) -> None:
        """Validate all configuration values after initialization."""
        validate_spacing(self.spacing)
        validate_color(self.color)
        validate_line_width(self.line_width)
        validate_opacity(self.opacity)
        validate_offset(self.offset_x)
        validate_offset(self.offset_y)

    @classmethod
    def load_from_file(cls, path: Path) -> "GridConfig":
        """Load grid configuration from JSON file with comprehensive error handling.

        Args:
            path: Path to JSON configuration file

        Returns:
            GridConfig instance with loaded values or defaults if file missing/invalid

        Logs:
            INFO: When file not found, using defaults
            ERROR: When file exists but contains invalid data
        """
        if not path.exists():
            logger.info("Configuration file %s not found, using default values", path)
            return cls()
        
        try:
            file_source = JsonFileConfigurationSource(path)
            data = file_source.load_config()
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, GridConfigError) as error:
            logger.error("Failed to load configuration from %s: %s, using defaults", path, error)
            return cls()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GridConfig":
        """Create GridConfig from dictionary with validation.

        Args:
            data: Dictionary containing configuration values

        Returns:
            GridConfig instance with validated values
        """
        style_value = data.get("style", GridStyle.LINES.value)
        style = GridStyle(style_value) if isinstance(style_value, str) else style_value
        
        return cls(
            spacing=data.get("spacing", DEFAULT_GRID_SPACING),
            color=tuple(data.get("color", DEFAULT_GRID_COLOR)),
            line_width=data.get("line_width", DEFAULT_LINE_WIDTH),
            style=style,
            opacity=data.get("opacity", 1.0),
            offset_x=data.get("offset_x", 0),
            offset_y=data.get("offset_y", 0)
        )

    def save_to_file(self, path: Path) -> None:
        """Save grid configuration to JSON file with error handling.

        Args:
            path: Destination path for configuration file

        Raises:
            IOError: When unable to create directory or write file
        """
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            file_source = JsonFileConfigurationSource(path)
            config_dict = asdict(self)
            config_dict["style"] = self.style.value
            file_source.save_config(config_dict)
            logger.info("Configuration saved to %s", path)
        except (OSError, IOError) as error:
            logger.error("Failed to save configuration to %s: %s", path, error)
            raise

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        result = asdict(self)
        result["style"] = self.style.value
        return result


class JsonFileConfigurationSource(ConfigurationSource):
    """JSON file-based configuration source."""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        with self.file_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    
    def save_config(self, config_data: Dict[str, Any]) -> None:
        """Save configuration to JSON file."""
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(config_data, file, indent=4)


def validate_spacing(spacing: int) -> None:
    """Validate grid spacing is within acceptable range.

    Args:
        spacing: Grid spacing value to validate

    Raises:
        GridConfigError: When spacing is invalid
    """
    if not isinstance(spacing, int):
        raise GridConfigError(f"Spacing must be integer, got {type(spacing).__name__}")
    
    if spacing < MIN_SPACING or spacing > MAX_SPACING:
        raise GridConfigError(f"Spacing {spacing} must be between {MIN_SPACING} and {MAX_SPACING}")


def validate_color(color: Tuple[int, int, int]) -> None:
    """Validate color is proper RGB tuple with values in valid range.

    Args:
        color: RGB color tuple to validate

    Raises:
        GridConfigError: When color format or values are invalid
    """
    if not isinstance(color, tuple):
        raise GridConfigError(f"Color must be tuple, got {type(color).__name__}")
    
    if len(color) != COLOR_TUPLE_LENGTH:
        raise GridConfigError(f"Color must have {COLOR_TUPLE_LENGTH} values, got {len(color)}")
    
    for i, component in enumerate(color):
        if not isinstance(component, int):
            raise GridConfigError(f"Color component {i} must be integer, got {type(component).__name__}")
        
        if component < MIN_COLOR_VALUE or component > MAX_COLOR_VALUE:
            raise GridConfigError(f"Color component {i} value {component} must be between {MIN_COLOR_VALUE} and {MAX_COLOR_VALUE}")


def validate_line_width(line_width: int) -> None:
    """Validate line width is positive integer.

    Args:
        line_width: Line width value to validate

    Raises:
        GridConfigError: When line width is invalid
    """
    if not isinstance(line_width, int):
        raise GridConfigError(f"Line width must be integer, got {type(line_width).__name__}")
    
    if line_width <= 0:
        raise GridConfigError(f"Line width {line_width} must be positive")


def validate_opacity(opacity: float) -> None:
    """Validate opacity is within valid range.

    Args:
        opacity: Opacity value to validate

    Raises:
        GridConfigError: When opacity is invalid
    """
    if not isinstance(opacity, (int, float)):
        raise GridConfigError(f"Opacity must be number, got {type(opacity).__name__}")
    
    if opacity < 0.0 or opacity > 1.0:
        raise GridConfigError(f"Opacity {opacity} must be between 0.0 and 1.0")


def validate_offset(offset: int) -> None:
    """Validate offset is integer within reasonable range.

    Args:
        offset: Offset value to validate

    Raises:
        GridConfigError: When offset is invalid
    """
    if not isinstance(offset, int):
        raise GridConfigError(f"Offset must be integer, got {type(offset).__name__}")
    
    if abs(offset) > MAX_SPACING:
        raise GridConfigError(f"Offset {offset} must be between -{MAX_SPACING} and {MAX_SPACING}")


def validate_engine_interface(engine: Any) -> None:
    """Validate drawing engine has required interface methods.

    Args:
        engine: Drawing engine to validate

    Raises:
        AttributeError: When engine lacks required methods or attributes
    """
    if not hasattr(engine, "screen"):
        raise AttributeError("Engine must have 'screen' attribute")
    
    if not callable(getattr(engine.screen, "get_size", None)):
        raise AttributeError("Engine screen must have callable 'get_size' method")
    
    if not callable(getattr(engine, "draw_line", None)):
        raise AttributeError("Engine must have callable 'draw_line' method")


def calculate_grid_points(width: int, height: int, spacing: int, offset_x: int = 0, offset_y: int = 0) -> List[Tuple[int, int]]:
    """Calculate all grid intersection points for given dimensions.

    Args:
        width: Total drawing area width
        height: Total drawing area height
        spacing: Distance between grid lines
        offset_x: Horizontal offset for grid alignment
        offset_y: Vertical offset for grid alignment

    Returns:
        List of (x, y) coordinate tuples for grid intersections
    """
    points = []
    
    for x in range(offset_x % spacing, width, spacing):
        for y in range(offset_y % spacing, height, spacing):
            points.append((x, y))
    
    return points


def calculate_vertical_lines(width: int, height: int, spacing: int, offset_x: int = 0) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """Calculate vertical grid line coordinates.

    Args:
        width: Total drawing area width
        height: Total drawing area height
        spacing: Distance between grid lines
        offset_x: Horizontal offset for grid alignment

    Returns:
        List of ((start_x, start_y), (end_x, end_y)) tuples for vertical lines
    """
    lines = []
    
    for x in range(offset_x % spacing, width, spacing):
        lines.append(((x, 0), (x, height)))
    
    return lines


def calculate_horizontal_lines(width: int, height: int, spacing: int, offset_y: int = 0) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """Calculate horizontal grid line coordinates.

    Args:
        width: Total drawing area width
        height: Total drawing area height
        spacing: Distance between grid lines
        offset_y: Vertical offset for grid alignment

    Returns:
        List of ((start_x, start_y), (end_x, end_y)) tuples for horizontal lines
    """
    lines = []
    
    for y in range(offset_y % spacing, height, spacing):
        lines.append(((0, y), (width, y)))
    
    return lines


def safe_draw_line(engine: DrawingEngine, start: Tuple[int, int], end: Tuple[int, int], width: int, color: Tuple[int, int, int]) -> None:
    """Draw line with comprehensive error handling.

    Args:
        engine: Drawing engine instance
        start: Starting coordinate (x, y)
        end: Ending coordinate (x, y)
        width: Line width in pixels
        color: RGB color tuple

    Logs:
        ERROR: When drawing operation fails
    """
    try:
        engine.draw_line(start, end, width, color)
    except Exception as error:
        logger.error("Failed to draw line from %s to %s: %s", start, end, error)


def safe_draw_circle(engine: DrawingEngine, center: Tuple[int, int], radius: int, color: Tuple[int, int, int]) -> None:
    """Draw circle with comprehensive error handling.

    Args:
        engine: Drawing engine instance
        center: Circle center coordinate (x, y)
        radius: Circle radius in pixels
        color: RGB color tuple

    Logs:
        ERROR: When drawing operation fails
    """
    try:
        if hasattr(engine, 'draw_circle') and callable(engine.draw_circle):
            engine.draw_circle(center, radius, color)
        else:
            logger.warning("Engine does not support circle drawing, skipping dots")
    except Exception as error:
        logger.error("Failed to draw circle at %s with radius %d: %s", center, radius, error)


class GridDrawer:
    """Enhanced grid drawing system with multiple styles and comprehensive configuration.
    
    Supports various grid styles including lines, dots, crosses, and dashed lines.
    Provides unified interface for drawing grids on any compatible engine.
    
    Attributes:
        engine: Drawing engine instance with required interface
        config: Grid configuration with style and appearance settings
    """

    def __init__(self, engine: DrawingEngine, config: Optional[GridConfig] = None) -> None:
        """Initialize grid drawer with engine and configuration.

        Args:
            engine: Drawing engine instance for rendering
            config: Grid configuration (loads from default path if None)

        Raises:
            AttributeError: When engine lacks required interface methods
            GridConfigError: When configuration is invalid
        """
        validate_engine_interface(engine)
        
        self.engine = engine
        self.config = config or GridConfig.load_from_file(DEFAULT_CONFIG_PATH)
        
        logger.info("GridDrawer initialized with style: %s", self.config.style.value)

    def draw(self) -> None:
        """Draw grid using configured style and settings.
        
        Automatically selects appropriate drawing method based on configured style.
        Handles errors gracefully and logs drawing operations.
        """
        try:
            width, height = self.engine.screen.get_size()
            logger.debug("Drawing grid on %dx%d surface", width, height)
            
            if self.config.style == GridStyle.LINES:
                self.draw_line_grid(width, height)
            elif self.config.style == GridStyle.DOTS:
                self.draw_dot_grid(width, height)
            elif self.config.style == GridStyle.CROSSES:
                self.draw_cross_grid(width, height)
            elif self.config.style == GridStyle.DASHED_LINES:
                self.draw_dashed_line_grid(width, height)
            else:
                logger.warning("Unknown grid style %s, using lines", self.config.style)
                self.draw_line_grid(width, height)
                
            logger.debug("Grid drawing completed successfully")
            
        except Exception as error:
            logger.error("Grid drawing failed: %s", error)
            raise GridDrawingError(f"Failed to draw grid: {error}") from error

    def draw_line_grid(self, width: int, height: int) -> None:
        """Draw traditional line-based grid.

        Args:
            width: Drawing area width
            height: Drawing area height
        """
        vertical_lines = calculate_vertical_lines(width, height, self.config.spacing, self.config.offset_x)
        horizontal_lines = calculate_horizontal_lines(width, height, self.config.spacing, self.config.offset_y)
        
        for start, end in vertical_lines:
            safe_draw_line(self.engine, start, end, self.config.line_width, self.config.color)
        
        for start, end in horizontal_lines:
            safe_draw_line(self.engine, start, end, self.config.line_width, self.config.color)

    def draw_dot_grid(self, width: int, height: int) -> None:
        """Draw dot-based grid at intersection points.

        Args:
            width: Drawing area width
            height: Drawing area height
        """
        points = calculate_grid_points(width, height, self.config.spacing, self.config.offset_x, self.config.offset_y)
        dot_radius = max(1, self.config.line_width)
        
        for point in points:
            safe_draw_circle(self.engine, point, dot_radius, self.config.color)

    def draw_cross_grid(self, width: int, height: int) -> None:
        """Draw cross marks at grid intersection points.

        Args:
            width: Drawing area width
            height: Drawing area height
        """
        points = calculate_grid_points(width, height, self.config.spacing, self.config.offset_x, self.config.offset_y)
        cross_size = max(3, self.config.line_width * 2)
        
        for x, y in points:
            safe_draw_line(self.engine, (x - cross_size, y), (x + cross_size, y), self.config.line_width, self.config.color)
            safe_draw_line(self.engine, (x, y - cross_size), (x, y + cross_size), self.config.line_width, self.config.color)

    def draw_dashed_line_grid(self, width: int, height: int) -> None:
        """Draw dashed line grid with alternating segments.

        Args:
            width: Drawing area width
            height: Drawing area height
        """
        dash_length = self.config.spacing // 4
        gap_length = dash_length // 2
        
        self.draw_dashed_vertical_lines(width, height, dash_length, gap_length)
        self.draw_dashed_horizontal_lines(width, height, dash_length, gap_length)

    def draw_dashed_vertical_lines(self, width: int, height: int, dash_length: int, gap_length: int) -> None:
        """Draw vertical dashed lines.

        Args:
            width: Drawing area width
            height: Drawing area height
            dash_length: Length of each dash segment
            gap_length: Length of gaps between dashes
        """
        for x in range(self.config.offset_x % self.config.spacing, width, self.config.spacing):
            y = 0
            while y < height:
                dash_end = min(y + dash_length, height)
                safe_draw_line(self.engine, (x, y), (x, dash_end), self.config.line_width, self.config.color)
                y = dash_end + gap_length

    def draw_dashed_horizontal_lines(self, width: int, height: int, dash_length: int, gap_length: int) -> None:
        """Draw horizontal dashed lines.

        Args:
            width: Drawing area width
            height: Drawing area height
            dash_length: Length of each dash segment
            gap_length: Length of gaps between dashes
        """
        for y in range(self.config.offset_y % self.config.spacing, height, self.config.spacing):
            x = 0
            while x < width:
                dash_end = min(x + dash_length, width)
                safe_draw_line(self.engine, (x, y), (dash_end, y), self.config.line_width, self.config.color)
                x = dash_end + gap_length

    def update_config(self, new_config: GridConfig) -> None:
        """Update grid configuration with validation.

        Args:
            new_config: New configuration to apply

        Logs:
            INFO: When configuration is successfully updated
        """
        self.config = new_config
        logger.info("Grid configuration updated: spacing=%d, style=%s", 
                   self.config.spacing, self.config.style.value)

    def save_current_config(self, path: Optional[Path] = None) -> None:
        """Save current configuration to file.

        Args:
            path: File path for saving (uses default if None)
        """
        save_path = path or DEFAULT_CONFIG_PATH
        self.config.save_to_file(save_path)


def create_default_grid_drawer(engine: DrawingEngine) -> GridDrawer:
    """Create grid drawer with default configuration.

    Args:
        engine: Drawing engine instance

    Returns:
        GridDrawer instance with default settings
    """
    return GridDrawer(engine)


def create_custom_grid_drawer(engine: DrawingEngine, spacing: int, color: Tuple[int, int, int], style: GridStyle = GridStyle.LINES) -> GridDrawer:
    """Create grid drawer with custom configuration.

    Args:
        engine: Drawing engine instance
        spacing: Grid spacing in pixels
        color: RGB color tuple
        style: Grid drawing style

    Returns:
        GridDrawer instance with custom settings
    """
    config = GridConfig(spacing=spacing, color=color, style=style)
    return GridDrawer(engine, config)


def load_grid_config_from_dict(config_dict: Dict[str, Any]) -> GridConfig:
    """Load grid configuration from dictionary with validation.

    Args:
        config_dict: Dictionary containing configuration values

    Returns:
        Validated GridConfig instance
    """
    return GridConfig.from_dict(config_dict)