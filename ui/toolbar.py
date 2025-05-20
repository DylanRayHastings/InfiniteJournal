"""
Toolbar Widget

Displays and allows switching between tools.
Currently text-based but designed for easy extension to graphical toolbars.
"""

from core.services import ToolService
from core.interfaces import Renderer
from core.events import EventBus

class Toolbar:
    """
    UI widget for displaying the current tool and responding to mode changes.

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

        # Subscribe to tool/mode change events
        bus.subscribe('mode_changed', self._on_mode_change)

    def _on_mode_change(self, mode: str) -> None:
        """
        Callback invoked when the tool mode changes.
        Updates internal state.
        """
        self._current_mode = mode

    def render(self) -> None:
        """
        Renders the toolbar.
        Currently displays the current tool as text.
        Extend this method to support icons or additional controls.
        """
        self._renderer.draw_text(f"Tool: {self._current_mode}", (10, 40), 16)
