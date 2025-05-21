"""
Main application class: event loop, rendering, input handling.
"""

from typing import List, Any
import pygame
import logging
from icecream import ic
from debug import *

from core.interfaces import Engine, Clock, InputAdapter
from core.events import EventBus
from services.grid import draw_grid
from services.journal import JournalService
from services.tools import ToolService

if DEBUG:
    ic.configureOutput(prefix='[app] ')
    logging.getLogger().setLevel(logging.DEBUG)

class App:
    def __init__(
        self,
        settings: Any,
        engine: Engine,
        clock: Clock,
        input_adapter: InputAdapter,
        journal_service: JournalService,
        tool_service: ToolService,
        undo_service: Any,
        repository: Any,
        exporter: Any,
        widgets: List[Any],
        bus: EventBus
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
        self.bus = bus
        self.running = False
        logging.info("App initialized")

    def run(self):
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
                        current_tool = self.tool.mode
                        if DEBUG: ic(f"Starting tool: {current_tool}")
                        if current_tool in ['brush', 'line', 'rect', 'circle', 'triangle', 'eraser']:
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
                draw_grid(self.engine)
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
