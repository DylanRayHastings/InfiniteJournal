"""Configuration management for Infinite Journal."""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class Config:
    """Application configuration."""
    
    # Window settings
    window_width: int = 1280
    window_height: int = 720
    window_title: str = "Infinite Journal"
    fullscreen: bool = False
    vsync: bool = True
    
    # OpenGL settings
    gl_version: tuple = (3, 3)
    gl_profile: str = "core"
    clear_color: tuple = (0.0, 0.0, 0.0, 1.0)  # Black background
    
    # Performance settings
    target_fps: int = 60
    show_fps: bool = True
    
    # Camera settings
    fov: float = 45.0
    near_plane: float = 0.1
    far_plane: float = 1000.0
    
    # Input settings
    mouse_sensitivity: float = 0.002
    move_speed: float = 5.0
    
    # Storage settings
    save_directory: Path = field(default_factory=lambda: Path.home() / ".infinitejournal")
    
    def __post_init__(self):
        """Ensure save directory exists."""
        self.save_directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def load_from_file(cls, config_path: Path) -> "Config":
        """Load configuration from JSON file."""
        if config_path.exists():
            with open(config_path, 'r') as f:
                data = json.load(f)
                return cls(**data)
        return cls()
    
    def save_to_file(self, config_path: Path):
        """Save configuration to JSON file."""
        data = {
            'window_width': self.window_width,
            'window_height': self.window_height,
            'window_title': self.window_title,
            'fullscreen': self.fullscreen,
            'vsync': self.vsync,
            'gl_version': list(self.gl_version),
            'gl_profile': self.gl_profile,
            'clear_color': list(self.clear_color),
            'target_fps': self.target_fps,
            'show_fps': self.show_fps,
            'fov': self.fov,
            'near_plane': self.near_plane,
            'far_plane': self.far_plane,
            'mouse_sensitivity': self.mouse_sensitivity,
            'move_speed': self.move_speed,
            'save_directory': str(self.save_directory)
        }
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
