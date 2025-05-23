"""Simplified application."""

import time
import logging
from dataclasses import dataclass
from typing import Dict, Any
from .core import EventBus, ValidationService, create_memory_storage
from .drawing import create_drawing_engine, create_tool_manager

logger = logging.getLogger(__name__)

@dataclass
class ApplicationSettings:
    """Application settings."""
    window_width: int = 1280
    window_height: int = 720
    window_title: str = "Application"
    target_fps: int = 60
    debug_mode: bool = False

class UnifiedApplication:
    """Simplified unified application."""
    
    def __init__(self, backend, settings=None):
        self.backend = backend
        self.settings = settings or ApplicationSettings()
        self.running = False
        
        # Core services
        self.event_bus = EventBus()
        self.validation_service = ValidationService()
        self.storage = create_memory_storage("app")
        
        # Application services  
        self.drawing_engine = create_drawing_engine(
            backend, self.validation_service, self.event_bus
        )
        self.tool_manager = create_tool_manager(
            self.validation_service, self.event_bus
        )
        
        # State
        self.is_drawing = False
        self.current_color = (255, 255, 255)
        self.brush_size = 5
        
        self._setup_events()
        
    def _setup_events(self):
        """Setup event subscriptions."""
        self.event_bus.subscribe('quit_requested', self._handle_quit)
        self.event_bus.subscribe('mouse_pressed', self._handle_mouse_press)
        self.event_bus.subscribe('mouse_released', self._handle_mouse_release)
        self.event_bus.subscribe('mouse_moved', self._handle_mouse_move)
        
    def initialize(self):
        """Initialize application."""
        # Initialize window
        if hasattr(self.backend, 'init_window'):
            self.backend.init_window(
                self.settings.window_width,
                self.settings.window_height,
                self.settings.window_title
            )
            
        # Start services
        self.drawing_engine.start()
        self.tool_manager.start()
        
        # Set screen size
        self.drawing_engine.set_screen_size(
            self.settings.window_width,
            self.settings.window_height
        )
        
        logger.info("Application initialized")
        
    def run(self):
        """Run application."""
        self.running = True
        target_frame_time = 1.0 / self.settings.target_fps
        
        logger.info("Starting application main loop")
        
        while self.running:
            frame_start = time.time()
            
            # Process events
            if hasattr(self.backend, 'poll_events'):
                events = self.backend.poll_events()
                self._process_events(events)
            
            # Render
            self.drawing_engine.render_frame()
            
            # Frame limiting
            frame_time = time.time() - frame_start
            if frame_time < target_frame_time:
                time.sleep(target_frame_time - frame_time)
                
        self.shutdown()
        
    def shutdown(self):
        """Shutdown application."""
        self.drawing_engine.stop()
        self.tool_manager.stop()
        self.event_bus.shutdown()
        
        if hasattr(self.backend, 'quit'):
            self.backend.quit()
            
        logger.info("Application shutdown")
        
    def _process_events(self, events):
        """Process input events."""
        for event in events:
            # Handle both pygame events and custom event objects
            event_type = None
            event_data = {}
            
            if hasattr(event, 'type'):
                # Custom event object
                event_type = event.type
                event_data = getattr(event, 'data', {})
            elif hasattr(event, '__dict__'):
                # Pygame event - extract type and data
                if 'type' in event.__dict__:
                    event_type = event.__dict__.get('type')
                    event_data = event.__dict__
                    
            if event_type == 'QUIT':
                self.event_bus.publish('quit_requested')
            elif event_type == 'MOUSE_DOWN' or event_type == 'MOUSEBUTTONDOWN':
                pos = event_data.get('pos', (0, 0))
                button = event_data.get('button', 1)
                self.event_bus.publish('mouse_pressed', {'pos': pos, 'button': button})
            elif event_type == 'MOUSE_UP' or event_type == 'MOUSEBUTTONUP':
                pos = event_data.get('pos', (0, 0))
                button = event_data.get('button', 1)
                self.event_bus.publish('mouse_released', {'pos': pos, 'button': button})
            elif event_type == 'MOUSE_MOVE' or event_type == 'MOUSEMOTION':
                pos = event_data.get('pos', (0, 0))
                self.event_bus.publish('mouse_moved', {'pos': pos})
            elif event_type == 'KEY_PRESS' or event_type == 'KEYDOWN':
                key = event_data.get('key', '')
                self.event_bus.publish('key_pressed', {'key': key})
                
    def _handle_quit(self, data):
        """Handle quit."""
        self.running = False
        
    def _handle_mouse_press(self, data):
        """Handle mouse press."""
        pos = data.get('pos', (0, 0))
        button = data.get('button', 1)
        
        if button == 1:  # Left click
            self.is_drawing = True
            self.drawing_engine.start_stroke(pos, self.current_color, self.brush_size)
            logger.info(f"Started drawing at {pos} with color {self.current_color}")
            
    def _handle_mouse_release(self, data):
        """Handle mouse release."""
        button = data.get('button', 1)
        
        if button == 1:  # Left click
            self.is_drawing = False
            self.drawing_engine.finish_current_stroke()
            logger.info("Finished drawing stroke")
            
    def _handle_mouse_move(self, data):
        """Handle mouse move."""
        if self.is_drawing:
            pos = data.get('pos', (0, 0))
            self.drawing_engine.add_stroke_point(pos)

class SimpleApp:
    """Legacy compatibility."""
    
    def __init__(self, settings, engine, clock, input_adapter, bus=None):
        app_settings = ApplicationSettings(
            window_width=getattr(settings, 'WIDTH', 1280),
            window_height=getattr(settings, 'HEIGHT', 720),
            window_title=getattr(settings, 'TITLE', 'Application'),
            target_fps=getattr(settings, 'FPS', 60),
            debug_mode=getattr(settings, 'DEBUG', False)
        )
        
        self.app = UnifiedApplication(engine, app_settings)
        
    def run(self):
        """Run application."""
        self.app.initialize()
        self.app.run()

def create_application(settings, backend):
    """Create application."""
    return UnifiedApplication(backend, settings)