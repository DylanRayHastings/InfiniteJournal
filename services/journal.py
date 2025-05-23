# services/journal.py (FIXED brush width synchronization and error handling)
"""Journal service with FIXED brush width persistence and robust error boundaries."""

from core.event_bus import EventBus
from core.drawing.models import Page, Point, Stroke
from core.interfaces import Stroke as StrokeType
from services.database import CanvasDatabase
from services.tools import ToolService
from services.calculator import get_line, get_triangle, get_parabola, get_rectangle, get_circle
import logging
import time
import math
from typing import List, Tuple, Any, Optional

# Constants for tool modes
_TOOL_MODES_SIMPLE = {'brush', 'eraser'}
_SHAPED_MODES = {'line', 'rect', 'circle', 'triangle', 'parabola'}

logger = logging.getLogger(__name__)


class JournalServiceError(Exception):
    """Base exception for journal service errors."""
    pass


class JournalService:
    """
    Service for recording, persisting, and rendering drawing strokes with FIXED brush width and error boundaries.
    """

    def __init__(self, bus: EventBus, tool_service: ToolService, database: CanvasDatabase) -> None:
        """
        Initialize JournalService with FIXED brush width handling and error boundaries.
        """
        # Validation with proper error messages
        if bus is None:
            raise ValueError('EventBus cannot be None')
        if tool_service is None:
            raise ValueError('ToolService cannot be None')
        if database is None:
            raise ValueError('CanvasDatabase cannot be None')

        self._bus = bus
        self._tool_service = tool_service
        self._database = database
        
        # Initialize drawing state with error boundaries
        try:
            self._page = Page()
            self._current_stroke = None
            self._start_point = None
            self._last_point = None
            
            # Shape preview system - more robust with error handling
            self._preview_stroke = None
            self._is_drawing_shape = False
            self._preview_start_point = None
            self._preview_end_point = None
            
            # Performance optimizations
            self._last_event_time = 0
            self._event_throttle_interval = 0.05  # 20 FPS for events
            
            # Rendering optimization with error recovery
            self._stroke_cache = []
            self._cache_valid = True
            
            # FIXED: Dynamic brush width tracking with proper initialization
            self._current_brush_width = 5  # Safe default
            self._width_sync_attempts = 0
            self._max_sync_attempts = 3
            
            # Subscribe to brush width changes with error handling
            try:
                bus.subscribe('brush_width_changed', self._on_brush_width_changed)
                logger.debug("Successfully subscribed to brush_width_changed events")
            except Exception as e:
                logger.error("Failed to subscribe to brush width events: %s", e)
                # Continue with default width
            
            logger.info("JournalService initialized with FIXED brush width handling")
            
        except Exception as e:
            logger.error("Critical error initializing JournalService: %s", e)
            raise JournalServiceError(f"Failed to initialize JournalService: {e}") from e

    def _on_brush_width_changed(self, width: int) -> None:
        """Handle brush width changes from hotbar with validation and error handling."""
        try:
            # FIXED: Proper validation and bounds checking
            if isinstance(width, (int, float)) and 1 <= width <= 200:
                old_width = self._current_brush_width
                self._current_brush_width = int(width)
                self._width_sync_attempts = 0  # Reset attempts on successful sync
                logger.debug("Journal brush width updated from %d to %d", old_width, self._current_brush_width)
            else:
                logger.warning("Invalid brush width received: %r, keeping current: %d", width, self._current_brush_width)
                self._width_sync_attempts += 1
                
                # Reset to safe default if too many failed attempts
                if self._width_sync_attempts >= self._max_sync_attempts:
                    self._current_brush_width = 5
                    self._width_sync_attempts = 0
                    logger.warning("Too many invalid width updates, reset to default: 5")
                    
        except Exception as e:
            logger.error("Error handling brush width change: %s", e)
            # Keep current width, don't crash

    def reset(self) -> None:
        """Clear current page and reset state with error handling."""
        try:
            self._page = Page()
            self._current_stroke = None
            self._preview_stroke = None
            self._start_point = None
            self._last_point = None
            self._is_drawing_shape = False
            self._preview_start_point = None
            self._preview_end_point = None
            self._stroke_cache.clear()
            self._cache_valid = False
            logger.info("Journal reset successfully")
            
        except Exception as e:
            logger.error("Error during journal reset: %s", e)
            # Try to initialize minimally
            try:
                self._page = Page()
                self._current_stroke = None
            except:
                pass

    def start_stroke(self, x: int, y: int, width: int, color: Tuple[int, int, int]) -> None:
        """
        Begin a new stroke with FIXED width handling and comprehensive error boundaries.
        """
        try:
            # Validate inputs with error recovery
            try:
                safe_x = max(0, min(9999, int(x)))
                safe_y = max(0, min(9999, int(y)))
                safe_color = self._validate_color(color)
            except (ValueError, TypeError) as e:
                logger.error("Invalid stroke parameters: x=%r, y=%r, color=%r: %s", x, y, color, e)
                # Use safe defaults
                safe_x, safe_y = 100, 100
                safe_color = (255, 255, 255)
            
            # Get current tool mode with error handling
            try:
                mode = self._tool_service.current_tool_mode
                if mode not in (_TOOL_MODES_SIMPLE | _SHAPED_MODES):
                    logger.warning("Unknown tool mode: %s, defaulting to brush", mode)
                    mode = 'brush'
            except Exception as e:
                logger.error("Error getting tool mode: %s", e)
                mode = 'brush'  # Safe fallback
            
            # Determine stroke color based on tool
            stroke_color = (0, 0, 0) if mode == 'eraser' else safe_color
            
            # CRITICAL FIX: Use current brush width from hotbar, not parameter
            actual_width = max(1, min(200, self._current_brush_width))
            logger.debug("Starting stroke with width: %d (mode: %s, requested: %d)", actual_width, mode, width)

            # Create stroke with proper width and error handling
            try:
                self._current_stroke = self._page.new_stroke(stroke_color, actual_width)
                self._start_point = Point(safe_x, safe_y, 0, actual_width)
                self._last_point = self._start_point
                
                # Shape preview system - FIXED with error boundaries
                self._is_drawing_shape = mode in _SHAPED_MODES
                if self._is_drawing_shape:
                    # Store preview points separately with error handling
                    self._preview_start_point = Point(safe_x, safe_y, 0, 1)  # Thin preview
                    self._preview_end_point = Point(safe_x, safe_y, 0, 1)
                    
                    # Create preview stroke that won't interfere with main stroke
                    try:
                        self._preview_stroke = Stroke(color=(128, 128, 128), width=1)  # Gray, thin
                        logger.debug("Started shape preview for mode: %s", mode)
                    except Exception as e:
                        logger.error("Failed to create preview stroke: %s", e)
                        self._preview_stroke = None
                
                self._cache_valid = False

                # For simple tools, add initial point
                if mode in _TOOL_MODES_SIMPLE:
                    self._current_stroke.add_point(self._start_point)
                    logger.debug("Added initial point with width: %d", actual_width)
                    
            except Exception as e:
                logger.error("Failed to create stroke: %s", e)
                # Clean up partial state
                self._current_stroke = None
                self._is_drawing_shape = False
                raise JournalServiceError(f"Failed to start stroke: {e}") from e
                
        except Exception as e:
            logger.error("Critical error starting stroke: %s", e)
            # Ensure we don't leave inconsistent state
            self._current_stroke = None
            self._is_drawing_shape = False

    def add_point(self, x: int, y: int, width: int) -> None:
        """
        Add a point with FIXED width handling and error boundaries.
        """
        if not self._current_stroke:
            logger.debug("add_point called but no active stroke")
            return

        try:
            # Validate coordinates with error recovery
            try:
                safe_x = max(0, min(9999, int(x)))
                safe_y = max(0, min(9999, int(y)))
            except (ValueError, TypeError) as e:
                logger.warning("Invalid point coordinates: x=%r, y=%r: %s", x, y, e)
                return  # Skip invalid points

            # CRITICAL FIX: ALWAYS use current brush width, ignore parameter
            actual_width = max(1, min(200, self._current_brush_width))
            current_time = time.time()
            
            # For shaped tools, update preview with error handling
            if self._is_drawing_shape:
                try:
                    self._preview_end_point = Point(safe_x, safe_y, 0, 1)
                    self._update_shape_preview()
                except Exception as e:
                    logger.error("Error updating shape preview: %s", e)
                return

            # For brush/eraser: Add point with correct width and error handling
            try:
                point = Point(safe_x, safe_y, 0, actual_width)
                self._current_stroke.add_point(point)
                self._last_point = point
                
                # Throttle event publishing for performance
                if current_time - self._last_event_time > self._event_throttle_interval:
                    try:
                        self._bus.publish('stroke_added')
                        self._last_event_time = current_time
                    except Exception as e:
                        logger.error("Error publishing stroke_added event: %s", e)
                        
            except Exception as e:
                logger.error("Error adding point to stroke: %s", e)
                
        except Exception as e:
            logger.error("Critical error adding point: %s", e)

    def end_stroke(self) -> None:
        """
        Finalize stroke with FIXED preview handling and comprehensive error boundaries.
        """
        if not self._current_stroke or not self._start_point:
            logger.debug("end_stroke called but no active stroke")
            return

        try:
            # Get tool mode with error handling
            try:
                mode = self._tool_service.current_tool_mode
            except Exception as e:
                logger.error("Error getting tool mode during stroke end: %s", e)
                mode = 'brush'  # Safe fallback
            
            try:
                # Apply final shape for shaped tools
                if mode in _SHAPED_MODES and self._preview_end_point:
                    self._apply_final_shape(mode)
                    
                self._cache_valid = False
                
                # Publish stroke completion event
                try:
                    self._bus.publish('stroke_added')
                except Exception as e:
                    logger.error("Error publishing stroke completion event: %s", e)
                    
                logger.debug("Stroke completed successfully with mode: %s", mode)
                
            except Exception as e:
                logger.error('Failed to finalize stroke: %s', e)
                # Don't raise - stroke is still valid, just may not be perfect
                
        except Exception as e:
            logger.error("Critical error ending stroke: %s", e)
            
        finally:
            # ALWAYS clean up state, even if errors occurred
            try:
                self._current_stroke = None
                self._preview_stroke = None
                self._start_point = None
                self._last_point = None
                self._is_drawing_shape = False
                self._preview_start_point = None
                self._preview_end_point = None
            except Exception as cleanup_error:
                logger.error("Error during stroke cleanup: %s", cleanup_error)

    def _update_shape_preview(self) -> None:
        """Update shape preview with robust error handling."""
        if not self._is_drawing_shape or not self._preview_start_point or not self._preview_end_point:
            return
            
        try:
            mode = self._tool_service.current_tool_mode
        except Exception as e:
            logger.error("Error getting tool mode for preview: %s", e)
            return
        
        try:
            # Calculate preview shape points with error boundaries
            preview_points = self._calculate_shape(
                mode, 
                self._preview_start_point.x, self._preview_start_point.y,
                self._preview_end_point.x, self._preview_end_point.y,
                width=1  # Thin preview
            )
            
            # Update preview stroke points with error handling
            if self._preview_stroke and preview_points:
                self._preview_stroke.points = preview_points
                
        except Exception as e:
            logger.error("Error updating shape preview: %s", e)
            # Clear preview on error to prevent rendering issues
            if self._preview_stroke:
                self._preview_stroke.points = []

    def _apply_final_shape(self, mode: str) -> None:
        """Apply final shape with proper width and comprehensive error handling."""
        try:
            if not self._preview_end_point:
                self._preview_end_point = self._start_point
                
            start = self._start_point
            end = self._preview_end_point
            
            # Calculate final shape with proper width and error boundaries
            shape_points = self._calculate_shape(
                mode, start.x, start.y, end.x, end.y, 
                width=self._current_brush_width
            )
            
            if shape_points:
                self._current_stroke.points = shape_points
                logger.debug("Applied final shape %s with width: %d", mode, self._current_brush_width)
            else:
                raise ValueError("Shape calculation returned no points")
                
        except Exception as e:
            logger.error("Error applying final shape %s: %s", mode, e)
            # Fallback to simple line with correct width
            try:
                start = self._start_point
                end = self._preview_end_point or start
                self._current_stroke.points = [
                    Point(start.x, start.y, 0, self._current_brush_width),
                    Point(end.x, end.y, 0, self._current_brush_width)
                ]
                logger.debug("Applied fallback line shape")
            except Exception as fallback_error:
                logger.error("Fallback shape creation failed: %s", fallback_error)

    def render(self, renderer: Any) -> None:
        """
        Render all strokes with FIXED width handling and comprehensive error boundaries.
        """
        if not self._page:
            return
            
        try:
            # Render completed strokes with error handling
            self._render_strokes(renderer)
            
            # Render shape preview if active
            if self._is_drawing_shape and self._preview_stroke and self._preview_stroke.points:
                self._render_preview(renderer)
                
        except Exception as e:
            logger.error("Critical error during rendering: %s", e)
            # Continue - don't crash the application

    def _render_strokes(self, renderer: Any) -> None:
        """Render completed strokes with proper width and error boundaries."""
        if not self._page or not self._page.strokes:
            return
            
        for stroke_idx, stroke in enumerate(self._page.strokes):
            try:
                if not stroke or not stroke.points:
                    continue
                    
                # Convert points with error handling
                points = []
                for point in stroke.points:
                    try:
                        if hasattr(point, 'x') and hasattr(point, 'y'):
                            points.append((float(point.x), float(point.y)))
                    except Exception as point_error:
                        logger.debug("Error converting point in stroke %d: %s", stroke_idx, point_error)
                        continue
                
                if points and hasattr(renderer, 'draw_stroke'):
                    # Validate color and width
                    color = self._validate_color(stroke.color)
                    width = max(1, min(200, getattr(stroke, 'width', 3)))
                    
                    try:
                        renderer.draw_stroke(points, color, width)
                    except Exception as render_error:
                        logger.error("Error rendering stroke %d: %s", stroke_idx, render_error)
                        continue
                    
            except Exception as e:
                logger.error("Error processing stroke %d: %s", stroke_idx, e)
                continue

    def _render_preview(self, renderer: Any) -> None:
        """Render shape preview with thin gray line and error handling."""
        try:
            if not self._preview_stroke or not self._preview_stroke.points:
                return
                
            points = []
            for point in self._preview_stroke.points:
                try:
                    if hasattr(point, 'x') and hasattr(point, 'y'):
                        points.append((float(point.x), float(point.y)))
                except Exception as point_error:
                    logger.debug("Error converting preview point: %s", point_error)
                    continue
            
            if points and hasattr(renderer, 'draw_stroke'):
                try:
                    # Gray preview with thin line
                    renderer.draw_stroke(points, (128, 128, 128), 1)
                except Exception as render_error:
                    logger.error("Error rendering preview: %s", render_error)
                
        except Exception as e:
            logger.error("Critical error rendering preview: %s", e)

    @staticmethod
    def _calculate_shape(mode: str, x0: float, y0: float, x1: float, y1: float, width: int = 1) -> List[Point]:
        """
        Calculate shape points with specified width and comprehensive error handling.
        """
        try:
            # Validate inputs
            safe_x0 = max(0, min(9999, float(x0)))
            safe_y0 = max(0, min(9999, float(y0)))
            safe_x1 = max(0, min(9999, float(x1)))
            safe_y1 = max(0, min(9999, float(y1)))
            safe_width = max(1, min(200, int(width)))
            
            # Calculate shape based on mode
            if mode == 'line':
                raw_points = get_line(int(safe_x0), int(safe_y0), int(safe_x1), int(safe_y1))
                return [Point(x, y, 0, safe_width) for x, y in raw_points]
                
            elif mode == 'rect':
                raw_points = get_rectangle(int(safe_x0), int(safe_y0), int(safe_x1), int(safe_y1))
                return [Point(x, y, 0, safe_width) for x, y in raw_points]
                
            elif mode == 'circle':
                center_x = (safe_x0 + safe_x1) / 2
                center_y = (safe_y0 + safe_y1) / 2
                radius = int(math.sqrt((safe_x1 - safe_x0)**2 + (safe_y1 - safe_y0)**2) / 2)
                radius = max(1, min(500, radius))  # Clamp radius
                raw_points = get_circle(int(center_x), int(center_y), radius)
                return [Point(x, y, 0, safe_width) for x, y in raw_points]
                
            elif mode == 'triangle':
                x2, y2 = safe_x1, safe_y0  # Right angle triangle
                raw_points = get_triangle(int(safe_x0), int(safe_y0), int(safe_x1), int(safe_y1), int(x2), int(y2))
                return [Point(x, y, 0, safe_width) for x, y in raw_points]
                
            elif mode == 'parabola':
                x_min = min(safe_x0, safe_x1)
                x_max = max(safe_x0, safe_x1)
                if x_max - x_min < 1:  # Avoid zero-width parabola
                    x_max = x_min + 100
                raw_points = get_parabola(1.0, 0.0, 0.0, float(x_min), float(x_max), 30)
                return [Point(x, y, 0, safe_width) for x, y in raw_points]
                
            else:
                # Fallback to simple line
                return [Point(safe_x0, safe_y0, 0, safe_width), Point(safe_x1, safe_y1, 0, safe_width)]
                
        except Exception as e:
            logger.error("Error calculating shape %s: %s", mode, e)
            # Return safe fallback
            try:
                safe_width = max(1, width) if isinstance(width, (int, float)) else 1
                return [Point(x0, y0, 0, safe_width), Point(x1, y1, 0, safe_width)]
            except:
                return [Point(100, 100, 0, 1), Point(200, 200, 0, 1)]

    def _validate_color(self, color: Any) -> Tuple[int, int, int]:
        """Validate and sanitize color tuple with error recovery."""
        try:
            if isinstance(color, (tuple, list)) and len(color) >= 3:
                r = max(0, min(255, int(color[0])))
                g = max(0, min(255, int(color[1])))
                b = max(0, min(255, int(color[2])))
                return (r, g, b)
        except (ValueError, TypeError, IndexError):
            pass
        
        # Return safe default
        return (255, 255, 255)

    def invalidate_cache(self) -> None:
        """Force cache invalidation for next render with error handling."""
        try:
            self._cache_valid = False
        except Exception as e:
            logger.error("Error invalidating cache: %s", e)

    def get_stroke_count(self) -> int:
        """Get the number of strokes in the current page with error handling."""
        try:
            return len(self._page.strokes) if self._page else 0
        except Exception as e:
            logger.error("Error getting stroke count: %s", e)
            return 0