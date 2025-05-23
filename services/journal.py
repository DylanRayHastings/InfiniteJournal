# services/journal.py (UPDATED - Enhanced with new architectural systems)
"""
Enhanced Journal Service with Architectural Integration

Integrates:
- Layered rendering for proper layer separation
- Coordinate system for infinite canvas
- Shape preview system for real-time feedback
- Mathematical curve generation for accurate parabolas

CRITICAL FIXES:
1. Dynamic brush width with proper layer handling
2. Preview system integration without gray artifacts
3. Coordinate system integration for large-scale support
4. Mathematical parabola generation
"""

from core.event_bus import EventBus
from core.drawing.models import Page, Point, Stroke
from services.database import CanvasDatabase
from services.tools import ToolService

# Import new architectural systems
from core.coordinates.infinite_system import WorldCoordinate, CoordinateManager
from core.preview.shape_preview import ShapePreviewSystem, PreviewIntegrationHelper, PreviewStyle
from core.math.curve_generation import CurveGenerationFramework, CurveType, CurveParameters

import logging
import time
import math
from typing import List, Tuple, Any, Optional

logger = logging.getLogger(__name__)

# Tool mode constants
_TOOL_MODES_SIMPLE = {'brush', 'eraser'}
_SHAPED_MODES = {'line', 'rect', 'circle', 'triangle', 'parabola'}


class EnhancedJournalService:
    """
    Enhanced Journal Service with architectural integration.
    
    Provides:
    - Layered rendering integration
    - Infinite coordinate system support
    - Non-destructive shape preview
    - Mathematical curve generation
    - Dynamic brush width during drawing
    """

    def __init__(self, bus: EventBus, tool_service: ToolService, database: CanvasDatabase,
                 coordinate_manager: Optional[CoordinateManager] = None,
                 preview_system: Optional[ShapePreviewSystem] = None,
                 curve_framework: Optional[CurveGenerationFramework] = None) -> None:
        """
        Initialize Enhanced Journal Service.
        """
        if bus is None:
            raise ValueError('bus must not be None')
        if tool_service is None:
            raise ValueError('tool_service must not be None')
        if database is None:
            raise ValueError('database must not be None')

        self._bus = bus
        self._tool_service = tool_service
        self._database = database
        self._page = Page()
        
        # Drawing state
        self._current_stroke = None
        self._start_point = None
        self._last_point = None
        self._is_drawing = False
        self._current_brush_width = 5
        
        # Shape drawing state
        self._is_drawing_shape = False
        self._shape_start_coord = None
        self._shape_end_coord = None
        
        # Architectural system integration
        self.coordinate_manager = coordinate_manager
        self.preview_system = preview_system
        self.preview_helper = PreviewIntegrationHelper(preview_system) if preview_system else None
        self.curve_framework = curve_framework or CurveGenerationFramework()
        
        # Performance optimizations
        self._last_event_time = 0
        self._event_throttle_interval = 0.016  # ~60 FPS
        self._stroke_cache = []
        self._cache_valid = True
        
        # Subscribe to events
        bus.subscribe('brush_width_changed', self._on_brush_width_changed)
        bus.subscribe('tool_changed', self._on_tool_changed)
        
        logger.info("Enhanced JournalService initialized")

    def _on_brush_width_changed(self, width: int) -> None:
        """Handle dynamic brush width changes."""
        try:
            if isinstance(width, (int, float)) and 1 <= width <= 200:
                old_width = self._current_brush_width
                self._current_brush_width = int(width)
                
                # Update current stroke width if drawing
                if self._is_drawing and self._current_stroke:
                    self._current_stroke.width = self._current_brush_width
                    logger.debug("Dynamic width change during drawing: %d -> %d", 
                               old_width, self._current_brush_width)
                else:
                    logger.debug("Brush width updated: %d", self._current_brush_width)
        except Exception as e:
            logger.error("Error handling brush width change: %s", e)

    def _on_tool_changed(self, tool_name: str) -> None:
        """Handle tool changes."""
        try:
            # End any active preview when tool changes
            if self.preview_helper:
                self.preview_helper.end_tool_preview()
        except Exception as e:
            logger.error("Error handling tool change: %s", e)

    def reset(self) -> None:
        """Clear current page and reset all state."""
        self._page = Page()
        self._current_stroke = None
        self._start_point = None
        self._last_point = None
        self._is_drawing = False
        self._is_drawing_shape = False
        self._shape_start_coord = None
        self._shape_end_coord = None
        self._stroke_cache.clear()
        self._cache_valid = False
        
        # End any active preview
        if self.preview_helper:
            self.preview_helper.end_tool_preview()
            
        logger.info("Enhanced journal reset")

    def start_stroke(self, x: int, y: int, width: int, color: Tuple[int, int, int]) -> None:
        """
        Begin a new stroke with coordinate system and preview integration.
        """
        try:
            mode = self._tool_service.current_tool_mode
            stroke_color = (0, 0, 0) if mode == 'eraser' else color
            
            # Use current brush width for dynamic changes
            actual_width = self._current_brush_width
            self._is_drawing = True
            
            # Convert screen coordinates to world coordinates
            if self.coordinate_manager:
                world_coord = self.coordinate_manager.screen_to_world_coord(x, y)
                self._start_point = Point(world_coord.to_world_float()[0], 
                                        world_coord.to_world_float()[1], 0, actual_width)
            else:
                self._start_point = Point(x, y, 0, actual_width)
            
            self._last_point = self._start_point
            
            # Handle different tool modes
            if mode in _SHAPED_MODES:
                self._start_shape_drawing(mode, world_coord if self.coordinate_manager else (x, y))
            else:
                self._start_simple_drawing(stroke_color, actual_width)
            
            self._cache_valid = False
            
            logger.debug("Started enhanced stroke with width: %d (mode: %s)", actual_width, mode)

        except Exception as e:
            logger.error("Error starting enhanced stroke: %s", e)
            self._is_drawing = False

    def _start_shape_drawing(self, mode: str, start_coord) -> None:
        """Start shape drawing with preview."""
        try:
            self._is_drawing_shape = True
            
            if self.coordinate_manager:
                self._shape_start_coord = start_coord
                self._shape_end_coord = start_coord
            else:
                self._shape_start_coord = start_coord
                self._shape_end_coord = start_coord
            
            # Start shape preview
            if self.preview_helper:
                if self.coordinate_manager:
                    screen_pos = self.coordinate_manager.world_coord_to_screen(start_coord)
                else:
                    screen_pos = start_coord
                    
                preview_style = PreviewStyle(
                    color=(128, 128, 255),  # Light blue instead of gray
                    width=max(2, self._current_brush_width),
                    alpha=128
                )
                
                self.preview_helper.start_tool_preview(mode, screen_pos[0], screen_pos[1], 
                                                     preview_style.width, preview_style.color)
                
        except Exception as e:
            logger.error("Error starting shape drawing: %s", e)

    def _start_simple_drawing(self, stroke_color: Tuple[int, int, int], actual_width: int) -> None:
        """Start simple brush/eraser drawing."""
        try:
            # Create stroke
            self._current_stroke = self._page.new_stroke(stroke_color, actual_width)
            
            # Add initial point
            self._current_stroke.add_point(self._start_point)
            
            logger.debug("Added initial point with dynamic width: %d", actual_width)
            
        except Exception as e:
            logger.error("Error starting simple drawing: %s", e)

    def add_point(self, x: int, y: int, width: int) -> None:
        """
        Add a point with enhanced coordinate handling and preview updates.
        """
        if not self._is_drawing:
            return

        try:
            # Use current brush width for dynamic changes
            current_width = self._current_brush_width
            current_time = time.time()
            
            # Convert to world coordinates
            if self.coordinate_manager:
                world_coord = self.coordinate_manager.screen_to_world_coord(x, y)
                world_pos = world_coord.to_world_float()
                point = Point(world_pos[0], world_pos[1], 0, current_width)
                screen_pos = (x, y)
            else:
                point = Point(x, y, 0, current_width)
                screen_pos = (x, y)
            
            if self._is_drawing_shape:
                # Update shape preview
                self._update_shape_preview(world_coord if self.coordinate_manager else (x, y), screen_pos)
            else:
                # Add point to current stroke
                self._add_point_to_stroke(point, current_time)
                
        except Exception as e:
            logger.error("Error adding enhanced point: %s", e)

    def _update_shape_preview(self, world_coord, screen_pos: Tuple[int, int]) -> None:
        """Update shape preview."""
        try:
            if self.coordinate_manager:
                self._shape_end_coord = world_coord
            else:
                self._shape_end_coord = world_coord
                
            # Update preview
            if self.preview_helper:
                self.preview_helper.update_tool_preview(screen_pos[0], screen_pos[1])
                
        except Exception as e:
            logger.error("Error updating shape preview: %s", e)

    def _add_point_to_stroke(self, point: Point, current_time: float) -> None:
        """Add point to current stroke with dynamic width."""
        try:
            if not self._current_stroke:
                return
                
            self._current_stroke.add_point(point)
            self._last_point = point
            
            # Update stroke's default width for consistency
            self._current_stroke.width = self._current_brush_width
            
            # Throttle event publishing for performance
            if current_time - self._last_event_time > self._event_throttle_interval:
                self._bus.publish('stroke_added')
                self._last_event_time = current_time
                
        except Exception as e:
            logger.error("Error adding point to stroke: %s", e)

    def end_stroke(self) -> None:
        """
        Finalize stroke with enhanced shape generation and preview cleanup.
        """
        if not self._is_drawing:
            return

        try:
            mode = self._tool_service.current_tool_mode
            
            if self._is_drawing_shape and self._shape_start_coord and self._shape_end_coord:
                self._finalize_shape(mode)
            
            # End preview
            if self.preview_helper:
                self.preview_helper.end_tool_preview()
            
            self._cache_valid = False
            self._bus.publish('stroke_added')
            
            logger.debug("Enhanced stroke completed with final width: %d", self._current_brush_width)
            
        except Exception as e:
            logger.error('Failed to end enhanced stroke: %s', e)
        finally:
            # Clean up all state
            self._is_drawing = False
            self._is_drawing_shape = False
            self._current_stroke = None
            self._start_point = None
            self._last_point = None
            self._shape_start_coord = None
            self._shape_end_coord = None

    def _finalize_shape(self, mode: str) -> None:
        """Finalize shape with mathematical accuracy."""
        try:
            # Get coordinates
            if self.coordinate_manager:
                start_world = self._shape_start_coord.to_world_float()
                end_world = self._shape_end_coord.to_world_float()
            else:
                start_world = self._shape_start_coord
                end_world = self._shape_end_coord
            
            # Generate shape points
            shape_points = self._generate_enhanced_shape(mode, start_world, end_world)
            
            # Create stroke
            stroke_color = (255, 255, 255)  # Default white for shapes
            self._current_stroke = self._page.new_stroke(stroke_color, self._current_brush_width)
            self._current_stroke.points = shape_points
            
            logger.debug("Finalized enhanced shape %s with %d points", mode, len(shape_points))
            
        except Exception as e:
            logger.error("Error finalizing enhanced shape: %s", e)

    def _generate_enhanced_shape(self, mode: str, start: Tuple[float, float], 
                               end: Tuple[float, float]) -> List[Point]:
        """Generate shape with enhanced mathematical accuracy."""
        try:
            if mode == 'line':
                return self._generate_line_points(start, end)
            elif mode == 'rect':
                return self._generate_rectangle_points(start, end)
            elif mode == 'circle':
                return self._generate_circle_points(start, end)
            elif mode == 'triangle':
                return self._generate_triangle_points(start, end)
            elif mode == 'parabola':
                return self._generate_parabola_points(start, end)
            else:
                # Fallback to line
                return self._generate_line_points(start, end)
                
        except Exception as e:
            logger.error("Error generating enhanced shape %s: %s", mode, e)
            return [Point(start[0], start[1], 0, self._current_brush_width),
                   Point(end[0], end[1], 0, self._current_brush_width)]

    def _generate_line_points(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Point]:
        """Generate line points."""
        try:
            # Simple interpolation for line
            steps = max(2, int(math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2) / 2))
            points = []
            
            for i in range(steps + 1):
                t = i / steps
                x = start[0] + t * (end[0] - start[0])
                y = start[1] + t * (end[1] - start[1])
                points.append(Point(x, y, 0, self._current_brush_width))
                
            return points
            
        except Exception as e:
            logger.error("Error generating line points: %s", e)
            return []

    def _generate_rectangle_points(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Point]:
        """Generate rectangle outline points."""
        try:
            x1, y1 = start
            x2, y2 = end
            
            # Ensure proper ordering
            min_x, max_x = min(x1, x2), max(x1, x2)
            min_y, max_y = min(y1, y2), max(y1, y2)
            
            points = []
            
            # Top edge
            points.extend(self._generate_line_points((min_x, min_y), (max_x, min_y)))
            # Right edge
            points.extend(self._generate_line_points((max_x, min_y), (max_x, max_y)))
            # Bottom edge
            points.extend(self._generate_line_points((max_x, max_y), (min_x, max_y)))
            # Left edge
            points.extend(self._generate_line_points((min_x, max_y), (min_x, min_y)))
            
            return points
            
        except Exception as e:
            logger.error("Error generating rectangle points: %s", e)
            return []

    def _generate_circle_points(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Point]:
        """Generate circle points."""
        try:
            center_x = (start[0] + end[0]) / 2
            center_y = (start[1] + end[1]) / 2
            radius = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2) / 2
            
            if self.curve_framework:
                raw_points = self.curve_framework.create_circle_from_bounds((center_x, center_y), radius)
                return [Point(x, y, 0, self._current_brush_width) for x, y in raw_points]
            else:
                # Fallback circle generation
                points = []
                num_points = max(12, int(radius * 0.5))
                
                for i in range(num_points + 1):
                    angle = 2 * math.pi * i / num_points
                    x = center_x + radius * math.cos(angle)
                    y = center_y + radius * math.sin(angle)
                    points.append(Point(x, y, 0, self._current_brush_width))
                    
                return points
                
        except Exception as e:
            logger.error("Error generating circle points: %s", e)
            return []

    def _generate_triangle_points(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Point]:
        """Generate triangle points."""
        try:
            x1, y1 = start
            x2, y2 = end
            x3, y3 = x2, y1  # Right angle triangle
            
            points = []
            points.extend(self._generate_line_points((x1, y1), (x2, y2)))
            points.extend(self._generate_line_points((x2, y2), (x3, y3)))
            points.extend(self._generate_line_points((x3, y3), (x1, y1)))
            
            return points
            
        except Exception as e:
            logger.error("Error generating triangle points: %s", e)
            return []

    def _generate_parabola_points(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Point]:
        """Generate mathematically accurate parabola points."""
        try:
            if self.curve_framework:
                # Use enhanced mathematical framework
                raw_points = self.curve_framework.fit_parabola_to_points(start, end, curvature=1.0, resolution=50)
                return [Point(x, y, 0, self._current_brush_width) for x, y in raw_points]
            else:
                # Fallback parabola generation
                logger.warning("Curve framework not available, using basic parabola")
                return self._generate_basic_parabola(start, end)
                
        except Exception as e:
            logger.error("Error generating parabola points: %s", e)
            return []

    def _generate_basic_parabola(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Point]:
        """Basic parabola generation as fallback."""
        try:
            x1, y1 = start
            x2, y2 = end
            
            if abs(x2 - x1) < 1:
                # Vertical line fallback
                return self._generate_line_points(start, end)
            
            # Calculate vertex
            h = (x1 + x2) / 2
            k = min(y1, y2) - abs(x2 - x1) / 4
            
            # Calculate coefficient
            if abs(x1 - h) > 0.01:
                a = (y1 - k) / ((x1 - h) ** 2)
            else:
                a = 1.0
            
            # Generate points
            points = []
            steps = 30
            
            for i in range(steps + 1):
                t = i / steps
                x = x1 + t * (x2 - x1)
                y = a * (x - h) ** 2 + k
                points.append(Point(x, y, 0, self._current_brush_width))
                
            return points
            
        except Exception as e:
            logger.error("Error in basic parabola generation: %s", e)
            return []

    def render(self, renderer: Any) -> None:
        """
        Enhanced rendering with layer awareness.
        """
        if not self._page:
            return
            
        try:
            # Check if renderer supports layered rendering
            if hasattr(renderer, 'draw_stroke_enhanced'):
                self._render_strokes_enhanced(renderer)
            else:
                self._render_strokes_legacy(renderer)
                
        except Exception as e:
            logger.error("Error in enhanced rendering: %s", e)

    def _render_strokes_enhanced(self, renderer: Any) -> None:
        """Render strokes using enhanced renderer."""
        try:
            for stroke in self._page.strokes:
                if not stroke.points:
                    continue
                    
                # Convert world coordinates to screen if needed
                if self.coordinate_manager:
                    screen_points = []
                    for point in stroke.points:
                        world_coord = WorldCoordinate.from_world(point.x, point.y)
                        screen_pos = self.coordinate_manager.world_coord_to_screen(world_coord)
                        screen_points.append((screen_pos[0], screen_pos[1], point.width))
                else:
                    screen_points = [(p.x, p.y, p.width) for p in stroke.points]
                
                # Use enhanced stroke rendering
                renderer.draw_stroke_enhanced(screen_points, stroke.color, stroke.width)
                
        except Exception as e:
            logger.error("Error in enhanced stroke rendering: %s", e)

    def _render_strokes_legacy(self, renderer: Any) -> None:
        """Render strokes using legacy renderer."""
        try:
            for stroke in self._page.strokes:
                if not stroke.points:
                    continue
                    
                # Convert to simple points
                points = [(p.x, p.y) for p in stroke.points]
                
                if hasattr(renderer, 'draw_stroke'):
                    renderer.draw_stroke(points, stroke.color, stroke.width)
                    
        except Exception as e:
            logger.error("Error in legacy stroke rendering: %s", e)

    def invalidate_cache(self) -> None:
        """Force cache invalidation for next render."""
        self._cache_valid = False

    def get_stroke_count(self) -> int:
        """Get the number of strokes in the current page."""
        return len(self._page.strokes) if self._page else 0

    def is_drawing(self) -> bool:
        """Check if currently drawing."""
        return self._is_drawing

    def get_coordinate_bounds(self) -> Optional[Tuple[float, float, float, float]]:
        """Get coordinate bounds of all strokes."""
        try:
            if not self._page.strokes:
                return None
                
            all_x = []
            all_y = []
            
            for stroke in self._page.strokes:
                for point in stroke.points:
                    all_x.append(point.x)
                    all_y.append(point.y)
                    
            if not all_x:
                return None
                
            return (min(all_x), min(all_y), max(all_x), max(all_y))
            
        except Exception as e:
            logger.error("Error getting coordinate bounds: %s", e)
            return None

    def get_system_stats(self) -> dict:
        """Get statistics about integrated systems."""
        try:
            stats = {
                'stroke_count': self.get_stroke_count(),
                'is_drawing': self.is_drawing(),
                'current_brush_width': self._current_brush_width,
                'coordinate_system_available': self.coordinate_manager is not None,
                'preview_system_available': self.preview_system is not None,
                'curve_framework_available': self.curve_framework is not None
            }
            
            if self.coordinate_manager:
                stats['coordinate_info'] = self.coordinate_manager.get_system_info()
                
            if self.preview_system:
                stats['preview_info'] = self.preview_system.get_preview_info()
                
            return stats
            
        except Exception as e:
            logger.error("Error getting system stats: %s", e)
            return {}


# Legacy compatibility wrapper
class JournalService(EnhancedJournalService):
    """Legacy compatibility wrapper for JournalService."""
    
    def __init__(self, bus: EventBus, tool_service: ToolService, database: CanvasDatabase) -> None:
        """Initialize with legacy interface."""
        super().__init__(bus, tool_service, database)
        logger.info("Legacy JournalService wrapper initialized")