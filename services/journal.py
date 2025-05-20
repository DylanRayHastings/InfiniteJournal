"""
Handles stroke creation, point management, and rendering.
"""

from typing import Tuple
from core.models import Page, Point
from core.interfaces import Renderer
from core.events import EventBus

import logging
from icecream import ic
from debug import *

if DEBUG:
    ic.configureOutput(prefix='[journal] ')
    logging.getLogger().setLevel(logging.DEBUG)

class JournalService:
    def __init__(self, bus: EventBus):
        self._bus = bus
        self._page = Page()
        self._current = None
        logging.info("JournalService initialized")

    def start_stroke(self, x: int, y: int, width: int, color: Tuple[int, int, int]):
        try:
            self._current = self._page.new_stroke(color)
            if DEBUG: ic(x, y, width, color)
            self.add_point(x, y, width)
        except Exception as e:
            logging.exception("Failed to start stroke")
            raise

    def add_point(self, x: int, y: int, width: int):
        if self._current is None:
            logging.error("Attempted to add point without active stroke")
            raise RuntimeError("start_stroke must be called before add_point")
        try:
            self._current.add_point(Point(x, y, width))
            self._bus.publish('stroke_added', None)
            if DEBUG and VERBOSE_DEBUG: ic(f"Point added: ({x}, {y}, width={width})")
        except Exception as e:
            logging.exception("Failed to add point")
            raise

    def end_stroke(self):
        self._current = None
        self._bus.publish('stroke_ended', None)
        if DEBUG: ic("Stroke ended")

    def render(self, renderer: Renderer):
        try:
            for stroke in self._page.strokes:
                color = stroke.color() if callable(stroke.color) else stroke.color
                if DEBUG and VERBOSE_DEBUG: ic(f"Rendering stroke with {len(stroke.points)} points")
                renderer.draw_stroke(stroke.points, color)
        except Exception as e:
            logging.exception("Failed to render strokes")
            raise
