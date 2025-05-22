"""
Configuration Module

Defines the `Settings` dataclass containing all application-wide constants.
Easily extensible to support environment variables or config files.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, List, Tuple

@dataclass(frozen=True)
class Settings:
    """
    Application-wide settings and constants.
    To add dynamic loading (from ./config), modify the `load` classmethod.
    """
    # Rendering / window
    WIDTH: int = 1280                 # Window width (pixels)
    HEIGHT: int = 720                 # Window height (pixels)
    TITLE: str = "InfiniteJournal"    # Window title
    FPS: int = 60                     # Target frames per second

    # Tools
    DEFAULT_TOOL: str = "brush"       # Default drawing tool
    VALID_TOOLS: ClassVar[List[str]] = [
        "brush", "eraser", "line", "rect", "circle", "parabola"
    ]

    # Brush
    BRUSH_SIZE_MIN: int = 1           # Minimum brush size (pixels)
    BRUSH_SIZE_MAX: int = 100         # Maximum brush size (pixels)

    # Colors
    NEON_COLORS: ClassVar[List[Tuple[int, int, int]]] = [
        (57, 255, 20),   # Neon Green
        (0, 255, 255),   # Neon Blue
        (255, 20, 147),  # Neon Pink
        (255, 255, 0),   # Neon Yellow
        (255, 97, 3),    # Neon Orange
    ]

    # Logging & data
    DEBUG: bool = False               # Enable debug output
    LOG_DIR: Path = Path("./logs")   # Directory for log files
    DATABASE_URL: str = "./data/database.json"  # File path for JSON-backed storage
    DATA_PATH: Path = Path("./data") # Path for journal data

    # Class-level config for logging
    class Config:
        LOG_MAX_BYTES: ClassVar[int] = 1_048_576
        LOG_BACKUP_COUNT: ClassVar[int] = 5
        MIN_SIZE: ClassVar[int] = 100
        MAX_SIZE: ClassVar[int] = 5000

    @classmethod
    def load(cls) -> "Settings":
        """
        Loads settings from environment variables or config file if implemented.
        Currently returns only the defaults defined in the dataclass.

        Returns:
            Settings: An instance with configuration values.
        """
        # Example overrides (uncomment to enable):
        # width = int(os.getenv("INFINITE_JOURNAL_WIDTH", cls.WIDTH))
        # height = int(os.getenv("INFINITE_JOURNAL_HEIGHT", cls.HEIGHT))
        # title = os.getenv("INFINITE_JOURNAL_TITLE", cls.TITLE)
        # fps = int(os.getenv("INFINITE_JOURNAL_FPS", cls.FPS))
        # default_tool = os.getenv("INFINITE_JOURNAL_DEFAULT_TOOL", cls.DEFAULT_TOOL)
        # return cls(
        #     width, height, title, fps,
        #     default_tool,
        #     cls.VALID_TOOLS,
        #     cls.BRUSH_SIZE_MIN, cls.BRUSH_SIZE_MAX,
        #     cls.NEON_COLORS,
        #     debug, log_dir, database_url, data_path
        # )

        # For now, just return defaults
        return cls()
