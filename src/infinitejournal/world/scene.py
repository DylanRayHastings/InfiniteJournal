# src/infinitejournal/world/scene.py
"""Scene management for organizing world objects."""

import numpy as np
from typing import Optional
import logging
from OpenGL.GL import *

from world.camera import Camera, FPSCamera
from world.grid import GridRenderer
from world.player import PlayerController


class Scene:
    """Manages the 3D scene and rendering order."""
    
    def __init__(self):
        """Initialize the scene."""
        self.logger = logging.getLogger(__name__)
        
        # Scene components
        self.player = PlayerController()
        self.grid_renderer = GridRenderer()
        
        # Scene settings
        self.near_plane = 0.1
        self.far_plane = 1000.0
        self.clear_color = (0.0, 0.0, 0.0, 1.0)
        
        # Performance monitoring
        self.frame_count = 0
        self.total_time = 0.0
        
        self._initialized = False
        
    def initialize(self):
        """Initialize scene resources."""
        if self._initialized:
            return
            
        try:
            # Initialize grid renderer
            self.grid_renderer.initialize()
            
            # Set initial player position
            self.player.set_position(np.array([0.0, 1.7, 5.0], dtype=np.float32))
            
            self._initialized = True
            self.logger.info("Scene initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize scene: {e}")
            raise
            
    def update(self, delta_time: float):
        """Update scene state."""
        if not self._initialized:
            self.initialize()
            
        # Update player/camera
        self.player.update(delta_time)
        
        # Update performance stats
        self.frame_count += 1
        self.total_time += delta_time
        
    def render(self):
        """Render the scene."""
        if not self._initialized:
            self.initialize()
            
        # Clear with scene color
        glClearColor(*self.clear_color)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Enable depth testing
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        
        # TODO: Render opaque objects here (future strokes, etc.)
        
        # Render grid last for proper transparency
        self.grid_renderer.render(
            self.player.camera,
            self.near_plane,
            self.far_plane
        )
        
        # TODO: Render UI overlay
        
    def handle_event(self, event):
        """Handle pygame events."""
        self.player.handle_event(event)
        
    def resize(self, width: int, height: int):
        """Handle window resize."""
        # Update viewport
        glViewport(0, 0, width, height)
        
        # Update camera aspect ratio
        aspect_ratio = width / height if height > 0 else 1.0
        self.player.set_aspect_ratio(aspect_ratio)
        
    def set_clear_color(self, color: tuple):
        """Set the background clear color."""
        self.clear_color = tuple(color[:4])
        
    def set_grid_settings(self, **kwargs):
        """Update grid renderer settings."""
        if 'size' in kwargs:
            self.grid_renderer.set_grid_size(kwargs['size'])
        if 'color' in kwargs:
            self.grid_renderer.set_grid_color(kwargs['color'])
        if 'fade_distance' in kwargs:
            self.grid_renderer.set_fade_distance(kwargs['fade_distance'])
            
    def get_performance_stats(self) -> dict:
        """Get performance statistics."""
        avg_frame_time = self.total_time / self.frame_count if self.frame_count > 0 else 0
        fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        
        return {
            'fps': fps,
            'frame_count': self.frame_count,
            'avg_frame_time': avg_frame_time * 1000,  # Convert to milliseconds
            'total_time': self.total_time
        }
        
    def cleanup(self):
        """Clean up scene resources."""
        if self.grid_renderer:
            self.grid_renderer.cleanup()
        self._initialized = False