"""Main application service with improved error handling and proper repository usage."""

import logging
import inspect
from typing import Any, Dict, List, Tuple

from core.event_bus import EventBus
from adapters.pygame_adapter import PygameEngineAdapter


class App:
    """
    Main application: orchestrates windowing, event loop, rendering, and input handling.
    """

    REQUIRED_SETTINGS = (
        'TITLE',
        'WIDTH',
        'HEIGHT',
        'FPS',
        'BRUSH_SIZE_MIN',
        'BRUSH_SIZE_MAX',
        'NEON_COLORS',
        'VALID_TOOLS',
    )

    def __init__(
        self,
        settings: Any,
        engine: PygameEngineAdapter,
        clock: Any,
        input_adapter: Any,
        journal_service: Any,
        tool_service: Any,
        undo_service: Any,
        repository: Any,
        exporter: Any,
        widgets: List[Any],
        bus: EventBus,
    ) -> None:
        """
        Initializes the App with required adapters, services, and configuration.

        Args:
            settings: Configuration object with application constants.
            engine: Engine adapter for window management and rendering.
            clock: Clock adapter for frame rate control.
            input_adapter: Adapter to translate raw events into normalized events.
            journal_service: Service to manage stroke recording.
            tool_service: Service to manage current tool mode.
            undo_service: Service for undo/redo operations.
            repository: Data persistence repository.
            exporter: Service to export data (e.g., screenshots).
            widgets: List of UI widget instances to render.
            bus: EventBus for decoupled event communication.

        Raises:
            ValueError: If required settings are missing or invalid.
        """
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

        self._validate_settings()

        # Initialize drawing state
        self._drawing: bool = False
        self._brush_width: int = self.settings.BRUSH_SIZE_MIN
        self._brush_color: Tuple[int, int, int] = (255, 255, 255)
        self._neon_map: Dict[str, Tuple[int, int, int]] = {
            str(i + 1): c for i, c in enumerate(self.settings.NEON_COLORS)
        }
        self._current_page_id: str = "main_page"  # Simple page management

        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.info("App initialized")

    def _validate_settings(self) -> None:
        """
        Validates that settings contain all required attributes with correct types.

        Raises:
            ValueError: If any required setting is missing.
            TypeError: If a setting has an unexpected type.
        """
        missing = [attr for attr in self.REQUIRED_SETTINGS if not hasattr(self.settings, attr)]
        if missing:
            raise ValueError(f"Missing required settings attributes: {missing}")
        if not isinstance(self.settings.NEON_COLORS, (list, tuple)):
            raise TypeError("settings.NEON_COLORS must be a list or tuple of colors")

    def run(self) -> None:
        """
        Launches the application by opening the window and entering the main loop.
        """
        self._open_window()
        try:
            self._main_loop()
        except KeyboardInterrupt:
            self._logger.info("Run loop interrupted by user")
        except Exception:
            self._logger.exception("Unhandled exception in App.run()")
            raise

    def _open_window(self) -> None:
        """
        Opens the application window using the engine adapter.

        Raises:
            RuntimeError: If the engine adapter is misconfigured or fails.
        """
        title = self.settings.TITLE
        width, height = self.settings.WIDTH, self.settings.HEIGHT
        try:
            self.engine.open_window(width, height, title)
            self._logger.info(f"Window opened: {width}×{height} '{title}'")
        except AttributeError as e:
            self._logger.critical("Engine adapter missing open_window()", exc_info=e)
            raise RuntimeError("Invalid engine adapter: missing open_window()") from e
        except Exception as e:
            self._logger.exception("Failed to open window", exc_info=e)
            raise RuntimeError("Failed to initialize UI") from e

    def _main_loop(self) -> None:
        """
        Main event-render loop: processes events, updates state, and renders widgets.
        """
        while True:
            events = self._get_events()
            for evt in events:
                if not self._handle_event(evt):
                    return
            self._render_frame()
            self.clock.tick(self.settings.FPS)

    def _get_events(self) -> List[Any]:
        """
        Polls raw events from the engine and translates them via the input adapter.

        Returns:
            List of normalized event objects.
        """
        raw = self.engine.poll_events()
        return self.input_adapter.translate(raw)

    def _handle_event(self, evt: Any) -> bool:
        """
        Dispatches a single event to the appropriate handler.

        Args:
            evt: Normalized event with 'type' and 'data' attributes.

        Returns:
            False if the loop should exit (e.g., on QUIT), True otherwise.
        """
        etype, data = evt.type, evt.data
        if etype == 'QUIT':
            self._logger.info("QUIT received, exiting")
            return False

        handler_name = f"_on_{etype.lower()}"
        handler = getattr(self, handler_name, None)
        if handler:
            try:
                handler(data)
            except Exception:
                self._logger.exception(f"Error in handler {handler_name}")
        return True

    def _on_key_press(self, data: Any) -> None:
        """
        Handles KEY_PRESS events: adjusts brush or publishes the key on the event bus.
        """
        key = data
        if key in ('=', '+'):
            self._brush_width = min(self._brush_width + 1, self.settings.BRUSH_SIZE_MAX)
            self._logger.debug("Brush size increased to %d", self._brush_width)
        elif key in ('-', '_'):
            self._brush_width = max(self._brush_width - 1, self.settings.BRUSH_SIZE_MIN)
            self._logger.debug("Brush size decreased to %d", self._brush_width)
        elif key in self._neon_map:
            self._brush_color = self._neon_map[key]
            self._logger.debug("Brush color changed to %s", self._brush_color)
        self.bus.publish('key_press', key)

    def _on_mouse_down(self, data: Dict[str, Any]) -> None:
        """
        Handles MOUSE_DOWN events: begins a new stroke.
        """
        if data.get('button') != 1:  # Only handle left mouse button
            return
        
        self._drawing = True
        x, y = data['pos']
        tool = self.tool.current_tool_mode
        
        if tool in self.settings.VALID_TOOLS:
            try:
                self.journal.start_stroke(x, y, self._brush_width, self._brush_color)
                self._logger.debug("Started stroke at (%d, %d) with tool %s", x, y, tool)
            except Exception as e:
                self._logger.error("Error starting stroke: %s", e)
                self._drawing = False

    def _on_mouse_up(self, data: Dict[str, Any]) -> None:
        """
        Handles MOUSE_UP events: ends the current stroke and persists data.
        """
        if data.get('button') != 1:  # Only handle left mouse button
            return
        
        if not self._drawing:
            return
            
        self._drawing = False
        
        try:
            self.journal.end_stroke()
            # Save the current page to the repository
            page = self.journal._page  # Access the current page
            self.repo.save_page(page, self._current_page_id)
            self._logger.debug("Stroke ended and page saved")
        except Exception as e:
            self._logger.error("Failed to persist stroke data: %s", e)

    def _on_mouse_move(self, data: Dict[str, Any]) -> None:
        """
        Handles MOUSE_MOVE events: adds points to an active stroke.
        """
        if not self._drawing:
            return
        
        x, y = data['pos']
        try:
            self.journal.add_point(x, y, self._brush_width)
        except Exception as e:
            self._logger.error("Error adding point to stroke: %s", e)

    def _render_frame(self) -> None:
        """
        Clears the screen, renders all widgets, and presents the frame.
        """
        try:
            self.engine.clear()
            for widget in self.widgets:
                try:
                    sig = inspect.signature(widget.render)
                    if len(sig.parameters) == 1:
                        widget.render(self.engine)
                    else:
                        widget.render()
                except Exception as e:
                    self._logger.error("Error rendering widget %s: %s", type(widget).__name__, e)
            self.engine.present()
        except Exception as e:
            self._logger.error("Error during frame rendering: %s", e)