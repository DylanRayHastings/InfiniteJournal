# services/app.py (Improved point distance threshold for smoother drawing)
"""Main application service with improved smoothing."""

import logging
import inspect
import threading
import queue
import time
from typing import Any, Dict, List, Tuple

from core.event_bus import EventBus
from adapters.pygame_adapter import PygameEngineAdapter


class AsyncPersistenceManager:
    """Manages asynchronous persistence operations."""
    
    def __init__(self, repository):
        self.repository = repository
        self._save_queue = queue.Queue()
        self._worker_thread = None
        self._stop_event = threading.Event()
        self._last_save_time = 0
        self._save_interval = 2.0
        self._start_worker()
        
    def _start_worker(self):
        """Start the background worker thread."""
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        
    def _worker_loop(self):
        """Background thread loop for processing save operations."""
        while not self._stop_event.is_set():
            try:
                page_data = self._save_queue.get(timeout=0.1)
                if page_data is None:
                    break
                    
                page, page_id = page_data
                
                current_time = time.time()
                if current_time - self._last_save_time < self._save_interval:
                    time.sleep(self._save_interval - (current_time - self._last_save_time))
                
                self.repository.save_page(page, page_id)
                self._last_save_time = time.time()
                self._clear_duplicate_requests(page_id)
                
            except queue.Empty:
                continue
            except Exception as e:
                logging.error("Error in async save worker: %s", e)
                
    def _clear_duplicate_requests(self, page_id: str):
        """Remove duplicate save requests from queue."""
        temp_queue = []
        while not self._save_queue.empty():
            try:
                item = self._save_queue.get_nowait()
                if item[1] != page_id:
                    temp_queue.append(item)
            except queue.Empty:
                break
                
        for item in temp_queue:
            self._save_queue.put(item)
    
    def queue_save(self, page, page_id: str):
        """Queue a save operation for background processing."""
        try:
            self._save_queue.put((page, page_id), block=False)
        except queue.Full:
            pass
    
    def shutdown(self):
        """Shutdown the persistence manager."""
        self._stop_event.set()
        self._save_queue.put(None)
        if self._worker_thread:
            self._worker_thread.join(timeout=3.0)


class App:
    """
    Main application with improved drawing smoothness.
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
        Initialize the App with improved smoothing.
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
        
        # Performance optimizations
        self._last_point = None
        self._frame_count = 0
        
        # Async persistence
        self._persistence_manager = AsyncPersistenceManager(self.repo)

        # Find hotbar widget
        self._hotbar_widget = None
        for widget in self.widgets:
            if hasattr(widget, 'handle_mouse_click'):
                self._hotbar_widget = widget
                break

        # Subscribe to brush width changes
        self.bus.subscribe('brush_width_changed', self._on_brush_width_changed)
        
        # Initialize brush width synchronization
        if self._hotbar_widget:
            self._brush_width = self._hotbar_widget.get_current_brush_width()

        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.info("App initialized with improved smoothing")

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
        try:
            self._persistence_manager.shutdown()
            self._logger.info("Application cleanup completed")
        except Exception as e:
            self._logger.error("Error during cleanup: %s", e)

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
        """Main event-render loop."""
        while True:
            events = self._get_events()
            for evt in events:
                if not self._handle_event(evt):
                    return
                    
            self._render_frame()
            self.clock.tick(self.settings.FPS)

    def _get_events(self) -> List[Any]:
        """Poll events from the engine."""
        raw = self.engine.poll_events()
        return self.input_adapter.translate(raw)

    def _handle_event(self, evt: Any) -> bool:
        """Dispatch events to handlers."""
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
        """Handle KEY_PRESS events."""
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

    def _on_mouse_click(self, data: Dict[str, Any]) -> None:
        """Handle mouse clicks."""
        if data.get('button') != 1:
            return

        pos = data.get('pos')
        if not pos:
            return

        # Check if hotbar handled the click
        if self._hotbar_widget and self._hotbar_widget.handle_mouse_click(pos, 1):
            return

        # Start drawing
        self._on_mouse_down(data)

    def _on_mouse_move(self, data: Dict[str, Any]) -> None:
        """Handle mouse movement."""
        pos = data.get('pos')
        if not pos:
            return

        # Update hotbar hover
        if self._hotbar_widget:
            self._hotbar_widget.handle_mouse_move(pos)

        # Handle drawing
        if self._drawing:
            self._handle_drawing_mouse_move(data)

    def _on_scroll_wheel(self, data: Dict[str, Any]) -> None:
        """Handle scroll wheel for brush width."""
        direction = data.get('direction', 0)
        pos = data.get('pos', (0, 0))
        
        # Let hotbar handle scroll first
        if self._hotbar_widget and self._hotbar_widget.handle_scroll_wheel(direction, pos):
            return

        # Fallback handling
        current_tool = self.tool.current_tool_mode
        if current_tool in ['brush', 'eraser'] and direction != 0:
            if direction > 0:
                self._brush_width = min(self._brush_width + 2, self.settings.BRUSH_SIZE_MAX)
            else:
                self._brush_width = max(self._brush_width - 2, self.settings.BRUSH_SIZE_MIN)
            
            self.bus.publish('brush_width_changed', self._brush_width)

    def _on_brush_width_changed(self, width: int) -> None:
        """Handle brush width changes."""
        self._brush_width = max(self.settings.BRUSH_SIZE_MIN, 
                               min(width, self.settings.BRUSH_SIZE_MAX))

    def _clear_canvas(self) -> None:
        """Clear the canvas."""
        try:
            self.journal.reset()
            self.bus.publish('page_cleared')
            self._logger.info("Canvas cleared")
        except Exception as e:
            self._logger.error("Error clearing canvas: %s", e)

    def _on_mouse_down(self, data: Dict[str, Any]) -> None:
        """Handle MOUSE_DOWN events."""
        if data.get('button') != 1:
            return

        # Don't start drawing if over hotbar
        if self._hotbar_widget and self._hotbar_widget.is_mouse_over_hotbar():
            return
        
        self._drawing = True
        x, y = data['pos']
        tool = self.tool.current_tool_mode
        
        if tool in self.settings.VALID_TOOLS:
            try:
                self.journal.start_stroke(x, y, self._brush_width, self._brush_color)
                self._last_point = (x, y)
            except Exception as e:
                self._logger.error("Error starting stroke: %s", e)
                self._drawing = False

    def _on_mouse_up(self, data: Dict[str, Any]) -> None:
        """Handle MOUSE_UP events."""
        if data.get('button') != 1:
            return
        
        if not self._drawing:
            return
            
        self._drawing = False
        
        try:
            self.journal.end_stroke()
            
            # Queue save
            page = self.journal._page
            self._persistence_manager.queue_save(page, self._current_page_id)
            
            self._last_point = None
        except Exception as e:
            self._logger.error("Failed to end stroke: %s", e)

    def _handle_drawing_mouse_move(self, data: Dict[str, Any]) -> None:
        """Handle MOUSE_MOVE for drawing with IMPROVED smoothing."""
        x, y = data['pos']
        current_point = (x, y)
        
        # IMPROVED: Reduce point density less aggressively for smoother curves
        if self._last_point:
            dx = x - self._last_point[0]
            dy = y - self._last_point[1]
            distance_sq = dx * dx + dy * dy
            
            # Reduced threshold for smoother drawing
            if distance_sq < 4:  # 2 pixels minimum (was 9)
                return
        
        try:
            self.journal.add_point(x, y, self._brush_width)
            self._last_point = current_point
        except Exception as e:
            self._logger.error("Error adding point: %s", e)

    def _render_frame(self) -> None:
        """Render frame."""
        try:
            self.engine.clear()
            
            for widget in self.widgets:
                try:
                    widget.render()
                except Exception as e:
                    self._logger.error("Error rendering widget %s: %s", type(widget).__name__, e)
                    
            self.engine.present()
        except Exception as e:
            self._logger.error("Error during frame rendering: %s", e)