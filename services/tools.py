"""
ToolService handles tool mode switching (e.g., brush, pan).
"""

from typing import Any
import logging
from icecream import ic
from core.events import EventBus
from debug import *

if DEBUG:
    ic.configureOutput(prefix='[tools] ')
    logging.getLogger().setLevel(logging.DEBUG)

class ToolService:
    def __init__(self, settings: Any, bus: EventBus):
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
        self.mode = settings.DEFAULT_TOOL
        self._bus = bus
        self._tool_keys = list(self.tools.keys())
        bus.subscribe('key_press', self._on_key)
        logging.info(f"ToolService initialized with mode: {self.mode}")

    def set_mode(self, tool_key: str):
        if tool_key in self.tools:
            self.mode = tool_key
            self._bus.publish('mode_changed', tool_key)
            if DEBUG: ic(f"Tool switched to: {tool_key} - {self.tools[tool_key]}")

    def _on_key(self, key: Any):
        if key in self.tools:
            self.set_mode(key)
        elif key == 'space':
            # Cycle to the next tool
            current_index = self._tool_keys.index(self.mode)
            next_index = (current_index + 1) % len(self._tool_keys)
            self.set_mode(self._tool_keys[next_index])
        if DEBUG: ic(f"Key press handled: {key}")

    @property
    def current_tool_mode(self):
        return self.mode

