"""Main application framework."""

import logging
import time
from infinitejournal.backends.base import Backend
from infinitejournal.config import Config


class Application:
    """Main application class."""
    
    def __init__(self, backend: Backend, config: Config):
        """Initialize application."""
        self.backend = backend
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.frame_count = 0
        self.fps_update_time = 0
        self.current_fps = 0
        
    def run(self):
        """Run the main application loop."""
        try:
            # Initialize backend
            self.backend.initialize()
            self.backend.start()
            
            self.logger.info("Starting main loop...")
            
            # Main loop
            while self.backend.is_running():
                # Get delta time
                delta_time = self.backend.get_delta_time()
                
                # Handle events
                self.backend.handle_events()
                
                # Update
                self.update(delta_time)
                
                # Render
                self.render()
                
                # Update FPS counter
                self.update_fps(delta_time)
                
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            self.backend.shutdown()
            
    def update(self, delta_time: float):
        """Update application state."""
        # TODO: Update camera, world, etc.
        pass
        
    def render(self):
        """Render the frame."""
        # Clear screen
        self.backend.clear()
        
        # TODO: Render world, UI, etc.
        
        # Show FPS if enabled
        if self.config.show_fps:
            self.render_fps()
        
        # Present frame
        self.backend.present()
        
    def render_fps(self):
        """Render FPS counter."""
        # For now, just log it
        if self.current_fps > 0:
            self.logger.debug(f"FPS: {self.current_fps:.1f}")
            
    def update_fps(self, delta_time: float):
        """Update FPS counter."""
        self.frame_count += 1
        self.fps_update_time += delta_time
        
        if self.fps_update_time >= 1.0:
            self.current_fps = self.frame_count / self.fps_update_time
            self.frame_count = 0
            self.fps_update_time = 0
