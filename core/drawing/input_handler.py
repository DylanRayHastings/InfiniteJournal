"""
Input handling logic - OPTIMIZED

Optimizations: __slots__, pre-computed mappings, reduced function calls.
"""

import logging
from typing import Dict, Optional, Callable, Tuple

logger = logging.getLogger(__name__)

# Pre-computed color mapping for speed
NEON_COLORS = {
    '1': (57, 255, 20),   # Neon Green
    '2': (0, 255, 255),   # Neon Blue  
    '3': (255, 20, 147),  # Neon Pink
    '4': (255, 255, 0),   # Neon Yellow
    '5': (255, 97, 3),    # Neon Orange
}

# Pre-computed key mappings
BRUSH_SIZE_KEYS = {'+', '=', '-', '_'}
CLEAR_KEY = 'c'

class DrawingInputHandler:
    """Handles input events for drawing - OPTIMIZED."""
    __slots__ = ('canvas', 'settings', '_is_drawing', 'on_tool_changed', 'on_brush_width_changed')
    
    def __init__(self, canvas, settings):
        self.canvas = canvas
        self.settings = settings
        self._is_drawing = False
        
        # Callbacks for UI interactions
        self.on_tool_changed: Optional[Callable[[str], None]] = None
        self.on_brush_width_changed: Optional[Callable[[int], None]] = None
        
    def handle_mouse_down(self, x: int, y: int, button: int) -> bool:
        """Handle mouse down event - optimized."""
        if button == 1:  # Left click only
            self._is_drawing = True
            return self.canvas.start_drawing(x, y)
        return False
    
    def handle_mouse_move(self, x: int, y: int) -> bool:
        """Handle mouse move event - optimized."""
        return self.canvas.continue_drawing(x, y) if self._is_drawing else False
    
    def handle_mouse_up(self, x: int, y: int, button: int) -> bool:
        """Handle mouse up event - optimized."""
        if button == 1 and self._is_drawing:
            self._is_drawing = False
            return self.canvas.end_drawing()
        return False
    
    def handle_key_press(self, key: str) -> bool:
        """Handle key press event - HEAVILY OPTIMIZED."""
        # Brush size adjustment - optimized with pre-computed sets
        if key in BRUSH_SIZE_KEYS:
            current_width = self.canvas._current_brush_width
            
            if key in ('+', '='):
                new_width = min(current_width + 1, self.settings.BRUSH_SIZE_MAX)
            else:  # key in ('-', '_')
                new_width = max(current_width - 1, self.settings.BRUSH_SIZE_MIN)
            
            if new_width != current_width:
                self.canvas.set_brush_width(new_width)
                if self.on_brush_width_changed:
                    self.on_brush_width_changed(new_width)
            return True
                
        # Neon colors - optimized with pre-computed dict
        if key in NEON_COLORS:
            self.canvas.set_brush_color(NEON_COLORS[key])
            return True
                
        # Clear canvas - optimized with pre-computed constant
        if key == CLEAR_KEY:
            self.canvas.clear()
            return True
                
        # Tool selection - optimized check
        if key in self.settings.VALID_TOOLS:
            self.canvas.set_tool(key)
            if self.on_tool_changed:
                self.on_tool_changed(key)
            return True
                
        return False
    
    def handle_scroll(self, direction: int) -> bool:
        """Handle scroll wheel - optimized."""
        current_tool = self.canvas._current_tool
        if current_tool in ('brush', 'eraser'):
            current_width = self.canvas._current_brush_width
            
            # Optimized width calculation
            if direction > 0:
                new_width = min(current_width + 2, self.settings.BRUSH_SIZE_MAX)
            else:
                new_width = max(current_width - 2, self.settings.BRUSH_SIZE_MIN)
            
            if new_width != current_width:
                self.canvas.set_brush_width(new_width)
                if self.on_brush_width_changed:
                    self.on_brush_width_changed(new_width)
                return True
                    
        return False
    
    def cycle_tool(self) -> None:
        """Cycle to next tool - optimized."""
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