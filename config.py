"""
Configuration Module

Defines the `Settings` dataclass containing all application-wide constants.
Easily extensible to support environment variables or config files.
"""

from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    """
    Application-wide settings and constants.
    To add dynamic loading (from ./config), modify the `load` classmethod.
    """
    WIDTH: int = 1280                 # Window width (pixels)
    HEIGHT: int = 720                 # Window height (pixels)
    TITLE: str = "InfiniteJournal"    # Window title
    FPS: int = 60                     # Target frames per second
    DEFAULT_TOOL: str = "brush"       # Default drawing tool
    BRUSH_SIZE_MIN: int = 1           # Minimum brush size (pixels)
    BRUSH_SIZE_MAX: int = 100         # Maximum brush size (pixels)

    NEON_COLORS = [
    (57, 255, 20),   # Neon Green
    (0, 255, 255),   # Neon Blue
    (255, 20, 147),  # Neon Pink
    (255, 255, 0),   # Neon Yellow
    (255, 97, 3),    # Neon Orange
    ]


    @classmethod
    def load(cls) -> "Settings":
        """
        Loads settings from environment variables or config file if implemented.
        Currently returns only the defaults defined in the dataclass.

        Returns:
            Settings: An instance with configuration values.
        """
        # Example: (uncomment below to use environment variable overrides)
        # width = int(os.getenv("INFINITE_JOURNAL_WIDTH", cls.WIDTH))
        # height = int(os.getenv("INFINITE_JOURNAL_HEIGHT", cls.HEIGHT))
        # title = os.getenv("INFINITE_JOURNAL_TITLE", cls.TITLE)
        # fps = int(os.getenv("INFINITE_JOURNAL_FPS", cls.FPS))
        # default_tool = os.getenv("INFINITE_JOURNAL_DEFAULT_TOOL", cls.DEFAULT_TOOL)
        # brush_min = int(os.getenv("INFINITE_JOURNAL_BRUSH_SIZE_MIN", cls.BRUSH_SIZE_MIN))
        # brush_max = int(os.getenv("INFINITE_JOURNAL_BRUSH_SIZE_MAX", cls.BRUSH_SIZE_MAX))
        # return cls(width, height, title, fps, default_tool, brush_min, brush_max)

        # Return default values for now
        return cls()
