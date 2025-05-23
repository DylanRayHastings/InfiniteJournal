"""
Bootstrap Factory - Legacy Application Creation
Creates applications for backward compatibility when Universal Services aren't available.
"""

import logging
import warnings
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def create_simple_app(settings) -> Any:
    """
    Create simple app for legacy compatibility.
    
    This function was missing and causing import errors in main.py.
    It creates a basic application when Universal Services Framework isn't available.
    """
    try:
        # Try to create with Universal Services first
        logger.info("Attempting to create app with Universal Services Framework")
        
        from services import (
            create_complete_application,
            integrate_with_existing_backend
        )
        from adapters.pygame_adapter import PygameEngineAdapter
        
        # Create pygame backend
        backend = PygameEngineAdapter()
        
        # Create complete application
        app = create_complete_application(
            backend=backend,
            window_width=getattr(settings, 'WIDTH', 1280),
            window_height=getattr(settings, 'HEIGHT', 720),
            window_title=getattr(settings, 'TITLE', 'InfiniteJournal'),
            target_fps=getattr(settings, 'FPS', 60),
            debug_mode=getattr(settings, 'DEBUG', False)
        )
        
        logger.info("Successfully created app with Universal Services Framework")
        return app
        
    except Exception as universal_error:
        logger.warning(f"Universal Services not available: {universal_error}")
        
        # Fallback to basic pygame app
        logger.info("Creating fallback pygame application")
        return create_basic_pygame_app(settings)


def create_basic_pygame_app(settings) -> Any:
    """
    Create basic pygame application as fallback.
    
    This provides minimal functionality when Universal Services aren't available.
    """
    try:
        from adapters.pygame_adapter import (
            PygameEngineAdapter, 
            PygameInputAdapter,
            PygameClock,
            create_pygame_bus
        )
        
        # Create pygame components
        engine = PygameEngineAdapter()
        input_adapter = PygameInputAdapter(engine)
        clock = PygameClock()
        bus = create_pygame_bus()
        
        # Initialize window
        engine.init_window(
            getattr(settings, 'WIDTH', 1280),
            getattr(settings, 'HEIGHT', 720),
            getattr(settings, 'TITLE', 'InfiniteJournal')
        )
        
        # Create basic app wrapper
        app = BasicPygameApp(settings, engine, clock, input_adapter, bus)
        
        logger.info("Created basic pygame application")
        return app
        
    except Exception as pygame_error:
        logger.error(f"Failed to create pygame app: {pygame_error}")
        
        # Last resort - create minimal app
        return create_minimal_app(settings)


class BasicPygameApp:
    """
    Basic pygame application for fallback compatibility.
    
    Provides minimal drawing functionality when full services aren't available.
    """
    
    def __init__(self, settings, engine, clock, input_adapter, bus):
        self.settings = settings
        self.engine = engine
        self.clock = clock
        self.input_adapter = input_adapter
        self.bus = bus
        
        self.running = False
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Basic state
        self.current_color = (255, 255, 255)  # White
        self.brush_size = 5
        self.drawing = False
        self.last_pos = None
        
    def run(self):
        """Run basic application loop."""
        self.running = True
        target_fps = getattr(self.settings, 'FPS', 60)
        
        self.logger.info("Starting basic pygame application")
        
        try:
            while self.running:
                # Handle events
                events = self.input_adapter.poll_events()
                
                for event in events:
                    if event.type == 'QUIT':
                        self.running = False
                        break
                    elif event.type == 'MOUSE_DOWN':
                        self._handle_mouse_down(event)
                    elif event.type == 'MOUSE_UP':
                        self._handle_mouse_up(event)
                    elif event.type == 'MOUSE_MOVE':
                        self._handle_mouse_move(event)
                    elif event.type == 'KEY_PRESS':
                        self._handle_key_press(event)
                
                # Clear screen
                self.engine.clear((0, 0, 0))  # Black background
                
                # Draw simple instructions
                self._draw_instructions()
                
                # Present frame
                self.engine.present()
                
                # Control frame rate
                self.clock.tick(target_fps)
                
        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
        except Exception as error:
            self.logger.error(f"Application error: {error}")
        finally:
            self.engine.quit()
            self.logger.info("Basic pygame application stopped")
    
    def _handle_mouse_down(self, event):
        """Handle mouse button press."""
        pos = event.data.get('pos', (0, 0))
        button = event.data.get('button', 1)
        
        if button == 1:  # Left click
            self.drawing = True
            self.last_pos = pos
            # Draw initial point
            self.engine.draw_circle(pos, self.brush_size // 2, self.current_color)
    
    def _handle_mouse_up(self, event):
        """Handle mouse button release."""
        self.drawing = False
        self.last_pos = None
    
    def _handle_mouse_move(self, event):
        """Handle mouse movement."""
        if self.drawing and self.last_pos:
            pos = event.data.get('pos', (0, 0))
            
            # Draw line from last position to current
            self.engine.draw_line(
                self.last_pos, 
                pos, 
                self.brush_size, 
                self.current_color
            )
            
            self.last_pos = pos
    
    def _handle_key_press(self, event):
        """Handle key press."""
        key = event.data.get('key', '')
        
        # Simple tool shortcuts
        if key == '1':
            self.current_color = (255, 255, 255)  # White
        elif key == '2':
            self.current_color = (255, 0, 0)      # Red
        elif key == '3':
            self.current_color = (0, 255, 0)      # Green
        elif key == '4':
            self.current_color = (0, 0, 255)      # Blue
        elif key == '5':
            self.current_color = (255, 255, 0)    # Yellow
        elif key == 'space':
            # Clear screen
            pass  # Screen clears automatically each frame
        elif key == 'escape':
            self.running = False
    
    def _draw_instructions(self):
        """Draw simple instructions on screen."""
        instructions = [
            "Basic InfiniteJournal - Click and drag to draw",
            "Keys: 1=White, 2=Red, 3=Green, 4=Blue, 5=Yellow",
            "Space=Clear, Escape=Quit"
        ]
        
        y_offset = 10
        for instruction in instructions:
            self.engine.draw_text(instruction, (10, y_offset), 24, (128, 128, 128))
            y_offset += 30


class MinimalApp:
    """
    Minimal application that just shows an error message.
    
    Used as last resort when nothing else works.
    """
    
    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def run(self):
        """Run minimal app that just logs error."""
        self.logger.error("Unable to create proper application - missing dependencies")
        self.logger.error("Please install pygame and ensure Universal Services Framework is complete")
        
        # Try to show a simple error window if possible
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()  # Hide main window
            
            messagebox.showerror(
                "InfiniteJournal Error",
                "Unable to start application.\n\n"
                "Missing dependencies or incomplete Universal Services Framework.\n"
                "Please check console for detailed error messages."
            )
            
        except Exception:
            # If even tkinter fails, just print error
            print("ERROR: Unable to start InfiniteJournal")
            print("Missing dependencies or incomplete Universal Services Framework")
            print("Check console logs for detailed error messages")


def create_minimal_app(settings) -> MinimalApp:
    """Create minimal error app as last resort."""
    logger.warning("Creating minimal error application")
    return MinimalApp(settings)


# Compatibility functions for different import patterns
def create_app_from_settings(settings) -> Any:
    """Alternative factory function name."""
    return create_simple_app(settings)


def bootstrap_application(settings) -> Any:
    """Another alternative factory function name."""
    return create_simple_app(settings)


# Export all functions
__all__ = [
    'create_simple_app',
    'create_basic_pygame_app', 
    'create_minimal_app',
    'create_app_from_settings',
    'bootstrap_application',
    'BasicPygameApp',
    'MinimalApp'
]