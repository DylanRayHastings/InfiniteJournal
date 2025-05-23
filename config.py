"""
Next-Generation Configuration Management System

Enterprise-grade configuration with comprehensive validation, safe parsing,
hot-reloading capabilities, and advanced service patterns.
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any, Protocol, TypeVar, Generic
from abc import ABC, abstractmethod
from contextlib import contextmanager
from functools import lru_cache
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ConfigurationError(Exception):
    """Base configuration error."""
    pass


class ValidationError(ConfigurationError):
    """Configuration validation error."""
    pass


class ParseError(ConfigurationError):
    """Environment variable parsing error."""
    pass


class EnvironmentParser(Protocol):
    """Protocol for environment variable parsers."""
    
    def parse(self, variable_name: str, default_value: T) -> T:
        """Parse environment variable with type-safe fallback."""
        ...


class SafeEnvironmentParser:
    """Type-safe environment variable parser with comprehensive error handling."""
    
    @staticmethod
    def parse_integer(variable_name: str, default_value: int) -> int:
        """Parse integer with detailed error logging."""
        raw_value = os.getenv(variable_name)
        
        if raw_value is None:
            logger.debug(f"Environment variable {variable_name} not set, using default: {default_value}")
            return default_value
        
        try:
            parsed_value = int(raw_value.strip())
            logger.debug(f"Successfully parsed {variable_name}={parsed_value}")
            return parsed_value
        except (ValueError, TypeError, AttributeError) as error:
            logger.warning(f"Failed to parse {variable_name}='{raw_value}' as integer: {error}. Using default: {default_value}")
            return default_value
    
    @staticmethod
    def parse_float(variable_name: str, default_value: float) -> float:
        """Parse float with detailed error logging."""
        raw_value = os.getenv(variable_name)
        
        if raw_value is None:
            logger.debug(f"Environment variable {variable_name} not set, using default: {default_value}")
            return default_value
        
        try:
            parsed_value = float(raw_value.strip())
            logger.debug(f"Successfully parsed {variable_name}={parsed_value}")
            return parsed_value
        except (ValueError, TypeError, AttributeError) as error:
            logger.warning(f"Failed to parse {variable_name}='{raw_value}' as float: {error}. Using default: {default_value}")
            return default_value
    
    @staticmethod
    def parse_boolean(variable_name: str, default_value: bool) -> bool:
        """Parse boolean with detailed error logging."""
        raw_value = os.getenv(variable_name)
        
        if raw_value is None:
            logger.debug(f"Environment variable {variable_name} not set, using default: {default_value}")
            return default_value
        
        try:
            normalized_value = str(raw_value).lower().strip()
            parsed_value = normalized_value in ("true", "1", "yes", "on", "enabled")
            logger.debug(f"Successfully parsed {variable_name}={parsed_value}")
            return parsed_value
        except (AttributeError, TypeError) as error:
            logger.warning(f"Failed to parse {variable_name}='{raw_value}' as boolean: {error}. Using default: {default_value}")
            return default_value
    
    @staticmethod
    def parse_string(variable_name: str, default_value: str) -> str:
        """Parse string with detailed error logging."""
        raw_value = os.getenv(variable_name)
        
        if raw_value is None:
            logger.debug(f"Environment variable {variable_name} not set, using default: {default_value}")
            return default_value
        
        try:
            parsed_value = str(raw_value).strip()
            if not parsed_value:
                logger.warning(f"Environment variable {variable_name} is empty, using default: {default_value}")
                return default_value
            
            logger.debug(f"Successfully parsed {variable_name}='{parsed_value}'")
            return parsed_value
        except Exception as error:
            logger.warning(f"Failed to parse {variable_name}='{raw_value}' as string: {error}. Using default: {default_value}")
            return default_value
    
    @staticmethod
    def parse_path(variable_name: str, default_path: str) -> Path:
        """Parse filesystem path with detailed error logging."""
        raw_value = os.getenv(variable_name, default_path)
        
        try:
            parsed_path = Path(raw_value).resolve()
            logger.debug(f"Successfully parsed {variable_name}={parsed_path}")
            return parsed_path
        except Exception as error:
            logger.warning(f"Failed to parse {variable_name}='{raw_value}' as path: {error}. Using default: {default_path}")
            return Path(default_path).resolve()


class ConfigurationValidationRules:
    """Centralized validation rules with clear business logic."""
    
    # Window constraints
    MIN_WINDOW_SIZE = 100
    MAX_WINDOW_SIZE = 5000
    
    # Performance constraints  
    MIN_FPS = 1
    MAX_FPS = 240
    
    # Tool constraints
    MIN_BRUSH_SIZE = 1
    MAX_BRUSH_SIZE = 200
    VALID_TOOLS = ["brush", "eraser", "line", "rect", "circle", "triangle", "parabola"]
    
    # Drawing constraints
    MAX_STROKE_POINTS_LIMIT = 5000
    MIN_POINT_THRESHOLD = 1
    MAX_POINT_THRESHOLD = 10
    
    # UI constraints
    MIN_BUTTON_SIZE = 20
    MAX_BUTTON_WIDTH = 200
    MAX_BUTTON_HEIGHT = 100
    MIN_BRUSH_STEP = 1
    MAX_BRUSH_STEP = 10


class ConfigurationValidator:
    """Comprehensive validator with detailed error messages."""
    
    rules = ConfigurationValidationRules()
    
    @classmethod
    def validate_window_dimensions(cls, width: int, height: int) -> None:
        """Validate window dimensions with detailed context."""
        if not isinstance(width, int):
            raise ValidationError(f"Window width must be integer, got {type(width).__name__}: {width}")
        
        if not isinstance(height, int):
            raise ValidationError(f"Window height must be integer, got {type(height).__name__}: {height}")
        
        if not (cls.rules.MIN_WINDOW_SIZE <= width <= cls.rules.MAX_WINDOW_SIZE):
            raise ValidationError(f"Window width {width} outside valid range {cls.rules.MIN_WINDOW_SIZE}-{cls.rules.MAX_WINDOW_SIZE}")
        
        if not (cls.rules.MIN_WINDOW_SIZE <= height <= cls.rules.MAX_WINDOW_SIZE):
            raise ValidationError(f"Window height {height} outside valid range {cls.rules.MIN_WINDOW_SIZE}-{cls.rules.MAX_WINDOW_SIZE}")
    
    @classmethod
    def validate_fps_configuration(cls, fps: int, max_fps: int) -> None:
        """Validate frame rate settings with performance considerations."""
        if not isinstance(fps, int):
            raise ValidationError(f"FPS must be integer, got {type(fps).__name__}: {fps}")
        
        if not isinstance(max_fps, int):
            raise ValidationError(f"Max FPS must be integer, got {type(max_fps).__name__}: {max_fps}")
        
        if not (cls.rules.MIN_FPS <= fps <= cls.rules.MAX_FPS):
            raise ValidationError(f"FPS {fps} outside valid range {cls.rules.MIN_FPS}-{cls.rules.MAX_FPS}")
        
        if not (cls.rules.MIN_FPS <= max_fps <= cls.rules.MAX_FPS):
            raise ValidationError(f"Max FPS {max_fps} outside valid range {cls.rules.MIN_FPS}-{cls.rules.MAX_FPS}")
        
        if fps > max_fps:
            raise ValidationError(f"FPS {fps} cannot exceed max FPS {max_fps}")
    
    @classmethod
    def validate_tool_configuration(cls, tool_name: str, min_size: int, max_size: int, step_size: int) -> None:
        """Validate tool settings comprehensively."""
        if not isinstance(tool_name, str):
            raise ValidationError(f"Tool name must be string, got {type(tool_name).__name__}: {tool_name}")
        
        if tool_name not in cls.rules.VALID_TOOLS:
            raise ValidationError(f"Invalid tool '{tool_name}'. Valid tools: {cls.rules.VALID_TOOLS}")
        
        if not isinstance(min_size, int):
            raise ValidationError(f"Minimum brush size must be integer, got {type(min_size).__name__}: {min_size}")
        
        if not isinstance(max_size, int):
            raise ValidationError(f"Maximum brush size must be integer, got {type(max_size).__name__}: {max_size}")
        
        if not isinstance(step_size, int):
            raise ValidationError(f"Brush step size must be integer, got {type(step_size).__name__}: {step_size}")
        
        if not (cls.rules.MIN_BRUSH_SIZE <= min_size <= cls.rules.MAX_BRUSH_SIZE):
            raise ValidationError(f"Minimum brush size {min_size} outside valid range {cls.rules.MIN_BRUSH_SIZE}-{cls.rules.MAX_BRUSH_SIZE}")
        
        if not (cls.rules.MIN_BRUSH_SIZE <= max_size <= cls.rules.MAX_BRUSH_SIZE):
            raise ValidationError(f"Maximum brush size {max_size} outside valid range {cls.rules.MIN_BRUSH_SIZE}-{cls.rules.MAX_BRUSH_SIZE}")
        
        if min_size > max_size:
            raise ValidationError(f"Minimum brush size {min_size} cannot exceed maximum size {max_size}")
        
        if not (cls.rules.MIN_BRUSH_STEP <= step_size <= cls.rules.MAX_BRUSH_STEP):
            raise ValidationError(f"Brush step size {step_size} outside valid range {cls.rules.MIN_BRUSH_STEP}-{cls.rules.MAX_BRUSH_STEP}")


@dataclass(frozen=True)
class WindowConfiguration:
    """Immutable window display configuration."""
    width: int
    height: int
    title: str
    fps: int
    max_fps: int
    vsync_enabled: bool
    double_buffer_enabled: bool
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        ConfigurationValidator.validate_window_dimensions(self.width, self.height)
        ConfigurationValidator.validate_fps_configuration(self.fps, self.max_fps)
        
        if not self.title or not self.title.strip():
            raise ValidationError("Window title cannot be empty")


@dataclass(frozen=True)
class DrawingConfiguration:
    """Immutable drawing and rendering configuration."""
    stroke_smoothing_enabled: bool
    max_stroke_points: int
    point_distance_threshold: int
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        rules = ConfigurationValidationRules()
        
        if not (1 <= self.max_stroke_points <= rules.MAX_STROKE_POINTS_LIMIT):
            raise ValidationError(f"Max stroke points {self.max_stroke_points} outside valid range 1-{rules.MAX_STROKE_POINTS_LIMIT}")
        
        if not (rules.MIN_POINT_THRESHOLD <= self.point_distance_threshold <= rules.MAX_POINT_THRESHOLD):
            raise ValidationError(f"Point threshold {self.point_distance_threshold} outside valid range {rules.MIN_POINT_THRESHOLD}-{rules.MAX_POINT_THRESHOLD}")


@dataclass(frozen=True)
class ToolConfiguration:
    """Immutable tool configuration."""
    default_tool: str
    brush_size_minimum: int
    brush_size_maximum: int
    brush_size_step: int
    available_tools: List[str] = field(default_factory=lambda: ConfigurationValidationRules.VALID_TOOLS.copy())
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        ConfigurationValidator.validate_tool_configuration(
            self.default_tool, 
            self.brush_size_minimum, 
            self.brush_size_maximum, 
            self.brush_size_step
        )


@dataclass(frozen=True)  
class HotbarConfiguration:
    """Immutable hotbar interface configuration."""
    x_position: int
    y_position: int
    button_width: int
    button_height: int
    button_spacing: int


@dataclass(frozen=True)
class ColorConfiguration:
    """Immutable color palette configuration."""
    neon_colors: List[Tuple[int, int, int]] = field(default_factory=lambda: [
        (57, 255, 20),   # Neon Green
        (0, 255, 255),   # Neon Blue  
        (255, 20, 147),  # Neon Pink
        (255, 255, 0),   # Neon Yellow
        (255, 97, 3),    # Neon Orange
    ])


@dataclass(frozen=True)
class StorageConfiguration:
    """Immutable storage and persistence configuration."""
    debug_mode_enabled: bool
    log_directory: Path
    database_url: str
    data_directory: Path
    auto_save_interval_seconds: float
    async_save_enabled: bool
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.auto_save_interval_seconds <= 0:
            raise ValidationError(f"Auto-save interval {self.auto_save_interval_seconds} must be positive")


@dataclass(frozen=True)
class ApplicationConfiguration:
    """Immutable complete application configuration."""
    window: WindowConfiguration
    drawing: DrawingConfiguration 
    tools: ToolConfiguration
    hotbar: HotbarConfiguration
    colors: ColorConfiguration
    storage: StorageConfiguration
    created_at: datetime = field(default_factory=datetime.now)
    
    def is_stale(self, max_age: timedelta = timedelta(hours=1)) -> bool:
        """Check if configuration is stale and needs reloading."""
        return datetime.now() - self.created_at > max_age


class ConfigurationLoader:
    """Handles loading configuration sections with comprehensive error recovery."""
    
    def __init__(self, parser: SafeEnvironmentParser = None):
        self.parser = parser or SafeEnvironmentParser()
    
    def load_window_configuration(self) -> WindowConfiguration:
        """Load window configuration with validation."""
        try:
            return WindowConfiguration(
                width=self.parser.parse_integer("IJ_WIDTH", 1280),
                height=self.parser.parse_integer("IJ_HEIGHT", 720),
                title=self.parser.parse_string("IJ_TITLE", "InfiniteJournal"),
                fps=self.parser.parse_integer("IJ_FPS", 60),
                max_fps=self.parser.parse_integer("IJ_MAX_FPS", 120),
                vsync_enabled=self.parser.parse_boolean("IJ_VSYNC", True),
                double_buffer_enabled=self.parser.parse_boolean("IJ_DOUBLE_BUFFER", True)
            )
        except ValidationError as error:
            logger.error(f"Window configuration validation failed: {error}")
            raise ConfigurationError(f"Invalid window configuration: {error}") from error
    
    def load_drawing_configuration(self) -> DrawingConfiguration:
        """Load drawing configuration with validation."""
        try:
            return DrawingConfiguration(
                stroke_smoothing_enabled=self.parser.parse_boolean("IJ_STROKE_SMOOTHING", True),
                max_stroke_points=self.parser.parse_integer("IJ_MAX_STROKE_POINTS", 1000),
                point_distance_threshold=self.parser.parse_integer("IJ_POINT_THRESHOLD", 2)
            )
        except ValidationError as error:
            logger.error(f"Drawing configuration validation failed: {error}")
            raise ConfigurationError(f"Invalid drawing configuration: {error}") from error
    
    def load_tool_configuration(self) -> ToolConfiguration:
        """Load tool configuration with validation."""
        try:
            return ToolConfiguration(
                default_tool=self.parser.parse_string("IJ_DEFAULT_TOOL", "brush"),
                brush_size_minimum=self.parser.parse_integer("IJ_BRUSH_MIN", 1),
                brush_size_maximum=self.parser.parse_integer("IJ_BRUSH_MAX", 50),
                brush_size_step=self.parser.parse_integer("IJ_BRUSH_STEP", 2)
            )
        except ValidationError as error:
            logger.error(f"Tool configuration validation failed: {error}")
            raise ConfigurationError(f"Invalid tool configuration: {error}") from error
    
    def load_hotbar_configuration(self, window_width: int, window_height: int) -> HotbarConfiguration:
        """Load hotbar configuration with window-relative validation."""
        x_pos = self.parser.parse_integer("IJ_HOTBAR_X", 10)
        y_pos = self.parser.parse_integer("IJ_HOTBAR_Y", 10)
        
        # Clamp positions within window bounds
        x_pos = max(0, min(x_pos, window_width - 100))
        y_pos = max(0, min(y_pos, window_height - 50))
        
        return HotbarConfiguration(
            x_position=x_pos,
            y_position=y_pos,
            button_width=self.parser.parse_integer("IJ_HOTBAR_BTN_WIDTH", 80),
            button_height=self.parser.parse_integer("IJ_HOTBAR_BTN_HEIGHT", 40),
            button_spacing=self.parser.parse_integer("IJ_HOTBAR_SPACING", 5)
        )
    
    def load_color_configuration(self) -> ColorConfiguration:
        """Load color configuration."""
        return ColorConfiguration()
    
    def load_storage_configuration(self) -> StorageConfiguration:
        """Load storage configuration with validation."""
        try:
            return StorageConfiguration(
                debug_mode_enabled=self.parser.parse_boolean("IJ_DEBUG", False),
                log_directory=self.parser.parse_path("IJ_LOG_DIR", "./logs"),
                database_url=self.parser.parse_string("DATABASE_URL", "sqlite:///./data/journal.db"),
                data_directory=self.parser.parse_path("IJ_DATA_PATH", "./data"),
                auto_save_interval_seconds=self.parser.parse_float("IJ_AUTO_SAVE_INTERVAL", 5.0),
                async_save_enabled=self.parser.parse_boolean("IJ_ASYNC_SAVE", True)
            )
        except ValidationError as error:
            logger.error(f"Storage configuration validation failed: {error}")
            raise ConfigurationError(f"Invalid storage configuration: {error}") from error


class ConfigurationService:
    """Thread-safe configuration service with hot-reloading and caching."""
    
    def __init__(self, loader: ConfigurationLoader = None):
        self._loader = loader or ConfigurationLoader()
        self._config: Optional[ApplicationConfiguration] = None
        self._lock = threading.RLock()
    
    @contextmanager
    def _thread_safe_access(self):
        """Context manager for thread-safe configuration access."""
        with self._lock:
            yield
    
    def get_configuration(self, max_age: timedelta = timedelta(hours=1)) -> ApplicationConfiguration:
        """Get current configuration with optional staleness check."""
        with self._thread_safe_access():
            if self._config is None or self._config.is_stale(max_age):
                self._config = self._load_configuration()
            return self._config
    
    def force_reload(self) -> ApplicationConfiguration:
        """Force immediate configuration reload."""
        with self._thread_safe_access():
            logger.info("Forcing configuration reload")
            self._config = self._load_configuration()
            return self._config
    
    def _load_configuration(self) -> ApplicationConfiguration:
        """Load complete configuration with comprehensive error handling."""
        try:
            logger.info("Loading application configuration")
            
            window_config = self._loader.load_window_configuration()
            drawing_config = self._loader.load_drawing_configuration() 
            tool_config = self._loader.load_tool_configuration()
            hotbar_config = self._loader.load_hotbar_configuration(window_config.width, window_config.height)
            color_config = self._loader.load_color_configuration()
            storage_config = self._loader.load_storage_configuration()
            
            config = ApplicationConfiguration(
                window=window_config,
                drawing=drawing_config,
                tools=tool_config,
                hotbar=hotbar_config,
                colors=color_config,
                storage=storage_config
            )
            
            logger.info("Configuration loaded successfully")
            logger.debug(f"Window: {config.window.width}x{config.window.height}, FPS: {config.window.fps}, Tool: {config.tools.default_tool}")
            
            return config
            
        except ConfigurationError:
            logger.error("Configuration loading failed")
            raise
        except Exception as error:
            logger.error(f"Unexpected configuration error: {error}")
            raise ConfigurationError(f"Configuration loading failed: {error}") from error
    
    @lru_cache(maxsize=1)
    def get_window_title(self) -> str:
        """Get cached window title."""
        return self.get_configuration().window.title
    
    @lru_cache(maxsize=1)
    def get_window_dimensions(self) -> Tuple[int, int]:
        """Get cached window dimensions."""
        config = self.get_configuration()
        return (config.window.width, config.window.height)
    
    def get_current_tool(self) -> str:
        """Get current tool selection."""
        return self.get_configuration().tools.default_tool
    
    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled."""
        return self.get_configuration().storage.debug_mode_enabled


def create_configuration_service() -> ConfigurationService:
    """Factory function for creating configuration service."""
    return ConfigurationService()


def load_application_configuration() -> ApplicationConfiguration:
    """Convenience function for loading complete configuration."""
    loader = ConfigurationLoader()
    service = ConfigurationService(loader)
    return service.get_configuration()


# Backward compatibility layer
class Settings:
    """DEPRECATED: Backward compatibility wrapper."""
    
    class Config:
        """DEPRECATED: Legacy constants."""
        LOG_MAX_BYTES = 1_048_576
        LOG_BACKUP_COUNT = 5
        MIN_WINDOW_SIZE = ConfigurationValidationRules.MIN_WINDOW_SIZE
        MAX_WINDOW_SIZE = ConfigurationValidationRules.MAX_WINDOW_SIZE
        MIN_BRUSH_SIZE = ConfigurationValidationRules.MIN_BRUSH_SIZE
        MAX_BRUSH_SIZE = ConfigurationValidationRules.MAX_BRUSH_SIZE
        MIN_FPS = ConfigurationValidationRules.MIN_FPS
        MAX_FPS = ConfigurationValidationRules.MAX_FPS
        MAX_STROKE_POINTS_LIMIT = ConfigurationValidationRules.MAX_STROKE_POINTS_LIMIT
        MIN_POINT_THRESHOLD = ConfigurationValidationRules.MIN_POINT_THRESHOLD
        MAX_POINT_THRESHOLD = ConfigurationValidationRules.MAX_POINT_THRESHOLD
    
    def __init__(self, config: ApplicationConfiguration):
        # Map all old attributes for backward compatibility
        self.WIDTH = config.window.width
        self.HEIGHT = config.window.height
        self.TITLE = config.window.title
        self.FPS = config.window.fps
        self.MAX_FPS = config.window.max_fps
        self.VSYNC = config.window.vsync_enabled
        self.DOUBLE_BUFFER = config.window.double_buffer_enabled
        self.STROKE_SMOOTHING = config.drawing.stroke_smoothing_enabled
        self.MAX_STROKE_POINTS = config.drawing.max_stroke_points
        self.POINT_DISTANCE_THRESHOLD = config.drawing.point_distance_threshold
        self.DEFAULT_TOOL = config.tools.default_tool
        self.VALID_TOOLS = config.tools.available_tools
        self.BRUSH_SIZE_MIN = config.tools.brush_size_minimum
        self.BRUSH_SIZE_MAX = config.tools.brush_size_maximum
        self.BRUSH_SIZE_STEP = config.tools.brush_size_step
        self.HOTBAR_X = config.hotbar.x_position
        self.HOTBAR_Y = config.hotbar.y_position
        self.HOTBAR_BUTTON_WIDTH = config.hotbar.button_width
        self.HOTBAR_BUTTON_HEIGHT = config.hotbar.button_height
        self.HOTBAR_SPACING = config.hotbar.button_spacing
        self.NEON_COLORS = config.colors.neon_colors
        self.DEBUG = config.storage.debug_mode_enabled
        self.LOG_DIR = config.storage.log_directory
        self.DATABASE_URL = config.storage.database_url
        self.DATA_PATH = config.storage.data_directory
        self.AUTO_SAVE_INTERVAL = config.storage.auto_save_interval_seconds
        self.ASYNC_SAVE = config.storage.async_save_enabled
    
    @classmethod
    def load(cls) -> "Settings":
        """DEPRECATED: Use load_application_configuration() instead."""
        import warnings
        warnings.warn("Settings.load() is deprecated. Use load_application_configuration().", DeprecationWarning, stacklevel=2)
        config = load_application_configuration()
        return cls(config)