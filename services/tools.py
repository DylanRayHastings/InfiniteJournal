# services/tools.py (Fixed initialization and tool order)
"""
Provides ToolService for managing and switching drawing tools,
publishing change events, and persisting the current tool mode.
"""

import logging
import json
from pathlib import Path
from typing import Any, Dict, List

from core.event_bus import EventBus


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ToolService:
    """Service for managing and persisting the current tool mode."""
    TOOL_STATE_FILENAME: str = "tool_state.json"
    
    # Define tools in the exact order they should appear and cycle
    ORDERED_TOOLS: List[str] = [
        "brush",      # Draw - #1
        "eraser",     # Erase - #2  
        "line",       # Line - #3
        "rect",       # Rectangle - #4
        "circle",     # Circle - #5
        "triangle",   # Triangle - #6
        "parabola",   # Curve - #7
    ]
    
    DEFAULT_TOOLS: Dict[str, str] = {
        "brush": "Freehand Brush",
        "eraser": "Eraser",
        "line": "Line",
        "rect": "Rectangle", 
        "circle": "Circle",
        "triangle": "Triangle",
        "parabola": "Parabolic Curve",
    }

    def __init__(self, settings: Any, bus: EventBus) -> None:
        """
        Initializes the ToolService.
        """
        self._logger = logging.getLogger(self.__class__.__name__)
        self.settings = settings
        self.bus = bus
        self.tools = self.DEFAULT_TOOLS.copy()

        # ALWAYS start with brush as default, ignore persisted state for now
        self.mode = "brush"  # Force brush as default
        
        self._logger.info("ToolService initialized with mode: %s", self.mode)

        try:
            self.bus.subscribe("key_press", self._on_key)
        except Exception as e:
            self._logger.error("Failed to subscribe to key_press events: %s", e)
            raise

    def set_mode(self, tool_key: str) -> None:
        """
        Sets the current tool mode, publishes 'mode_changed' event, and persists it.
        """
        if tool_key not in self.ORDERED_TOOLS:
            self._logger.warning("Attempted to set invalid tool mode: %s", tool_key)
            return
        old = self.mode
        self.mode = tool_key
        self.bus.publish("mode_changed", self.mode)
        self._logger.info("Tool switched from %s to %s", old, self.mode)

    def cycle_mode(self) -> None:
        """
        Cycles forward to the next tool in the ORDERED_TOOLS list.
        """
        try:
            current_idx = self.ORDERED_TOOLS.index(self.mode)
        except ValueError:
            # Current mode not in ordered tools, start from beginning
            current_idx = -1
        
        next_idx = (current_idx + 1) % len(self.ORDERED_TOOLS)
        next_key = self.ORDERED_TOOLS[next_idx]
        self.set_mode(next_key)
        self._logger.info("Cycled from %s to %s", self.mode, next_key)

    def _on_key(self, key: Any) -> None:
        """
        Handles 'key_press' events for switching tool modes.
        """
        if key == "space":
            self.cycle_mode()
            return
        
        # Direct tool selection by key
        if key in self.ORDERED_TOOLS:
            self.set_mode(key)
            self._logger.debug("Direct tool selection: %s", key)

    @property
    def current_tool_mode(self) -> str:
        """
        Returns the current tool key.
        """
        return self.mode
    
    def get_tool_list(self) -> List[str]:
        """Get the ordered list of available tools."""
        return self.ORDERED_TOOLS.copy()