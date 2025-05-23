"""Main application service with drawing and brush width support."""

import logging
import time
from typing import Any, Dict, List, Tuple

from core.event_bus import EventBus
from adapters.pygame_adapter import PygameEngineAdapter

logger = logging.getLogger(__name__)


class App:
    """
    Main application with STABLE drawing and DYNAMIC brush width.
    """

    REQUIRED_SETTINGS = (
        'TITLE', 'WIDTH', 'HEIGHT', 'FPS', 'BRUSH_SIZE_MIN', 'BRUSH_SIZE_MAX', 'NEON_COLORS', 'VALID_TOOLS',
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
        Initialize the App with STABLE drawing system.
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
        self._brush_width: int = 5
        self._brush_color: Tuple[int, int, int] = (255, 255, 255)
        self._neon_map: Dict[str, Tuple[int, int, int]] = {
            str(i + 1): c for i, c in enumerate(self.settings.NEON_COLORS)
        }
        self._current_page_id: str = "main_page"
        
        # CRITICAL FIX: Optimized performance tracking
        self._last_point = None
        self._frame_count = 0
        self._last_frame_time = time.time()

        # CRITICAL FIX: Find hotbar widget properly
        self._hotbar_widget = None
        for widget in self.widgets:
            widget_name = str(type(widget).__name__).lower()
            if 'hotbar' in widget_name:
                self._hotbar_widget = widget
                logger.info("Found hotbar widget: %s", type(widget).__name__)
                break

        if not self._hotbar_widget:
            logger.error("CRITICAL: Hotbar widget not found!")

        # Subscribe to brush width changes
        self.bus.subscribe('brush_width_changed', self._on_brush_width_changed)
        
        # Initialize brush width synchronization
        if self._hotbar_widget and hasattr(self._hotbar_widget, 'get_current_brush_width'):
            try:
                self._brush_width = self._hotbar_widget.get_current_brush_width()
            except Exception as e:
                logger.warning("Failed to get initial brush width: %s", e)
                self._brush_width = 5

        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.info("App initialized with STABLE drawing system")

    def _validate_settings(self) -> None:
        """Validate settings."""
        missing = [attr for attr in self.REQUIRED_SETTINGS if not hasattr(self.settings, attr)]
        if missing:
            raise ValueError(f"Missing required settings attributes: {missing}")

    def run(self) -> None:
        """Launch the application."""
        self._open_window()
        try:
            self._main_loop()
        except KeyboardInterrupt:
            self._logger.info("Run loop interrupted by user")
        except Exception:
            self._logger.exception("Unhandled exception in App.run()")
            raise
        finally:
            self._cleanup()

    def _cleanup(self):
        """Cleanup resources."""
        self._logger.info("Application cleanup completed")

    def _open_window(self) -> None:
        """Open the application window."""
        title = self.settings.TITLE
        width, height = self.settings.WIDTH, self.settings.HEIGHT
        try:
            self.engine.open_window(width, height, title)
            self._logger.info(f"Window opened: {width}×{height} '{title}'")
        except Exception as e:
            self._logger.exception("Failed to open window")
            raise RuntimeError("Failed to initialize UI") from e

    def _main_loop(self) -> None:
        """CRITICAL FIX: Optimized main loop for stable drawing."""
        target_fps = self.settings.FPS
        frame_time = 1.0 / target_fps
        
        while True:
            frame_start = time.time()
            
            try:
                # Get events
                events = self._get_events()
                for evt in events:
                    if not self._handle_event(evt):
                        return
                
                # CRITICAL FIX: Stable render cycle
                self._render_frame_stable()
                
                # CRITICAL FIX: Consistent timing
                elapsed = time.time() - frame_start
                if elapsed < frame_time:
                    # Use clock for precise timing
                    self.clock.tick(target_fps)
                else:
                    # Skip delay if frame took too long
                    self.clock.tick(target_fps * 2)  # Double rate for catch-up
                
            except Exception as e:
                self._logger.error("Error in main loop: %s", e)
                # Continue running

    def _get_events(self) -> List[Any]:
        """Poll events from the engine."""
        try:
            raw = self.engine.poll_events()
            return self.input_adapter.translate(raw)
        except Exception as e:
            self._logger.error("Error getting events: %s", e)
            return []

    def _handle_event(self, evt: Any) -> bool:
        """Dispatch events to handlers."""
        try:
            etype, data = evt.type, evt.data
            if etype == 'QUIT':
                self._logger.info("QUIT received, exiting")
                return False

            handler_name = f"_on_{etype.lower()}"
            handler = getattr(self, handler_name, None)
            if handler:
                handler(data)
        except Exception as e:
            self._logger.error("Error handling event: %s", e)
        return True

    def _on_key_press(self, data: Any) -> None:
        """Handle KEY_PRESS events."""
        try:
            key = data
            if key in ('=', '+'):
                self._brush_width = min(self._brush_width + 1, self.settings.BRUSH_SIZE_MAX)
                self.bus.publish('brush_width_changed', self._brush_width)
            elif key in ('-', '_'):
                self._brush_width = max(self._brush_width - 1, self.settings.BRUSH_SIZE_MIN)
                self.bus.publish('brush_width_changed', self._brush_width)
            elif key in self._neon_map:
                self._brush_color = self._neon_map[key]
            elif key == 'c':
                self._clear_canvas()
            self.bus.publish('key_press', key)
        except Exception as e:
            self._logger.error("Error in key press: %s", e)

    def _on_mouse_click(self, data: Dict[str, Any]) -> None:
        """Handle mouse clicks."""
        try:
            if data.get('button') != 1:
                return

            pos = data.get('pos')
            if not pos:
                return

            # Check if hotbar handled the click
            if self._hotbar_widget and hasattr(self._hotbar_widget, 'handle_mouse_click'):
                try:
                    if self._hotbar_widget.handle_mouse_click(pos, 1):
                        return
                except Exception as e:
                    logger.warning("Hotbar click handling failed: %s", e)

            # Start drawing
            self._on_mouse_down(data)
        except Exception as e:
            self._logger.error("Error in mouse click: %s", e)

    def _on_mouse_move(self, data: Dict[str, Any]) -> None:
        """Handle mouse movement."""
        try:
            pos = data.get('pos')
            if not pos:
                return

            # Update hotbar hover
            if self._hotbar_widget and hasattr(self._hotbar_widget, 'handle_mouse_move'):
                try:
                    self._hotbar_widget.handle_mouse_move(pos)
                except Exception as e:
                    logger.debug("Hotbar hover update failed: %s", e)

            # Handle drawing
            if self._drawing:
                self._handle_drawing_mouse_move(data)
        except Exception as e:
            self._logger.error("Error in mouse move: %s", e)

    def _on_scroll_wheel(self, data: Dict[str, Any]) -> None:
        """CRITICAL FIX: Dynamic brush width during drawing."""
        try:
            direction = data.get('direction', 0)
            current_tool = self.tool.current_tool_mode
            
            # CRITICAL FIX: Allow dynamic resize for brush and eraser
            if current_tool in ['brush', 'eraser'] and direction != 0:
                old_width = self._brush_width
                
                if direction > 0:
                    self._brush_width = min(self._brush_width + 2, self.settings.BRUSH_SIZE_MAX)
                else:
                    self._brush_width = max(self._brush_width - 2, self.settings.BRUSH_SIZE_MIN)
                
                if self._brush_width != old_width:
                    # CRITICAL FIX: Immediately publish change for dynamic drawing
                    self.bus.publish('brush_width_changed', self._brush_width)
                    
                    # CRITICAL FIX: Show dynamic feedback
                    if self._drawing:
                        logger.info("DYNAMIC brush resize during drawing: %d", self._brush_width)
                    else:
                        logger.info("Brush size changed: %d", self._brush_width)
                
        except Exception as e:
            self._logger.error("Error in scroll wheel: %s", e)

    def _on_brush_width_changed(self, width: int) -> None:
        """Handle brush width changes."""
        try:
            if isinstance(width, (int, float)) and 1 <= width <= 200:
                self._brush_width = int(width)
                logger.debug("App brush width updated to: %d", self._brush_width)
        except Exception as e:
            logger.error("Error handling brush width change: %s", e)

    def _clear_canvas(self) -> None:
        """Clear the canvas."""
        try:
            if self.journal:
                self.journal.reset()
                self.bus.publish('page_cleared')
                self._logger.info("Canvas cleared")
        except Exception as e:
            self._logger.error("Error clearing canvas: %s", e)

    def _on_mouse_down(self, data: Dict[str, Any]) -> None:
        """Handle MOUSE_DOWN events."""
        try:
            if data.get('button') != 1:
                return

            # Don't start drawing if over hotbar
            if self._hotbar_widget and hasattr(self._hotbar_widget, 'is_mouse_over_hotbar'):
                try:
                    if self._hotbar_widget.is_mouse_over_hotbar():
                        return
                except Exception as e:
                    logger.debug("Hotbar check failed: %s", e)
            
            self._drawing = True
            x, y = data['pos']
            tool = self.tool.current_tool_mode
            
            if tool in self.settings.VALID_TOOLS and self.journal:
                self.journal.start_stroke(x, y, self._brush_width, self._brush_color)
                self._last_point = (x, y)
                logger.debug("Started drawing with initial width: %d", self._brush_width)
        except Exception as e:
            self._logger.error("Error starting stroke: %s", e)
            self._drawing = False

    def _on_mouse_up(self, data: Dict[str, Any]) -> None:
        """Handle MOUSE_UP events."""
        try:
            if data.get('button') != 1:
                return
            
            if not self._drawing:
                return
                
            self._drawing = False
            
            if self.journal:
                self.journal.end_stroke()
                logger.debug("Finished drawing")
            
            self._last_point = None
        except Exception as e:
            self._logger.error("Failed to end stroke: %s", e)

    def _handle_drawing_mouse_move(self, data: Dict[str, Any]) -> None:
        """CRITICAL FIX: Optimized drawing mouse movement."""
        try:
            x, y = data['pos']
            current_point = (x, y)
            
            # CRITICAL FIX: Optimized point filtering for smooth drawing
            if self._last_point:
                dx = x - self._last_point[0]
                dy = y - self._last_point[1]
                distance_sq = dx * dx + dy * dy
                
                # CRITICAL FIX: Dynamic threshold based on brush size
                threshold = max(1, self._brush_width // 4)
                if distance_sq < threshold:
                    return
            
            if self.journal:
                # CRITICAL FIX: Always use current brush width for dynamic changes
                self.journal.add_point(x, y, self._brush_width)
                self._last_point = current_point
        except Exception as e:
            self._logger.error("Error adding point: %s", e)

    def _render_frame_stable(self) -> None:
        """CRITICAL FIX: Stable render cycle without glitches."""
        try:
            # CRITICAL FIX: Always clear first
            self.engine.clear()
            
            # CRITICAL FIX: Render widgets in stable order
            for widget in self.widgets:
                try:
                    if hasattr(widget, 'render'):
                        widget.render()
                except Exception as e:
                    # Log but continue rendering
                    logger.debug("Widget render error (%s): %s", type(widget).__name__, e)
                    continue
                    
            # CRITICAL FIX: Always present
            self.engine.present()
            
        except Exception as e:
            self._logger.error("CRITICAL: Frame rendering failed: %s", e)