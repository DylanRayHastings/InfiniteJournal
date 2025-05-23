"""
Input handling logic separated from pygame-specific code.
"""

import logging
from typing import Dict, Any, Optional, Callable, Tuple

logger = logging.getLogger(__name__)


class DrawingInputHandler:
    """Handles input events for drawing, independent of input source."""
    
    def __init__(self, canvas, settings):
        self.canvas = canvas
        self.settings = settings
        self._is_drawing = False
        self._neon_colors = {
            '1': (57, 255, 20),   # Neon Green
            '2': (0, 255, 255),   # Neon Blue  
            '3': (255, 20, 147),  # Neon Pink
            '4': (255, 255, 0),   # Neon Yellow
            '5': (255, 97, 3),    # Neon Orange
        }
        
        # Callbacks for UI interactions
        self.on_tool_changed: Optional[Callable[[str], None]] = None
        self.on_brush_width_changed: Optional[Callable[[int], None]] = None
        
    def handle_mouse_down(self, x: int, y: int, button: int) -> bool:
        """Handle mouse down event."""
        if button == 1:  # Left click
            self._is_drawing = True
            success = self.canvas.start_drawing(x, y)
            logger.debug("Mouse down at (%d, %d), drawing started: %s", x, y, success)
            return success
        return False
    
    def handle_mouse_move(self, x: int, y: int) -> bool:
        """Handle mouse move event."""
        if self._is_drawing:
            return self.canvas.continue_drawing(x, y)
        return False
    
    def handle_mouse_up(self, x: int, y: int, button: int) -> bool:
        """Handle mouse up event."""
        if button == 1 and self._is_drawing:
            self._is_drawing = False
            success = self.canvas.end_drawing()
            logger.debug("Mouse up at (%d, %d), drawing ended: %s", x, y, success)
            return success
        return False
    
    def handle_key_press(self, key: str) -> bool:
        """Handle key press event."""
        try:
            # Brush size adjustment
            if key in ('=', '+'):
                current_width = self.canvas._current_brush_width
                new_width = min(current_width + 1, self.settings.BRUSH_SIZE_MAX)
                self.canvas.set_brush_width(new_width)
                if self.on_brush_width_changed:
                    self.on_brush_width_changed(new_width)
                return True
                
            elif key in ('-', '_'):
                current_width = self.canvas._current_brush_width
                new_width = max(current_width - 1, self.settings.BRUSH_SIZE_MIN)
                self.canvas.set_brush_width(new_width)
                if self.on_brush_width_changed:
                    self.on_brush_width_changed(new_width)
                return True
                
            # Neon colors
            elif key in self._neon_colors:
                color = self._neon_colors[key]
                self.canvas.set_brush_color(color)
                logger.debug("Color changed to %s", color)
                return True
                
            # Clear canvas
            elif key == 'c':
                self.canvas.clear()
                return True
                
            # Tool selection
            elif key in self.settings.VALID_TOOLS:
                self.canvas.set_tool(key)
                if self.on_tool_changed:
                    self.on_tool_changed(key)
                logger.debug("Tool changed to: %s", key)
                return True
                
        except Exception as e:
            logger.error("Error handling key press '%s': %s", key, e)
            
        return False
    
    def handle_scroll(self, direction: int) -> bool:
        """Handle scroll wheel for brush size."""
        try:
            current_tool = self.canvas._current_tool
            if current_tool in ['brush', 'eraser']:
                current_width = self.canvas._current_brush_width
                
                if direction > 0:
                    new_width = min(current_width + 2, self.settings.BRUSH_SIZE_MAX)
                else:
                    new_width = max(current_width - 2, self.settings.BRUSH_SIZE_MIN)
                
                if new_width != current_width:
                    self.canvas.set_brush_width(new_width)
                    if self.on_brush_width_changed:
                        self.on_brush_width_changed(new_width)
                    
                    # Show dynamic feedback
                    if self._is_drawing:
                        logger.info("Dynamic brush resize during drawing: %d", new_width)
                    
                    return True
                    
        except Exception as e:
            logger.error("Error handling scroll: %s", e)
            
        return False
    
    def cycle_tool(self) -> None:
        """Cycle to next tool."""
        try:
            tools = self.settings.VALID_TOOLS
            current_tool = self.canvas._current_tool
            
            try:
                current_index = tools.index(current_tool)
            except ValueError:
                current_index = -1
                
            next_index = (current_index + 1) % len(tools)
            next_tool = tools[next_index]
            
            self.canvas.set_tool(next_tool)
            if self.on_tool_changed:
                self.on_tool_changed(next_tool)
                
            logger.info("Cycled tool from %s to %s", current_tool, next_tool)
            
        except Exception as e:
            logger.error("Error cycling tool: %s", e)