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
        self.mode = settings.DEFAULT_TOOL
        bus.subscribe('key_press', self._on_key)
        logging.info(f"ToolService initialized with mode: {self.mode}")

    def _on_key(self, key: Any):
        self.mode = 'pan' if key == 'SPACE' else 'brush'
        if DEBUG: ic(f"Tool switched to: {self.mode}")
