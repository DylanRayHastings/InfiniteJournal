"""Main application service with improved error handling, optimized rendering, and async persistence."""

import logging
import inspect
import threading
import queue
import time
from typing import Any, Dict, List, Tuple

from core.event_bus import EventBus
from adapters.pygame_adapter import PygameEngineAdapter


class AsyncPersistenceManager:
    """Manages asynchronous persistence operations to avoid blocking the main thread."""
    
    def __init__(self, repository):
        self.repository = repository
        self._save_queue = queue.Queue()
        self._worker_thread = None
        self._stop_event = threading.Event()
        self._last_save_time = 0
        self._save_interval = 1.0  # Save at most once per second
        self._start_worker()
        
    def _start_worker(self):
        """Start the background worker thread."""
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        
    def _worker_loop(self):
        """Background thread loop for processing save operations."""
        while not self._stop_event.is_set():
            try:
                # Wait for save requests with timeout
                page_data = self._save_queue.get(timeout=0.1)
                if page_data is None:  # Shutdown signal
                    break
                    
                page, page_id = page_data
                
                # Throttle saves to avoid excessive I/O
                current_time = time.time()
                if current_time - self._last_save_time < self._save_interval:
                    time.sleep(self._save_interval - (current_time - self._last_save_time))
                
                # Perform the actual save operation
                self.repository.save_page(page, page_id)
                self._last_save_time = time.time()
                
                # Clear any duplicate save requests for the same page
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
                if item[1] != page_id:  # Keep requests for different pages
                    temp_queue.append(item)
            except queue.Empty:
                break
                
        # Put back non-duplicate items
        for item in temp_queue:
            self._save_queue.put(item)
    
    def queue_save(self, page, page_id: str):
        """Queue a save operation for background processing."""
        try:
            # Only queue if not already queued
            self._save_queue.put((page, page_id), block=False)
        except queue.Full:
            logging.warning("Save queue full, skipping save request")
    
    def shutdown(self):
        """Shutdown the persistence manager and wait for pending saves."""
        self._stop_event.set()
        self._save_queue.put(None)  # Signal shutdown
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)


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
        
        # Performance optimizations
        self._last_point = None
        self._point_buffer = []
        self._frame_count = 0
        self._last_render_time = 0
        
        # Async persistence
        self._persistence_manager = AsyncPersistenceManager(self.repo)

        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.info("App initialized with async persistence")

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
        finally:
            self._cleanup()

    def _cleanup(self):
        """Cleanup resources on application exit."""
        try:
            self._persistence_manager.shutdown()
            self._logger.info("Application cleanup completed")
        except Exception as e:
            self._logger.error("Error during cleanup: %s", e)

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
        Optimized for performance with frame timing and reduced allocations.
        """
        while True:
            frame_start = time.time()
            
            events = self._get_events()
            for evt in events:
                if not self._handle_event(evt):
                    return
                    
            # Always render every frame to ensure persistent visibility
            self._render_frame()
            
            # Performance monitoring
            self._frame_count += 1
            if self._frame_count % 60 == 0:  # Log every 60 frames
                frame_time = time.time() - frame_start
                if frame_time > 0.016:  # > 16ms (60 FPS threshold)
                    self._logger.debug("Frame time: %.3fms", frame_time * 1000)
            
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
        elif key == 'c':  # Clear canvas
            self._clear_canvas()
        self.bus.publish('key_press', key)

    def _clear_canvas(self) -> None:
        """Clear the current canvas/page."""
        try:
            self.journal.reset()
            self.bus.publish('page_cleared')
            self._logger.info("Canvas cleared")
        except Exception as e:
            self._logger.error("Error clearing canvas: %s", e)

    def _on_mouse_down(self, data: Dict[str, Any]) -> None:
        """
        Handles MOUSE_DOWN events: begins a new stroke.
        """
        if data.get('button') != 1:  # Only handle left mouse button
            return
        
        self._drawing = True
        x, y = data['pos']
        tool = self.tool.current_tool_mode
        
        # Clear point buffer for new stroke
        self._point_buffer.clear()
        
        if tool in self.settings.VALID_TOOLS:
            try:
                self.journal.start_stroke(x, y, self._brush_width, self._brush_color)
                self._last_point = (x, y)
                self._point_buffer.append((x, y))
                self._logger.debug("Started stroke at (%d, %d) with tool %s", x, y, tool)
            except Exception as e:
                self._logger.error("Error starting stroke: %s", e)
                self._drawing = False

    def _on_mouse_up(self, data: Dict[str, Any]) -> None:
        """
        Handles MOUSE_UP events: ends the current stroke and queues async persistence.
        """
        if data.get('button') != 1:  # Only handle left mouse button
            return
        
        if not self._drawing:
            return
            
        self._drawing = False
        
        try:
            self.journal.end_stroke()
            
            # Queue async save instead of blocking save
            page = self.journal._page
            self._persistence_manager.queue_save(page, self._current_page_id)
            
            # Clear buffers
            self._point_buffer.clear()
            self._last_point = None
            
            self._logger.debug("Stroke ended and queued for async save")
        except Exception as e:
            self._logger.error("Failed to end stroke: %s", e)

    def _on_mouse_move(self, data: Dict[str, Any]) -> None:
        """
        Handles MOUSE_MOVE events: adds points to an active stroke with optimization.
        """
        if not self._drawing:
            return
        
        x, y = data['pos']
        current_point = (x, y)
        
        # Optimize point addition - skip points that are too close
        if self._last_point:
            dx = x - self._last_point[0]
            dy = y - self._last_point[1]
            distance_sq = dx * dx + dy * dy
            
            # Skip points that are too close (reduces point density)
            if distance_sq < 4:  # Less than 2 pixels distance
                return
        
        try:
            self.journal.add_point(x, y, self._brush_width)
            self._last_point = current_point
            self._point_buffer.append(current_point)
            
            # Limit buffer size for performance
            if len(self._point_buffer) > 100:
                self._point_buffer = self._point_buffer[-50:]  # Keep last 50 points
                
        except Exception as e:
            self._logger.error("Error adding point to stroke: %s", e)

    def _render_frame(self) -> None:
        """
        Clears the screen, renders all widgets, and presents the frame.
        ALWAYS renders all widgets to ensure persistent visibility.
        """
        try:
            render_start = time.time()
            
            # Clear the screen buffer
            self.engine.clear()
            
            # Always render all widgets - this ensures content persistence
            for widget in self.widgets:
                try:
                    sig = inspect.signature(widget.render)
                    if len(sig.parameters) == 1:
                        widget.render(self.engine)
                    else:
                        widget.render()
                except Exception as e:
                    self._logger.error("Error rendering widget %s: %s", type(widget).__name__, e)
                    
            # Present the rendered frame
            self.engine.present()
            
            # Track render performance
            render_time = time.time() - render_start
            if render_time > 0.008:  # > 8ms render time
                self._logger.debug("Slow render: %.3fms", render_time * 1000)
                
        except Exception as e:
            self._logger.error("Error during frame rendering: %s", e)