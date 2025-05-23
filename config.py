"""
Configuration Module

Defines the `Settings` dataclass containing all application-wide constants.
Supports environment variables and validation with performance optimizations.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""
    pass


@dataclass(frozen=True)
class Settings:
    """
    Application-wide settings and constants.
    Loads from environment variables with fallback to defaults.
    Optimized for drawing performance.
    """
    # Rendering / window
    WIDTH: int = field(default_factory=lambda: int(os.getenv("IJ_WIDTH", "1280")))
    HEIGHT: int = field(default_factory=lambda: int(os.getenv("IJ_HEIGHT", "720")))
    TITLE: str = field(default_factory=lambda: os.getenv("IJ_TITLE", "InfiniteJournal"))
    FPS: int = field(default_factory=lambda: int(os.getenv("IJ_FPS", "60")))

    # Performance settings
    MAX_FPS: int = field(default_factory=lambda: int(os.getenv("IJ_MAX_FPS", "120")))
    VSYNC: bool = field(default_factory=lambda: os.getenv("IJ_VSYNC", "true").lower() == "true")
    DOUBLE_BUFFER: bool = field(default_factory=lambda: os.getenv("IJ_DOUBLE_BUFFER", "true").lower() == "true")

    # Drawing performance
    STROKE_SMOOTHING: bool = field(default_factory=lambda: os.getenv("IJ_STROKE_SMOOTHING", "true").lower() == "true")
    MAX_STROKE_POINTS: int = field(default_factory=lambda: int(os.getenv("IJ_MAX_STROKE_POINTS", "1000")))
    POINT_DISTANCE_THRESHOLD: int = field(default_factory=lambda: int(os.getenv("IJ_POINT_THRESHOLD", "2")))

    # Tools
    DEFAULT_TOOL: str = field(default_factory=lambda: os.getenv("IJ_DEFAULT_TOOL", "brush"))
    VALID_TOOLS: ClassVar[List[str]] = [
        "brush", "eraser", "line", "rect", "circle", "parabola"
    ]

    # Brush
    BRUSH_SIZE_MIN: int = field(default_factory=lambda: int(os.getenv("IJ_BRUSH_MIN", "1")))
    BRUSH_SIZE_MAX: int = field(default_factory=lambda: int(os.getenv("IJ_BRUSH_MAX", "100")))

    # Colors optimized for performance
    NEON_COLORS: ClassVar[List[Tuple[int, int, int]]] = [
        (57, 255, 20),   # Neon Green
        (0, 255, 255),   # Neon Blue
        (255, 20, 147),  # Neon Pink
        (255, 255, 0),   # Neon Yellow
        (255, 97, 3),    # Neon Orange
    ]

    # Logging & data
    DEBUG: bool = field(default_factory=lambda: os.getenv("IJ_DEBUG", "false").lower() == "true")
    LOG_DIR: Path = field(default_factory=lambda: Path(os.getenv("IJ_LOG_DIR", "./logs")))
    DATABASE_URL: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./data/journal.db"))
    DATA_PATH: Path = field(default_factory=lambda: Path(os.getenv("IJ_DATA_PATH", "./data")))

    # Persistence performance
    AUTO_SAVE_INTERVAL: float = field(default_factory=lambda: float(os.getenv("IJ_AUTO_SAVE_INTERVAL", "5.0")))
    ASYNC_SAVE: bool = field(default_factory=lambda: os.getenv("IJ_ASYNC_SAVE", "true").lower() == "true")

    # Class-level config for logging and limits
    class Config:
        LOG_MAX_BYTES: ClassVar[int] = 1_048_576
        LOG_BACKUP_COUNT: ClassVar[int] = 5
        # Window size limits
        MIN_WINDOW_SIZE: ClassVar[int] = 100
        MAX_WINDOW_SIZE: ClassVar[int] = 5000
        # Brush size limits
        MIN_BRUSH_SIZE: ClassVar[int] = 1
        MAX_BRUSH_SIZE: ClassVar[int] = 200
        # FPS limits
        MIN_FPS: ClassVar[int] = 1
        MAX_FPS: ClassVar[int] = 240
        # Performance limits
        MAX_STROKE_POINTS_LIMIT: ClassVar[int] = 5000
        MIN_POINT_THRESHOLD: ClassVar[int] = 1
        MAX_POINT_THRESHOLD: ClassVar[int] = 10

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate configuration values including performance settings."""
        # Validate window dimensions
        if not (self.Config.MIN_WINDOW_SIZE <= self.WIDTH <= self.Config.MAX_WINDOW_SIZE):
            raise ConfigurationError(f"Invalid window width: {self.WIDTH} (must be {self.Config.MIN_WINDOW_SIZE}-{self.Config.MAX_WINDOW_SIZE})")
        
        if not (self.Config.MIN_WINDOW_SIZE <= self.HEIGHT <= self.Config.MAX_WINDOW_SIZE):
            raise ConfigurationError(f"Invalid window height: {self.HEIGHT} (must be {self.Config.MIN_WINDOW_SIZE}-{self.Config.MAX_WINDOW_SIZE})")
        
        # Validate FPS
        if not (self.Config.MIN_FPS <= self.FPS <= self.Config.MAX_FPS):
            raise ConfigurationError(f"Invalid FPS: {self.FPS} (must be {self.Config.MIN_FPS}-{self.Config.MAX_FPS})")
        
        if not (self.Config.MIN_FPS <= self.MAX_FPS <= self.Config.MAX_FPS):
            raise ConfigurationError(f"Invalid MAX_FPS: {self.MAX_FPS} (must be {self.Config.MIN_FPS}-{self.Config.MAX_FPS})")
            
        # Validate default tool
        if self.DEFAULT_TOOL not in self.VALID_TOOLS:
            raise ConfigurationError(f"Invalid default tool: {self.DEFAULT_TOOL} (must be one of {self.VALID_TOOLS})")
            
        # Validate brush sizes
        if not (self.Config.MIN_BRUSH_SIZE <= self.BRUSH_SIZE_MIN <= self.Config.MAX_BRUSH_SIZE):
            raise ConfigurationError(f"Invalid brush minimum size: {self.BRUSH_SIZE_MIN} (must be {self.Config.MIN_BRUSH_SIZE}-{self.Config.MAX_BRUSH_SIZE})")
            
        if not (self.Config.MIN_BRUSH_SIZE <= self.BRUSH_SIZE_MAX <= self.Config.MAX_BRUSH_SIZE):
            raise ConfigurationError(f"Invalid brush maximum size: {self.BRUSH_SIZE_MAX} (must be {self.Config.MIN_BRUSH_SIZE}-{self.Config.MAX_BRUSH_SIZE})")
            
        if self.BRUSH_SIZE_MIN > self.BRUSH_SIZE_MAX:
            raise ConfigurationError(f"Brush minimum size ({self.BRUSH_SIZE_MIN}) cannot be greater than maximum size ({self.BRUSH_SIZE_MAX})")

        # Validate performance settings
        if not (1 <= self.MAX_STROKE_POINTS <= self.Config.MAX_STROKE_POINTS_LIMIT):
            raise ConfigurationError(f"Invalid MAX_STROKE_POINTS: {self.MAX_STROKE_POINTS} (must be 1-{self.Config.MAX_STROKE_POINTS_LIMIT})")
        
        if not (self.Config.MIN_POINT_THRESHOLD <= self.POINT_DISTANCE_THRESHOLD <= self.Config.MAX_POINT_THRESHOLD):
            raise ConfigurationError(f"Invalid POINT_DISTANCE_THRESHOLD: {self.POINT_DISTANCE_THRESHOLD} (must be {self.Config.MIN_POINT_THRESHOLD}-{self.Config.MAX_POINT_THRESHOLD})")

        if self.AUTO_SAVE_INTERVAL <= 0:
            raise ConfigurationError(f"Invalid AUTO_SAVE_INTERVAL: {self.AUTO_SAVE_INTERVAL} (must be positive)")

        # Validate title
        if not self.TITLE or not self.TITLE.strip():
            raise ConfigurationError("Window title cannot be empty")

    @classmethod
    def load(cls) -> "Settings":
        """
        Load settings with validation and performance optimization.

        Returns:
            Settings: Validated configuration instance.
            
        Raises:
            ConfigurationError: If configuration is invalid.
        """
        try:
            settings = cls()
            logger.info("Configuration loaded successfully")
            logger.debug("Settings: WIDTH=%d, HEIGHT=%d, FPS=%d, TOOL=%s, SMOOTHING=%s", 
                        settings.WIDTH, settings.HEIGHT, settings.FPS, settings.DEFAULT_TOOL, settings.STROKE_SMOOTHING)
            return settings
        except (ValueError, TypeError) as e:
            raise ConfigurationError(f"Configuration parsing error: {e}") from e