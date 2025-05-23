"""
UndoRedoService manages simple undo/redo stacks tied to stroke events.
"""

from typing import Any, List
import logging
from icecream import ic
from core.event_bus import EventBus

if logging.DEBUG:
    ic.configureOutput(prefix='[undo] ')
    logging.getLogger().setLevel(logging.DEBUG)

class UndoRedoService:
    def __init__(self, bus: EventBus, max_stack_size: int = 100):
        self._undo: List[Any] = []
        self._redo: List[Any] = []
        self._max_stack_size = max_stack_size
        bus.subscribe('stroke_added', self._record)
        logging.info("UndoRedoService initialized with max stack: %d", max_stack_size)

    def _record(self, _):
        self._undo.append(None)
        
        # CRITICAL FIX: Limit stack size to prevent memory issues
        if len(self._undo) > self._max_stack_size:
            self._undo.pop(0)  # Remove oldest entry
            
        if logging.DEBUG: 
            ic(f"Undo recorded. Stack size: {len(self._undo)}")
