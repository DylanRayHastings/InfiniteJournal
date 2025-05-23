"""
Simplified drawing service.
"""

import logging
from typing import Any, Tuple
from core.event_bus import EventBus
from core.drawing.canvas import DrawingCanvas
from core.drawing.input_handler import DrawingInputHandler

logger = logging.getLogger(__name__)


class SimpleDrawingService:
    """Simple, reliable drawing service."""
    
    def __init__(self, bus: EventBus, settings: Any):
        self.bus = bus
        self.settings = settings
        self.canvas = DrawingCanvas()
        self.input_handler = DrawingInputHandler(self.canvas, settings)
        
        # Connect input handler callbacks
        self.input_handler.on_tool_changed = self._on_tool_changed
        self.input_handler.on_brush_width_changed = self._on_brush_width_changed
        
        logger.info("SimpleDrawingService initialized")
    
    def _on_tool_changed(self, tool: str) -> None:
        """Handle tool changes."""
        self.bus.publish('tool_changed', tool)
        logger.debug("Tool changed: %s", tool)
    
    def _on_brush_width_changed(self, width: int) -> None:
        """Handle brush width changes."""
        self.bus.publish('brush_width_changed', width)
        logger.debug("Brush width changed: %d", width)
    
    def handle_mouse_down(self, x: int, y: int, button: int) -> bool:
        """Handle mouse down event."""
        return self.input_handler.handle_mouse_down(x, y, button)
    
    def handle_mouse_move(self, x: int, y: int) -> bool:
        """Handle mouse move event."""
        return self.input_handler.handle_mouse_move(x, y)
    
    def handle_mouse_up(self, x: int, y: int, button: int) -> bool:
        """Handle mouse up event."""
        return self.input_handler.handle_mouse_up(x, y, button)
    
    def handle_key_press(self, key: str) -> bool:
        """Handle key press event."""
        if key == 'space':
            self.input_handler.cycle_tool()
            return True
        return self.input_handler.handle_key_press(key)
    
    def handle_scroll(self, direction: int) -> bool:
        """Handle scroll event."""
        return self.input_handler.handle_scroll(direction)
    
    def render(self, renderer) -> None:
        """Render the canvas."""
        self.canvas.render(renderer)
    
    def clear_canvas(self) -> None:
        """Clear the canvas."""
        self.canvas.clear()
        self.bus.publish('canvas_cleared')
    
    def get_current_tool(self) -> str:
        """Get current tool."""
        return self.canvas._current_tool
    
    def get_current_brush_width(self) -> int:
        """Get current brush width."""
        return self.canvas._current_brush_width
    
    def get_current_brush_color(self) -> Tuple[int, int, int]:
        """Get current brush color."""
        return self.canvas._current_brush_color
    
    def is_drawing(self) -> bool:
        """Check if currently drawing."""
        return self.canvas.is_drawing()
    
    def get_stroke_count(self) -> int:
        """Get number of strokes."""
        return self.canvas.get_stroke_count()