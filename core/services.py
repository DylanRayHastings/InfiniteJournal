"""
Domain services and App orchestration.
"""
from turtle import color
from typing import List, Any, Tuple
import pygame
from core.models import Page, Point
from core.interfaces import Engine, Clock, InputAdapter, Renderer
from core.events import EventBus

import logging
from icecream import ic
from debug import *

if DEBUG:
    ic.configureOutput(prefix='[services] ')
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


class ToolService:
    def __init__(self, settings: Any, bus: EventBus):
        self.mode = settings.DEFAULT_TOOL
        bus.subscribe('key_press', self._on_key)
        logging.info(f"ToolService initialized with mode: {self.mode}")

    def _on_key(self, key: Any):
        self.mode = 'pan' if key == 'SPACE' else 'brush'
        if DEBUG: ic(f"Tool switched to: {self.mode}")


class UndoRedoService:
    def __init__(self, bus: EventBus):
        self._undo: List[Any] = []
        self._redo: List[Any] = []
        bus.subscribe('stroke_added', self._record)
        logging.info("UndoRedoService initialized")

    def _record(self, _):
        self._undo.append(None)
        if DEBUG: ic(f"Undo recorded. Stack size: {len(self._undo)}")

    def undo(self):
        if self._undo:
            self._undo.pop()
            if DEBUG: ic(f"Undo executed. Stack size: {len(self._undo)}")

    def redo(self):
        if self._redo:
            self._redo.pop()
            if DEBUG: ic(f"Redo executed. Stack size: {len(self._redo)}")


class App:
    def __init__(
        self,
        settings: Any,
        engine: Engine,
        clock: Clock,
        input_adapter: InputAdapter,
        journal_service: JournalService,
        tool_service: ToolService,
        undo_service: UndoRedoService,
        repository: Any,
        exporter: Any,
        widgets: List[Any]
    ):
        self.settings = settings
        self.engine = engine
        self.clock = clock
        self.input_adapter = input_adapter
        self.journal = journal_service
        self.tool = tool_service
        self.undo = undo_service
        self.repo = repository
        self.exporter = exporter
        self.widgets = widgets
        self.bus = EventBus()
        self.running = False
        logging.info("App initialized")

    def run(self):
        """
        Main application loop: handle input, update state, and render.
        """
        try:
            self.engine.init_window(
                self.settings.WIDTH,
                self.settings.HEIGHT,
                self.settings.TITLE
            )
            logging.info("Window initialized")
        except Exception as e:
            logging.exception("Failed to initialize window")
            raise

        drawing = False
        current_width = self.settings.BRUSH_SIZE_MIN
        current_color = (255, 255, 255)
        NEON_COLORS = {
            '1': (57, 255, 20),
            '2': (0, 255, 255),
            '3': (255, 20, 147),
            '4': (255, 255, 0),
            '5': (255, 97, 3),
        }

        try:
            while True:
                raw_events = self.engine.poll_events()
                events = self.input_adapter.translate(raw_events)

                for evt in events:
                    if evt.type == 'QUIT':
                        logging.info("QUIT event received")
                        return

                    elif evt.type == 'MOUSE_DOWN' and evt.data.get('button') == 1:
                        drawing = True
                        x, y = evt.data['pos']
                        self.journal.start_stroke(x, y, current_width, current_color)

                    elif evt.type == 'MOUSE_UP' and evt.data.get('button') == 1:
                        drawing = False
                        self.journal.end_stroke()

                    elif evt.type == 'MOUSE_MOVE' and drawing:
                        x, y = evt.data['pos']
                        self.journal.add_point(x, y, current_width)

                    elif evt.type == 'KEY_PRESS':
                        key = evt.data
                        if key in ('=', '+'):
                            current_width = min(current_width + 1, self.settings.BRUSH_SIZE_MAX)
                        elif key in ('-', '_'):
                            current_width = max(current_width - 1, self.settings.BRUSH_SIZE_MIN)
                        elif key == 'SCROLL_UP':
                            current_width = min(current_width + 1, self.settings.BRUSH_SIZE_MAX)
                        elif key == 'SCROLL_DOWN':
                            current_width = max(current_width - 1, self.settings.BRUSH_SIZE_MIN)
                        elif key in NEON_COLORS:
                            current_color = NEON_COLORS[key]
                        self.bus.publish('key_press', key)

                self.engine.clear()
                self.journal.render(self.engine)
                mx, my = pygame.mouse.get_pos() if hasattr(self.engine, 'screen') else (0, 0)
                self.engine.draw_circle((mx, my), current_width, current_color)
                for widget in self.widgets:
                    widget.render()
                self.engine.present()
                self.clock.tick(self.settings.FPS)
        except Exception as e:
            logging.exception("Unhandled exception in App.run()")
            raise
