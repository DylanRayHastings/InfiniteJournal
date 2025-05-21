"""
UndoRedoService manages simple undo/redo stacks tied to stroke events.
"""

from typing import Any, List
import logging
from icecream import ic
from core.events import EventBus
from debug import *

if DEBUG:
    ic.configureOutput(prefix='[undo] ')
    logging.getLogger().setLevel(logging.DEBUG)

class UndoRedoService:
    def __init__(self, bus: EventBus):
        self._undo: List[Any] = []
        self._redo: List[Any] = []
        bus.subscribe('stroke_added', self._record)
        logging.info("UndoRedoService initialized")

    def _record(self, _):
        self._undo.append(None)
        if DEBUG and VERBOSE_DEBUG: ic(f"Undo recorded. Stack size: {len(self._undo)}")

    def undo(self):
        if self._undo:
            self._undo.pop()
            if DEBUG and VERBOSE_DEBUG: ic(f"Undo executed. Stack size: {len(self._undo)}")

    def redo(self):
        if self._redo:
            self._redo.pop()
            if DEBUG and VERBOSE_DEBUG: ic(f"Redo executed. Stack size: {len(self._redo)}")
