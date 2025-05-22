import logging
import inspect
from core.events import EventBus
from adapters.pygame_adapter import PygameEngineAdapter

class App:
    """
    Main application: event loop, rendering, and input handling.
    """
    def __init__(
        self,
        settings,
        engine: PygameEngineAdapter,
        clock,
        input_adapter,
        journal_service,
        tool_service,
        undo_service,
        repository,
        exporter,
        widgets,
        bus: EventBus,
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
        self._logger = logging.getLogger(__name__)
        self._logger.info("App initialized")

    def run(self):
        title = type(self.settings).TITLE
        width = self.settings.width
        height = self.settings.height
        fps = self.settings.FPS

        # Initialize window
        try:
            self.engine.open_window(width, height, title)
            self._logger.info(f"Window opened: {width}×{height} '{title}'")
        except AttributeError as e:
            self._logger.critical("Engine adapter misconfigured; missing open_window()", exc_info=e)
            raise RuntimeError("Failed to start UI: invalid engine adapter") from e
        except Exception:
            self._logger.exception("Failed to open window")
            raise

        drawing = False
        current_width = self.settings.BRUSH_SIZE_MIN
        current_color = (255, 255, 255)
        neon_colors = {str(i+1): c for i, c in enumerate(self.settings.NEON_COLORS)}

        try:
            while True:
                raw_events = self.engine.poll_events()
                events = self.input_adapter.translate(raw_events)

                for evt in events:
                    etype = evt.type
                    data = evt.data

                    if etype == 'QUIT':
                        self._logger.info("QUIT received, exiting run loop")
                        return

                    if etype == 'KEY_PRESS':
                        key = data
                        if key in ('=', '+'):
                            current_width = min(current_width + 1, self.settings.BRUSH_SIZE_MAX)
                        elif key in ('-', '_'):
                            current_width = max(current_width - 1, self.settings.BRUSH_SIZE_MIN)
                        elif key in neon_colors:
                            current_color = neon_colors[key]
                        self.bus.publish('key_press', key)

                    if etype == 'MOUSE_DOWN' and data.get('button') == 1:
                        drawing = True
                        x, y = data['pos']
                        tool = self.tool.current_tool_mode
                        # Only begin strokes for tools we actually support/configure
                        if tool in self.settings.VALID_TOOLS:
                            self.journal.start_stroke(x, y, current_width, current_color)

                    if etype == 'MOUSE_UP' and data.get('button') == 1:
                        drawing = False
                        self.journal.end_stroke()

                    if etype == 'MOUSE_MOVE' and drawing:
                        x, y = data['pos']
                        self.journal.add_point(x, y, current_width)

                # Render cycle
                self.engine.clear()
                for widget in self.widgets:
                    sig = inspect.signature(widget.render)
                    if len(sig.parameters) > 1:
                        widget.render(self.engine)
                    else:
                        widget.render()
                self.engine.present()

                self.clock.tick(fps)

        except KeyboardInterrupt:
            self._logger.info("Run loop interrupted by user")
            return
        except Exception:
            self._logger.exception("Unhandled exception in App.run()")
            raise
