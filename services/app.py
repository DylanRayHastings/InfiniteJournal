# services/app.py (Comprehensive fixes for dynamic width and input handling)
"""Enhanced main application service with robust dynamic width support and improved drawing."""

import logging
import inspect
import threading
import queue
import time
import math
from typing import Any, Dict, List, Tuple, Optional

from core.event_bus import EventBus
from adapters.pygame_adapter import PygameEngineAdapter


class AsyncPersistenceManager:
   """Enhanced asynchronous persistence operations manager with robust error handling."""
   
   def __init__(self, repository):
       self.repository = repository
       self._save_queue = queue.Queue(maxsize=20)  # Increased queue size
       self._worker_thread = None
       self._stop_event = threading.Event()
       self._last_save_time = 0
       self._save_interval = 1.0  # Faster saves for better responsiveness
       self._stats = {
           'saves_queued': 0,
           'saves_completed': 0,
           'saves_failed': 0,
           'saves_skipped': 0
       }
       self._start_worker()
       
   def _start_worker(self):
       """Start the background worker thread."""
       self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
       self._worker_thread.start()
       logging.info("Async persistence worker started")
       
   def _worker_loop(self):
       """Background thread loop for processing save operations with enhanced error handling."""
       while not self._stop_event.is_set():
           try:
               page_data = self._save_queue.get(timeout=0.1)
               if page_data is None:
                   break
                   
               page, page_id = page_data
               
               current_time = time.time()
               time_since_last = current_time - self._last_save_time
               if time_since_last < self._save_interval:
                   sleep_time = self._save_interval - time_since_last
                   time.sleep(sleep_time)
               
               try:
                   self.repository.save_page(page, page_id)
                   self._stats['saves_completed'] += 1
                   self._last_save_time = time.time()
                   self._clear_duplicate_requests(page_id)
                   
               except Exception as e:
                   self._stats['saves_failed'] += 1
                   logging.error("Failed to save page %s: %s", page_id, e)
               
           except queue.Empty:
               continue
           except Exception as e:
               logging.error("Error in async save worker: %s", e)
               
   def _clear_duplicate_requests(self, page_id: str):
       """Remove duplicate save requests from queue."""
       temp_queue = []
       duplicates_removed = 0
       
       while not self._save_queue.empty():
           try:
               item = self._save_queue.get_nowait()
               if item[1] != page_id:
                   temp_queue.append(item)
               else:
                   duplicates_removed += 1
           except queue.Empty:
               break
               
       for item in temp_queue:
           try:
               self._save_queue.put_nowait(item)
           except queue.Full:
               self._stats['saves_skipped'] += 1
               break
       
       if duplicates_removed > 0:
           self._stats['saves_skipped'] += duplicates_removed
           logging.debug("Removed %d duplicate save requests", duplicates_removed)
   
   def queue_save(self, page, page_id: str):
       """Queue a save operation for background processing."""
       try:
           self._save_queue.put_nowait((page, page_id))
           self._stats['saves_queued'] += 1
       except queue.Full:
           self._stats['saves_skipped'] += 1
           logging.warning("Save queue full, skipping save for %s", page_id)
   
   def get_stats(self) -> Dict[str, int]:
       """Get persistence statistics."""
       return self._stats.copy()
   
   def shutdown(self):
       """Shutdown the persistence manager."""
       logging.info("Shutting down async persistence manager")
       self._stop_event.set()
       try:
           self._save_queue.put_nowait(None)
       except queue.Full:
           pass
       if self._worker_thread:
           self._worker_thread.join(timeout=5.0)
       logging.info("Async persistence manager shut down. Stats: %s", self._stats)


class App:
   """
   Enhanced main application with robust dynamic width support and comprehensive error handling.
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
       Initialize the enhanced App with robust dynamic width support.
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

       # Enhanced drawing state with validation
       self._drawing: bool = False
       self._brush_width: int = max(settings.BRUSH_SIZE_MIN, min(5, settings.BRUSH_SIZE_MAX))
       self._brush_color: Tuple[int, int, int] = (255, 255, 255)
       self._neon_map: Dict[str, Tuple[int, int, int]] = {
           str(i + 1): c for i, c in enumerate(self.settings.NEON_COLORS)
       }
       self._current_page_id: str = "main_page"
       
       # Enhanced performance optimizations
       self._last_point = None
       self._frame_count = 0
       self._last_mouse_time = 0
       self._mouse_velocity = 0.0
       self._adaptive_point_threshold = 2.0
       self._last_width_change_time = 0
       
       # Performance monitoring with enhanced metrics
       self._performance_stats = {
           'frame_time': 0.0,
           'draw_operations': 0,
           'points_per_second': 0.0,
           'avg_fps': 0.0,
           'memory_usage': 0,
           'stroke_count': 0
       }
       
       # Enhanced async persistence with better error handling
       self._persistence_manager = AsyncPersistenceManager(self.repo)

       # Find hotbar widget with enhanced validation
       self._hotbar_widget = None
       for widget in self.widgets:
           if hasattr(widget, 'handle_mouse_click') and hasattr(widget, 'get_current_brush_width'):
               self._hotbar_widget = widget
               break

       if not self._hotbar_widget:
           logging.warning("No hotbar widget found - brush width synchronization disabled")

       # Subscribe to brush width changes with error handling
       try:
           self.bus.subscribe('brush_width_changed', self._on_brush_width_changed)
       except Exception as e:
           logging.error("Failed to subscribe to brush width changes: %s", e)
       
       # Initialize brush width synchronization
       if self._hotbar_widget:
           try:
               self._brush_width = self._hotbar_widget.get_current_brush_width()
               self._brush_width = max(self.settings.BRUSH_SIZE_MIN, 
                                     min(self._brush_width, self.settings.BRUSH_SIZE_MAX))
           except Exception as e:
               logging.error("Failed to sync initial brush width: %s", e)

       self._logger = logging.getLogger(self.__class__.__name__)
       self._logger.info("Enhanced App initialized with robust dynamic width support")

   def _validate_settings(self) -> None:
       """Validate settings with enhanced checks."""
       missing = [attr for attr in self.REQUIRED_SETTINGS if not hasattr(self.settings, attr)]
       if missing:
           raise ValueError(f"Missing required settings attributes: {missing}")
       
       # Validate ranges
       if self.settings.BRUSH_SIZE_MIN >= self.settings.BRUSH_SIZE_MAX:
           raise ValueError("BRUSH_SIZE_MIN must be less than BRUSH_SIZE_MAX")
       
       if self.settings.WIDTH <= 0 or self.settings.HEIGHT <= 0:
           raise ValueError("Window dimensions must be positive")

   def run(self) -> None:
       """Launch the enhanced application with comprehensive error handling."""
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
       """Cleanup resources with enhanced error handling."""
       try:
           if hasattr(self, '_persistence_manager'):
               self._persistence_manager.shutdown()
           
           # Log final performance stats
           self._log_final_performance_stats()
           
           self._logger.info("Enhanced application cleanup completed")
       except Exception as e:
           self._logger.error("Error during cleanup: %s", e)

   def _log_final_performance_stats(self):
       """Log final performance statistics."""
       try:
           stats = self._performance_stats.copy()
           if hasattr(self, '_persistence_manager'):
               stats.update(self._persistence_manager.get_stats())
           
           self._logger.info("Final performance stats: %s", stats)
       except Exception as e:
           self._logger.error("Error logging final stats: %s", e)

   def _open_window(self) -> None:
       """Open the application window with enhanced error handling."""
       title = self.settings.TITLE
       width, height = self.settings.WIDTH, self.settings.HEIGHT
       try:
           self.engine.open_window(width, height, title)
           self._logger.info(f"Window opened: {width}×{height} '{title}'")
       except Exception as e:
           self._logger.exception("Failed to open window")
           raise RuntimeError("Failed to initialize UI") from e

   def _main_loop(self) -> None:
       """Enhanced main event-render loop with comprehensive performance monitoring."""
       last_performance_log = time.time()
       frame_times = []
       
       while True:
           loop_start = time.time()
           
           # Process events with error handling
           try:
               events = self._get_events()
               for evt in events:
                   if not self._handle_event(evt):
                       return
           except Exception as e:
               self._logger.error("Error processing events: %s", e)
               continue
                   
           # Render frame with error handling
           try:
               self._render_frame()
           except Exception as e:
               self._logger.error("Error rendering frame: %s", e)
               continue
           
           # Performance monitoring with enhanced metrics
           try:
               frame_time = self.clock.tick(self.settings.FPS)
               frame_times.append(frame_time)
               if len(frame_times) > 60:  # Keep last 60 frames
                   frame_times.pop(0)
               
               self._performance_stats['frame_time'] = frame_time
               self._performance_stats['avg_fps'] = self.clock.get_fps()
               self._frame_count += 1
               
               # Log performance stats every 5 seconds
               if time.time() - last_performance_log > 5.0:
                   self._log_performance_stats()
                   last_performance_log = time.time()
                   
           except Exception as e:
               self._logger.error("Error in performance monitoring: %s", e)

   def _log_performance_stats(self) -> None:
       """Log performance statistics with enhanced metrics."""
       try:
           avg_fps = self.clock.get_fps()
           journal_stats = self.journal.get_performance_stats() if hasattr(self.journal, 'get_performance_stats') else {}
           
           self._performance_stats.update({
               'stroke_count': journal_stats.get('stroke_count', 0),
               'total_points': journal_stats.get('total_points', 0),
               'current_width': journal_stats.get('current_width', self._brush_width)
           })
           
           self._logger.debug(
               "Performance: FPS=%.1f, Strokes=%d, Points=%d, Width=%d, Drawing=%s",
               avg_fps,
               self._performance_stats['stroke_count'],
               self._performance_stats['total_points'],
               self._performance_stats['current_width'],
               self._drawing
           )
       except Exception as e:
           self._logger.error("Error logging performance stats: %s", e)

   def _get_events(self) -> List[Any]:
       """Poll events from the engine with error handling."""
       try:
           raw = self.engine.poll_events()
           return self.input_adapter.translate(raw)
       except Exception as e:
           self._logger.error("Error getting events: %s", e)
           return []

   def _handle_event(self, evt: Any) -> bool:
       """Dispatch events to handlers with enhanced processing and error handling."""
       try:
           etype, data = evt.type, evt.data
           if etype == 'QUIT':
               self._logger.info("QUIT received, exiting")
               return False

           handler_name = f"_on_{etype.lower()}"
           handler = getattr(self, handler_name, None)
           if handler:
               try:
                   handler(data)
               except Exception as e:
                   self._logger.exception(f"Error in handler {handler_name}: %s", e)
           
           return True
       except Exception as e:
           self._logger.error("Error handling event %r: %s", evt, e)
           return True  # Continue processing other events

   def _on_key_press(self, data: Any) -> None:
       """Handle KEY_PRESS events with enhanced brush width control."""
       try:
           key = data
           if key in ('=', '+'):
               old_width = self._brush_width
               step = max(1, self._brush_width // 10)  # Adaptive step size
               self._brush_width = min(self._brush_width + step, self.settings.BRUSH_SIZE_MAX)
               if old_width != self._brush_width:
                   self._publish_width_change()
                   self._logger.debug("Brush width increased to: %d", self._brush_width)
           elif key in ('-', '_'):
               old_width = self._brush_width
               step = max(1, self._brush_width // 10)  # Adaptive step size
               self._brush_width = max(self._brush_width - step, self.settings.BRUSH_SIZE_MIN)
               if old_width != self._brush_width:
                   self._publish_width_change()
                   self._logger.debug("Brush width decreased to: %d", self._brush_width)
           elif key in self._neon_map:
               self._brush_color = self._neon_map[key]
               self._logger.debug("Brush color changed to: %s", self._brush_color)
           elif key == 'c':
               self._clear_canvas()
           
           self.bus.publish('key_press', key)
       except Exception as e:
           self._logger.error("Error handling key press %r: %s", data, e)

   def _publish_width_change(self):
       """Publish brush width change with error handling."""
       try:
           self._last_width_change_time = time.time()
           self.bus.publish('brush_width_changed', self._brush_width)
       except Exception as e:
           self._logger.error("Error publishing width change: %s", e)

   def _on_mouse_click(self, data: Dict[str, Any]) -> None:
       """Handle mouse clicks with enhanced processing."""
       try:
           if data.get('button') != 1:
               return

           pos = data.get('pos')
           if not pos:
               return

           # Check if hotbar handled the click
           if self._hotbar_widget:
               try:
                   if self._hotbar_widget.handle_mouse_click(pos, 1):
                       return
               except Exception as e:
                   self._logger.error("Error in hotbar click handling: %s", e)

           # Start drawing
           self._on_mouse_down(data)
       except Exception as e:
           self._logger.error("Error handling mouse click: %s", e)

   def _on_mouse_move(self, data: Dict[str, Any]) -> None:
       """Handle mouse movement with enhanced velocity tracking and adaptive point spacing."""
       try:
           pos = data.get('pos')
           if not pos:
               return

           # Update hotbar hover
           if self._hotbar_widget:
               try:
                   self._hotbar_widget.handle_mouse_move(pos)
               except Exception as e:
                   self._logger.error("Error in hotbar move handling: %s", e)

           # Enhanced velocity tracking
           current_time = time.time()
           if self._last_point and self._last_mouse_time > 0:
               try:
                   dx = pos[0] - self._last_point[0]
                   dy = pos[1] - self._last_point[1]
                   distance = math.sqrt(dx * dx + dy * dy)
                   time_delta = current_time - self._last_mouse_time
                   
                   if time_delta > 0:
                       self._mouse_velocity = distance / time_delta
                       # Adaptive point threshold based on velocity and brush size
                       self._adaptive_point_threshold = max(
                           1.0, 
                           min(self._brush_width / 3.0, self._mouse_velocity / 100.0)
                       )
               except Exception as e:
                   self._logger.error("Error calculating mouse velocity: %s", e)

           # Handle drawing with enhanced movement processing
           if self._drawing:
               self._handle_enhanced_drawing_mouse_move(data)
               
           self._last_mouse_time = current_time
       except Exception as e:
           self._logger.error("Error handling mouse move: %s", e)

   def _on_scroll_wheel(self, data: Dict[str, Any]) -> None:
       """Handle scroll wheel for dynamic brush width adjustment."""
       try:
           direction = data.get('direction', 0)
           pos = data.get('pos', (0, 0))
           
           # Let hotbar handle scroll first
           if self._hotbar_widget:
               try:
                   if self._hotbar_widget.handle_scroll_wheel(direction, pos):
                       return
               except Exception as e:
                   self._logger.error("Error in hotbar scroll handling: %s", e)

           # Enhanced brush width adjustment during drawing
           current_tool = self.tool.current_tool_mode
           if current_tool in ['brush', 'eraser'] and direction != 0:
               old_width = self._brush_width
               
               # Dynamic step size based on current width and drawing state
               if self._drawing:
                   step_size = max(1, self._brush_width // 8)  # Smaller steps during drawing
               else:
                   step_size = max(1, self._brush_width // 5)  # Larger steps when not drawing
               
               if direction > 0:
                   self._brush_width = min(self._brush_width + step_size, self.settings.BRUSH_SIZE_MAX)
               else:
                   self._brush_width = max(self._brush_width - step_size, self.settings.BRUSH_SIZE_MIN)
               
               if old_width != self._brush_width:
                   self._publish_width_change()
                   self._logger.debug("Dynamic brush width change: %d -> %d (drawing: %s)", 
                                    old_width, self._brush_width, self._drawing)
       except Exception as e:
           self._logger.error("Error handling scroll wheel: %s", e)

   def _on_brush_width_changed(self, width: int) -> None:
       """Handle brush width changes with enhanced validation."""
       try:
           old_width = self._brush_width
           self._brush_width = max(self.settings.BRUSH_SIZE_MIN, 
                                  min(width, self.settings.BRUSH_SIZE_MAX))
           
           if old_width != self._brush_width:
               self._last_width_change_time = time.time()
               self._logger.debug("Brush width synchronized: %d -> %d", old_width, self._brush_width)
       except Exception as e:
           self._logger.error("Error handling brush width change: %s", e)

   def _clear_canvas(self) -> None:
       """Clear the canvas with enhanced cleanup."""
       try:
           self.journal.reset()
           self.bus.publish('page_cleared')
           self._performance_stats['stroke_count'] = 0
           self._performance_stats['total_points'] = 0
           self._logger.info("Canvas cleared")
       except Exception as e:
           self._logger.error("Error clearing canvas: %s", e)

   def _on_mouse_down(self, data: Dict[str, Any]) -> None:
       """Handle MOUSE_DOWN events with enhanced state management."""
       try:
           if data.get('button') != 1:
               return

           # Don't start drawing if over hotbar
           if self._hotbar_widget:
               try:
                   if self._hotbar_widget.is_mouse_over_hotbar():
                       return
               except Exception as e:
                   self._logger.error("Error checking hotbar mouse over: %s", e)
           
           self._drawing = True
           x, y = data['pos']
           tool = self.tool.current_tool_mode
           
           if tool in self.settings.VALID_TOOLS:
               try:
                   # Use current brush width for stroke initialization
                   self.journal.start_stroke(x, y, self._brush_width, self._brush_color)
                   self._last_point = (x, y)
                   self._mouse_velocity = 0.0
                   self._adaptive_point_threshold = max(1.0, self._brush_width / 4.0)
                   
                   self._logger.debug("Started stroke at (%d, %d) with width %d", 
                                    x, y, self._brush_width)
               except Exception as e:
                   self._logger.error("Error starting stroke: %s", e)
                   self._drawing = False
       except Exception as e:
           self._logger.error("Error handling mouse down: %s", e)

   def _on_mouse_up(self, data: Dict[str, Any]) -> None:
       """Handle MOUSE_UP events with enhanced completion processing."""
       try:
           if data.get('button') != 1:
               return
           
           if not self._drawing:
               return
               
           self._drawing = False
           
           try:
               self.journal.end_stroke()
               
               # Queue save with performance stats
               page = self.journal._page
               self._persistence_manager.queue_save(page, self._current_page_id)
               
               # Update performance stats
               self._performance_stats['draw_operations'] += 1
               
               self._last_point = None
               self._mouse_velocity = 0.0
               
               self._logger.debug("Stroke completed and queued for save")
           except Exception as e:
               self._logger.error("Failed to end stroke: %s", e)
       except Exception as e:
           self._logger.error("Error handling mouse up: %s", e)

   def _handle_enhanced_drawing_mouse_move(self, data: Dict[str, Any]) -> None:
       """Handle MOUSE_MOVE for drawing with enhanced adaptive spacing and velocity."""
       try:
           x, y = data['pos']
           current_point = (x, y)
           
           # Enhanced adaptive point filtering
           if self._last_point:
               dx = x - self._last_point[0]
               dy = y - self._last_point[1]
               distance_sq = dx * dx + dy * dy
               
               # Dynamic threshold based on brush width, velocity, and drawing mode
               current_tool = self.tool.current_tool_mode
               base_threshold = self._adaptive_point_threshold
               
               # Adjust threshold for different tools
               if current_tool == 'brush':
                   threshold_sq = (base_threshold * 0.7) ** 2  # Denser for brush
               elif current_tool == 'eraser':
                   threshold_sq = (base_threshold * 1.3) ** 2  # Less dense for eraser
               else:
                   threshold_sq = base_threshold ** 2
               
               if distance_sq < threshold_sq:
                   return
           
           try:
               # Add point with current brush width (supports real-time dynamic width)
               self.journal.add_point(x, y, self._brush_width)
               self._last_point = current_point
               
               # Update performance stats
               self._performance_stats['draw_operations'] += 1
               
           except Exception as e:
               self._logger.error("Error adding point: %s", e)
       except Exception as e:
           self._logger.error("Error handling drawing mouse move: %s", e)

   def _render_frame(self) -> None:
       """Render frame with enhanced performance monitoring."""
       render_start = time.time()
       
       try:
           self.engine.clear()
           
           widgets_rendered = 0
           for widget in self.widgets:
               try:
                   widget.render()
                   widgets_rendered += 1
               except Exception as e:
                   self._logger.error("Error rendering widget %s: %s", type(widget).__name__, e)
                   
           self.engine.present()
           
           # Performance tracking
           render_time = time.time() - render_start
           if render_time > 0.020:  # Log if frame takes longer than 50fps
               self._logger.debug("Slow frame render: %.3fs (%d widgets)", 
                                render_time, widgets_rendered)
               
       except Exception as e:
           self._logger.error("Error during frame rendering: %s", e)