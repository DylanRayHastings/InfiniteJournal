"""
Simplified Application that focuses on core functionality.

This app uses the SimpleDrawingService for all drawing operations.
"""

import logging
import time
from typing import Any, Dict, List, Tuple

from core.event_bus import EventBus
from services.simple_drawing import SimpleDrawingService

logger = logging.getLogger(__name__)


class SimpleApp:
    """
    Simplified application focused on working drawing functionality.
    """

    def __init__(
        self,
        settings: Any,
        engine: Any,
        clock: Any,
        input_adapter: Any,
        bus: EventBus,
    ) -> None:
        """Initialize the simple app."""
        self.settings = settings
        self.engine = engine
        self.clock = clock
        self.input_adapter = input_adapter
        self.bus = bus
        
        # Initialize drawing service
        self.drawing_service = SimpleDrawingService(bus, settings)
        
        logger.info("SimpleApp initialized")

    def run(self) -> None:
        """Launch the application."""
        self._open_window()
        try:
            self._main_loop()
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        except Exception:
            logger.exception("Unhandled exception in SimpleApp.run()")
            raise

    def _open_window(self) -> None:
        """Open the application window."""
        title = self.settings.TITLE
        width, height = self.settings.WIDTH, self.settings.HEIGHT
        try:
            self.engine.init_window(width, height, title)
            logger.info(f"Window opened: {width}×{height} '{title}'")
        except Exception as e:
            logger.exception("Failed to open window")
            raise RuntimeError("Failed to initialize UI") from e

    def _main_loop(self) -> None:
        """Main application loop."""
        target_fps = self.settings.FPS
        
        while True:
            try:
                # Get and handle events
                events = self._get_events()
                for evt in events:
                    if not self._handle_event(evt):
                        return
                
                # Render frame
                self._render_frame()
                
                # Maintain target FPS
                self.clock.tick(target_fps)
                
            except Exception as e:
                logger.error("Error in main loop: %s", e)
                # Continue running

    def _get_events(self) -> List[Any]:
        """Poll events from the engine."""
        try:
            raw = self.engine.poll_events()
            return self.input_adapter.translate(raw)
        except Exception as e:
            logger.error("Error getting events: %s", e)
            return []

    def _handle_event(self, evt: Any) -> bool:
        """Handle individual events."""
        try:
            etype, data = evt.type, evt.data
            
            if etype == 'QUIT':
                logger.info("QUIT received, exiting")
                return False
            elif etype == 'MOUSE_DOWN':
                pos = data.get('pos', (0, 0))
                button = data.get('button', 1)
                self.drawing_service.handle_mouse_down(pos[0], pos[1], button)
            elif etype == 'MOUSE_MOVE':
                pos = data.get('pos', (0, 0))
                self.drawing_service.handle_mouse_move(pos[0], pos[1])
            elif etype == 'MOUSE_UP':
                pos = data.get('pos', (0, 0))
                button = data.get('button', 1)
                self.drawing_service.handle_mouse_up(pos[0], pos[1], button)
            elif etype == 'KEY_PRESS':
                key = data
                self.drawing_service.handle_key_press(key)
            elif etype == 'SCROLL_WHEEL':
                direction = data.get('direction', 0)
                self.drawing_service.handle_scroll(direction)
                
        except Exception as e:
            logger.error("Error handling event: %s", e)
            
        return True

    def _render_frame(self) -> None:
        """Render a single frame."""
        try:
            # Clear screen
            self.engine.clear()
            
            # Draw simple grid
            self._draw_grid()
            
            # Render drawing service content
            self.drawing_service.render(self.engine)
            
            # Draw simple UI
            self._draw_ui()
            
            # Present frame
            self.engine.present()
            
        except Exception as e:
            logger.error("Error rendering frame: %s", e)

    def _draw_grid(self) -> None:
        """Draw a simple grid background."""
        try:
            if not hasattr(self.engine, 'get_size'):
                return
                
            width, height = self.engine.get_size()
            grid_spacing = 40
            grid_color = (30, 30, 30)
            
            # Draw vertical lines
            for x in range(0, width, grid_spacing):
                self.engine.draw_line((x, 0), (x, height), 1, grid_color)
            
            # Draw horizontal lines  
            for y in range(0, height, grid_spacing):
                self.engine.draw_line((0, y), (width, y), 1, grid_color)
                
        except Exception as e:
            logger.debug("Error drawing grid: %s", e)

    def _draw_ui(self) -> None:
        """Draw simple UI information."""
        try:
            # Current tool
            tool = self.drawing_service.get_current_tool()
            self.engine.draw_text(f"Tool: {tool.capitalize()}", (10, 10), 16, (255, 255, 255))
            
            # Current brush width for drawing tools
            if tool in ['brush', 'eraser']:
                width = self.drawing_service.get_current_brush_width()
                self.engine.draw_text(f"Size: {width}", (10, 30), 14, (255, 255, 255))
            
            # Stroke count
            count = self.drawing_service.get_stroke_count()
            self.engine.draw_text(f"Strokes: {count}", (10, 50), 12, (200, 200, 200))
            
            # Simple instructions
            instructions = [
                "Space: Cycle tools",
                "1-5: Neon colors",
                "C: Clear canvas",
                "+/-: Brush size",
                "Scroll: Brush size"
            ]
            
            for i, instruction in enumerate(instructions):
                self.engine.draw_text(instruction, (10, 80 + i * 15), 10, (150, 150, 150))
                
        except Exception as e:
            logger.debug("Error drawing UI: %s", e)