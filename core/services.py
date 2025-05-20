"""
Domain services and App orchestration.
"""
from typing import List, Any
import pygame
from core.models import Page, Point
from core.interfaces import Engine, Clock, InputAdapter, Renderer
from core.events import EventBus

class JournalService:
    def __init__(self, bus: EventBus):
        self._bus = bus
        self._page = None
        self.reset()

    def reset(self):
        self._page = Page()
        self._current = None

    def start_stroke(self, x: int, y: int, width: int):
        self._current = self._page.new_stroke()
        self.add_point(x, y, width)

    def add_point(self, x: int, y: int, width: int):
        if self._current is None:
            self.start_stroke(x, y, width)
        self._current.add_point(Point(x, y, width))
        self._bus.publish('stroke_added', None)

    def end_stroke(self):
        self._current = None
        self._bus.publish('stroke_ended', None)

    def render(self, renderer: Renderer):
        for stroke in self._page.strokes:
            pts = [(pt.x, pt.y) for pt in stroke.points]
            w = stroke.points[-1].width if stroke.points else 1
            renderer.draw_stroke(pts, w)

class ToolService:
    def __init__(self, settings: Any, bus: EventBus):
        self.mode = settings.DEFAULT_TOOL
        bus.subscribe('key_press', self._on_key)

    def _on_key(self, key: Any):
        self.mode = 'pan' if key == 'SPACE' else 'brush'

class UndoRedoService:
    def __init__(self, bus: EventBus):
        self._undo: List[Any] = []
        self._redo: List[Any] = []
        bus.subscribe('stroke_added', self._record)

    def _record(self, _):
        self._undo.append(None)

    def undo(self):
        if self._undo:
            self._undo.pop()

    def redo(self):
        if self._redo:
            self._redo.pop()

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

    def run(self):
        """
        Main application loop: handle input, update state, and render.
        """
        self.engine.init_window(
            self.settings.WIDTH,
            self.settings.HEIGHT,
            self.settings.TITLE
        )
        drawing = False
        current_width = self.settings.BRUSH_SIZE_MIN
        while True:
            raw_events = self.engine.poll_events()
            events = self.input_adapter.translate(raw_events)
            for evt in events:
                if evt.type == 'QUIT':
                    return
                elif evt.type == 'MOUSE_DOWN' and evt.data.get('button') == 1:
                    drawing = True
                    x, y = evt.data['pos']
                    self.journal.start_stroke(x, y, current_width)
                elif evt.type == 'MOUSE_UP' and evt.data.get('button') == 1:
                    drawing = False
                    self.journal.end_stroke()
                elif evt.type == 'MOUSE_MOVE' and drawing:
                    x, y = evt.data['pos']
                    self.journal.add_point(x, y, current_width)
                elif evt.type == 'KEY_PRESS':
                    key = evt.data
                    # adjust brush size with + / - keys
                    if key == '=' or key == '+':
                        current_width = min(current_width + 1, self.settings.BRUSH_SIZE_MAX)
                    elif key == '-' or key == '_':
                        current_width = max(current_width - 1, self.settings.BRUSH_SIZE_MIN)
                    self.bus.publish('key_press', key)
            # render
            self.engine.clear()
            self.journal.render(self.engine)
            # optional cursor
            mx, my = pygame.mouse.get_pos() if hasattr(self.engine, 'screen') else (0, 0)
            self.engine.draw_circle((mx, my), current_width)
            for widget in self.widgets:
                widget.render()
            self.engine.present()
            self.clock.tick(self.settings.FPS)
