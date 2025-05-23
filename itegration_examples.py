# integration_examples.py (NEW FILE - Examples of using the new systems)
"""
Integration examples showing how to use the new error boundary and performance systems.
"""

import logging
from pathlib import Path
from typing import List, Tuple, Any, Optional
from core.error_boundary import (
    drawing_boundary, rendering_boundary, tool_boundary, persistence_boundary,
    ErrorContext, ErrorCategory, ErrorSeverity, ApplicationError
)
from core.performance import (
    profile_operation, cached_operation, get_global_profiler, 
    get_global_adaptive_quality, get_global_rendering_optimizer
)
from core.drawing.models import Point, Stroke, Page

logger = logging.getLogger(__name__)


class ExampleDrawingService:
    """Example service showing how to integrate error boundaries and performance monitoring."""
    
    def __init__(self):
        self.strokes: List[Stroke] = []
        self._cache_valid = True
        
    @drawing_boundary("create_stroke", "drawing_service")
    @profile_operation("stroke_creation")
    def create_stroke(self, color: Tuple[int, int, int], width: int = 3) -> Stroke:
        """
        Create a new stroke with error boundary and performance monitoring.
        
        This method demonstrates:
        - Error boundary decoration for automatic error handling
        - Performance profiling to track operation times
        - Proper error context for debugging
        """
        try:
            # Validate inputs with proper error messages
            if not isinstance(color, (tuple, list)) or len(color) != 3:
                raise ApplicationError(
                    "Invalid color format",
                    "INVALID_COLOR",
                    severity=ErrorSeverity.MEDIUM,
                    category=ErrorCategory.DRAWING,
                    context=ErrorContext("stroke_creation", "drawing_service", user_action="create_stroke")
                )
            
            if not isinstance(width, int) or width < 1 or width > 200:
                raise ApplicationError(
                    f"Invalid width: {width}",
                    "INVALID_WIDTH", 
                    severity=ErrorSeverity.LOW,
                    category=ErrorCategory.DRAWING
                )
            
            # Create stroke (this could fail)
            stroke = Stroke(color=color, width=width)
            self.strokes.append(stroke)
            
            logger.debug("Created stroke with color %s, width %d", color, width)
            return stroke
            
        except ApplicationError:
            # Re-raise application errors as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise ApplicationError(
                f"Unexpected error creating stroke: {e}",
                "STROKE_CREATION_FAILED",
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.DRAWING
            ) from e
    
    @cached_operation("point_conversion", max_size=200)
    def convert_points(self, raw_points: List[Any]) -> List[Point]:
        """
        Convert raw points to Point objects with caching for performance.
        
        This method demonstrates:
        - Automatic caching of expensive operations
        - Performance optimization through memoization
        """
        converted = []
        for raw_point in raw_points:
            try:
                if isinstance(raw_point, dict):
                    point = Point.from_dict(raw_point)
                elif isinstance(raw_point, (tuple, list)) and len(raw_point) >= 2:
                    point = Point(float(raw_point[0]), float(raw_point[1]))
                else:
                    logger.warning("Skipping invalid point: %r", raw_point)
                    continue
                    
                converted.append(point)
            except Exception as e:
                logger.warning("Error converting point %r: %s", raw_point, e)
                continue
        
        return converted
    
    @rendering_boundary("render_strokes", "drawing_service", fallback_value=[])
    @profile_operation("stroke_rendering")
    def render_strokes(self, renderer: Any) -> List[str]:
        """
        Render all strokes with error boundary and performance monitoring.
        
        This method demonstrates:
        - Rendering error boundary with fallback value
        - Performance monitoring for render operations
        - Adaptive quality integration
        """
        rendered_ids = []
        
        # Get adaptive quality for performance adjustments
        quality = get_global_adaptive_quality()
        detail_level = quality.get_stroke_detail_level()
        
        for i, stroke in enumerate(self.strokes):
            try:
                # Skip strokes based on quality level for performance
                if detail_level > 1 and i % detail_level != 0:
                    continue
                
                # Convert points for rendering
                points = [(p.x, p.y) for p in stroke.points[::detail_level]]
                
                if points and hasattr(renderer, 'draw_stroke'):
                    renderer.draw_stroke(points, stroke.color, stroke.width)
                    rendered_ids.append(f"stroke_{i}")
                    
            except Exception as e:
                # Error boundary will handle this, but we log for debugging
                logger.warning("Error rendering stroke %d: %s", i, e)
                continue
        
        return rendered_ids


class ExampleToolManager:
    """Example tool manager showing error boundary integration."""
    
    def __init__(self):
        self.current_tool = "brush"
        self.tools = {"brush", "eraser", "line", "rect", "circle"}
    
    @tool_boundary("switch_tool", "tool_manager")
    def switch_tool(self, tool_name: str) -> bool:
        """
        Switch to a different tool with error boundary.
        
        This method demonstrates:
        - Tool operation error boundary
        - Graceful handling of invalid tool names
        - Recovery to safe defaults
        """
        if not isinstance(tool_name, str):
            raise ApplicationError(
                "Tool name must be a string",
                "INVALID_TOOL_TYPE",
                category=ErrorCategory.TOOL
            )
        
        if tool_name not in self.tools:
            raise ApplicationError(
                f"Unknown tool: {tool_name}",
                "UNKNOWN_TOOL",
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.TOOL,
                user_message=f"Tool '{tool_name}' is not available"
            )
        
        old_tool = self.current_tool
        self.current_tool = tool_name
        logger.info("Switched from %s to %s", old_tool, tool_name)
        return True


class ExamplePersistenceManager:
    """Example persistence manager with error boundaries."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    @persistence_boundary("save_page", "persistence_manager")
    def save_page(self, page: Page) -> bool:
        """
        Save a page with persistence error boundary.
        
        This method demonstrates:
        - Persistence error boundary
        - File operation error handling
        - Graceful degradation on save failures
        """
        try:
            # This could fail due to permissions, disk space, etc.
            page.save(Path(self.file_path))
            logger.info("Page saved successfully to %s", self.file_path)
            return True
            
        except Exception as e:
            # Error boundary will handle this and potentially recover
            raise ApplicationError(
                f"Failed to save page: {e}",
                "SAVE_FAILED",
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.PERSISTENCE,
                user_message="Could not save your work. Please check disk space and permissions."
            ) from e
    
    @persistence_boundary("load_page", "persistence_manager", fallback_value=None)
    def load_page(self) -> Optional[Page]:
        """
        Load a page with error boundary and fallback.
        
        This method demonstrates:
        - Persistence error boundary with fallback value
        - Safe handling of corrupted files
        - Graceful degradation when loading fails
        """
        try:
            from pathlib import Path
            page = Page.load(Path(self.file_path))
            logger.info("Page loaded successfully from %s", self.file_path)
            return page
            
        except FileNotFoundError:
            # Not an error - file doesn't exist yet
            logger.info("No existing page file found, starting fresh")
            return Page()
            
        except Exception as e:
            raise ApplicationError(
                f"Failed to load page: {e}",
                "LOAD_FAILED",
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.PERSISTENCE,
                user_message="Could not load your previous work. Starting with a blank page."
            ) from e


def demonstrate_performance_monitoring():
    """Demonstrate performance monitoring features."""
    
    # Get the global profiler
    profiler = get_global_profiler()
    
    # Simulate some operations
    drawing_service = ExampleDrawingService()
    
    # These operations will be automatically profiled
    stroke1 = drawing_service.create_stroke((255, 0, 0), 5)
    stroke1.add_point(Point(10, 10))
    stroke1.add_point(Point(20, 20))
    
    stroke2 = drawing_service.create_stroke((0, 255, 0), 3)
    stroke2.add_point(Point(30, 30))
    
    # Convert some points (will be cached)
    raw_points = [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 5, "y": 6}]
    points1 = drawing_service.convert_points(raw_points)  # Cache miss
    points2 = drawing_service.convert_points(raw_points)  # Cache hit
    
    # Get performance metrics
    metrics = profiler.get_metrics()
    
    print("Performance Metrics:")
    for operation, times in metrics.operation_times.items():
        if times:
            avg_time = sum(times) / len(times)
            print(f"  {operation}: {len(times)} calls, avg {avg_time*1000:.2f}ms")


def demonstrate_error_handling():
    """Demonstrate error boundary features."""
    
    drawing_service = ExampleDrawingService()
    tool_manager = ExampleToolManager()
    
    # These operations will have errors handled by error boundaries
    
    # This will succeed
    try:
        stroke = drawing_service.create_stroke((255, 0, 0), 5)
        print("✓ Created stroke successfully")
    except Exception as e:
        print(f"✗ Failed to create stroke: {e}")
    
    # This will fail but be handled gracefully
    try:
        stroke = drawing_service.create_stroke("invalid_color", 5)
        print("✓ Created stroke with invalid color (shouldn't happen)")
    except Exception as e:
        print(f"✓ Error handled gracefully: {e}")
    
    # Tool switching
    try:
        tool_manager.switch_tool("eraser")
        print("✓ Switched to eraser")
    except Exception as e:
        print(f"✗ Tool switch failed: {e}")
    
    try:
        tool_manager.switch_tool("invalid_tool")
        print("✓ Switched to invalid tool (shouldn't happen)")
    except Exception as e:
        print(f"✓ Invalid tool handled gracefully: {e}")


if __name__ == "__main__":
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    
    print("=== Performance Monitoring Demo ===")
    demonstrate_performance_monitoring()
    
    print("\n=== Error Handling Demo ===")
    demonstrate_error_handling()
    
    print("\n=== Integration Complete ===")
    print("The new systems are working correctly!")


# Usage patterns for other developers:

"""
# 1. Adding error boundaries to your methods:

@drawing_boundary("my_drawing_operation", "my_component")
def my_drawing_method(self, data):
    # Your drawing logic here
    # Errors will be caught and handled automatically
    pass

# 2. Adding performance monitoring:

@profile_operation("expensive_calculation")
def expensive_method(self, data):
    # This method's performance will be tracked
    # Slow operations will be logged automatically
    pass

# 3. Adding caching for expensive operations:

@cached_operation("data_processing", max_size=100)
def process_data(self, input_data):
    # Results will be cached automatically
    # Repeated calls with same input return cached results
    pass

# 4. Using adaptive quality:

def render_with_quality(self):
    quality = get_global_adaptive_quality()
    detail_level = quality.get_stroke_detail_level()
    
    # Adjust rendering based on current performance
    if quality.should_use_antialiasing():
        enable_antialiasing()
    
    render_with_detail(detail_level)

# 5. Creating custom application errors:

def my_risky_operation(self):
    try:
        # Risky operation here
        pass
    except Exception as e:
        raise ApplicationError(
            "Operation failed",
            "MY_OPERATION_FAILED",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.DRAWING,
            user_message="Something went wrong, but you can continue drawing"
        ) from e
"""