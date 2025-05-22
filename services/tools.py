import logging
from typing import Any
from core.events import EventBus

class ToolService:
    """
    Handles tool mode switching and publishes change events.
    """
    def __init__(self, settings: Any, bus: EventBus):
        self._logger = logging.getLogger(__name__)
        self.settings = settings
        self.bus = bus

        # Map of available tools
        self.tools = {
            'brush': 'Freehand Brush',
            'line': 'Line',
            'rect': 'Rectangle',
            'circle': 'Circle',
            'triangle': 'Triangle',
            'eraser': 'Eraser',
            'text': 'Text',
            'pan': 'Pan',
            'integral': 'Integral (∫)',
            'derivative': 'Derivative (dy/dx)',
            'plot': 'Function Plot',
        }

        # Initialize mode from settings.default_tool
        self.mode = settings.default_tool
        self._logger.info(f"ToolService initialized with mode: {self.mode}")

        # Listen for key events to switch tools
        bus.subscribe('key_press', self._on_key)

    def set_mode(self, tool_key: str):
        if tool_key in self.tools:
            self.mode = tool_key
            self.bus.publish('mode_changed', tool_key)
            self._logger.debug(f"Tool switched to: {tool_key} - {self.tools[tool_key]}")

    def _on_key(self, key: Any):
        # Directly switch if key matches a tool
        if key in self.tools:
            self.set_mode(key)
        elif key == 'space':
            # Cycle forward through the list
            keys = list(self.tools)
            idx = keys.index(self.mode)
            self.set_mode(keys[(idx + 1) % len(keys)])
        self._logger.debug(f"Key press handled in ToolService: {key}")

    @property
    def current_tool_mode(self) -> str:
        return self.mode
