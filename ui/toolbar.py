# ui/toolbar.py (Updated to work with hotbar)
"""
Toolbar Widget

Displays and allows switching between tools.
Now works alongside the hotbar for comprehensive tool management.
"""

from services.tools import ToolService
from core.interfaces import Renderer
from core.event_bus import EventBus

class Toolbar:
    """
    UI widget for displaying additional tool information and shortcuts.
    Works alongside the hotbar for comprehensive tool management.

    Args:
        tool_service (ToolService): Service for tool/mode management.
        renderer (Renderer): Rendering backend for drawing the toolbar.
        bus (EventBus): Event bus for subscribing to mode change events.
    """

    def __init__(
        self,
        tool_service: ToolService,
        renderer: Renderer,
        bus: EventBus
    ) -> None:
        self._tool_service = tool_service
        self._renderer = renderer
        self._current_mode = tool_service.mode
        self._brush_width = 3

        # Subscribe to tool/mode change events
        bus.subscribe('mode_changed', self._on_mode_change)
        bus.subscribe('brush_width_changed', self._on_brush_width_change)

    def _on_mode_change(self, mode: str) -> None:
        """
        Callback invoked when the tool mode changes.
        Updates internal state.
        """
        self._current_mode = mode

    def _on_brush_width_change(self, width: int) -> None:
        """
        Callback invoked when brush width changes.
        Updates internal state.
        """
        self._brush_width = width

    def render(self) -> None:
        """
        Renders the toolbar information.
        Shows current tool details and shortcuts.
        """
        # Position below the hotbar
        y_offset = 70
        
        # Show current tool details
        tool_description = self._tool_service.tools.get(self._current_mode, self._current_mode)
        self._renderer.draw_text(f"Current: {tool_description}", (10, y_offset), 14)
        
        # Show brush width for drawing tools
        if self._current_mode in ['brush', 'eraser']:
            self._renderer.draw_text(f"Width: {self._brush_width}", (10, y_offset + 20), 12)
        
        # Show shortcuts
        shortcuts = [
            "Space: Cycle tools",
            "1-5: Neon colors", 
            "C: Clear canvas",
            "+/-: Brush size",
            "Scroll: Brush size (Draw/Erase)"
        ]
        
        for i, shortcut in enumerate(shortcuts):
            self._renderer.draw_text(shortcut, (10, y_offset + 40 + i * 15), 10, (200, 200, 200))