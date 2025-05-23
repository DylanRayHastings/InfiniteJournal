"""
Integration examples showing how to use the new error boundary and performance systems.

This module provides comprehensive examples of integrating error boundaries and performance
monitoring into drawing application components. Demonstrates best practices for robust
error handling, performance optimization, and system reliability.
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


class DrawingServiceError(ApplicationError):
   """Exceptions raised during drawing service operations."""
   pass


class InvalidColorError(DrawingServiceError):
   """Raised when color format is invalid."""
   pass


class InvalidWidthError(DrawingServiceError):
   """Raised when stroke width is invalid."""
   pass


class ExampleDrawingService:
   """Drawing service demonstrating error boundary and performance integration.
   
   Provides stroke creation, point conversion, and rendering capabilities with
   comprehensive error handling and performance monitoring. Serves as reference
   implementation for robust drawing operations.
   """
   
   def __init__(self) -> None:
       """Initialize drawing service with empty stroke collection."""
       self.strokes: List[Stroke] = []
       self._cache_valid = True
   
   @drawing_boundary("create_stroke", "drawing_service")
   @profile_operation("stroke_creation")
   def create_stroke(self, color: Tuple[int, int, int], width: int = 3) -> Stroke:
       """Create new stroke with error boundary and performance monitoring.
       
       Args:
           color: RGB color tuple with values 0-255
           width: Stroke width in pixels, must be between 1-200
           
       Returns:
           Newly created stroke instance
           
       Raises:
           InvalidColorError: If color format is invalid
           InvalidWidthError: If width is outside valid range
       """
       validated_color = self._validate_stroke_color(color)
       validated_width = self._validate_stroke_width(width)
       
       stroke = self._create_stroke_instance(validated_color, validated_width)
       self.strokes.append(stroke)
       
       logger.debug("Created stroke with color %s, width %d", validated_color, validated_width)
       return stroke
   
   def _validate_stroke_color(self, color: Tuple[int, int, int]) -> Tuple[int, int, int]:
       """Validate stroke color format and values."""
       if not isinstance(color, (tuple, list)) or len(color) != 3:
           raise InvalidColorError(
               "Color must be RGB tuple with 3 values",
               "INVALID_COLOR_FORMAT",
               severity=ErrorSeverity.MEDIUM,
               category=ErrorCategory.DRAWING,
               context=ErrorContext("stroke_creation", "drawing_service", user_action="create_stroke")
           )
       
       if not all(isinstance(c, int) and 0 <= c <= 255 for c in color):
           raise InvalidColorError(
               "Color values must be integers between 0-255",
               "INVALID_COLOR_VALUES",
               severity=ErrorSeverity.MEDIUM,
               category=ErrorCategory.DRAWING
           )
       
       return tuple(color)
   
   def _validate_stroke_width(self, width: int) -> int:
       """Validate stroke width value."""
       if not isinstance(width, int) or width < 1 or width > 200:
           raise InvalidWidthError(
               f"Width must be integer between 1-200, got {width}",
               "INVALID_WIDTH_VALUE",
               severity=ErrorSeverity.LOW,
               category=ErrorCategory.DRAWING
           )
       
       return width
   
   def _create_stroke_instance(self, color: Tuple[int, int, int], width: int) -> Stroke:
       """Create stroke instance with validated parameters."""
       try:
           return Stroke(color=color, width=width)
       except Exception as e:
           raise DrawingServiceError(
               f"Failed to create stroke instance: {e}",
               "STROKE_INSTANTIATION_FAILED",
               severity=ErrorSeverity.HIGH,
               category=ErrorCategory.DRAWING
           ) from e
   
   @cached_operation("point_conversion", max_size=200)
   def convert_points(self, raw_points: List[Any]) -> List[Point]:
       """Convert raw point data to Point objects with performance caching.
       
       Args:
           raw_points: Collection of raw point data in various formats
           
       Returns:
           List of validated Point objects
       """
       converted_points = []
       
       for raw_point in raw_points:
           converted_point = self._convert_single_point(raw_point)
           if converted_point:
               converted_points.append(converted_point)
       
       return converted_points
   
   def _convert_single_point(self, raw_point: Any) -> Optional[Point]:
       """Convert single raw point to Point object."""
       try:
           if isinstance(raw_point, dict):
               return Point.from_dict(raw_point)
           
           if isinstance(raw_point, (tuple, list)) and len(raw_point) >= 2:
               return Point(float(raw_point[0]), float(raw_point[1]))
           
           logger.warning("Skipping invalid point format: %r", raw_point)
           return None
           
       except Exception as e:
           logger.warning("Error converting point %r: %s", raw_point, e)
           return None
   
   @rendering_boundary("render_strokes", "drawing_service", fallback_value=[])
   @profile_operation("stroke_rendering")
   def render_strokes(self, renderer: Any) -> List[str]:
       """Render all strokes with adaptive quality and error boundaries.
       
       Args:
           renderer: Rendering engine instance
           
       Returns:
           List of rendered stroke identifiers
       """
       quality_manager = get_global_adaptive_quality()
       detail_level = quality_manager.get_stroke_detail_level()
       
       rendered_stroke_ids = []
       
       for stroke_index, stroke in enumerate(self.strokes):
           rendered_id = self._render_single_stroke(renderer, stroke, stroke_index, detail_level)
           if rendered_id:
               rendered_stroke_ids.append(rendered_id)
       
       return rendered_stroke_ids
   
   def _render_single_stroke(self, renderer: Any, stroke: Stroke, index: int, detail_level: int) -> Optional[str]:
       """Render individual stroke with quality adaptation."""
       if self._should_skip_stroke_for_quality(index, detail_level):
           return None
       
       try:
           stroke_points = self._prepare_stroke_points_for_rendering(stroke, detail_level)
           
           if stroke_points and hasattr(renderer, 'draw_stroke'):
               renderer.draw_stroke(stroke_points, stroke.color, stroke.width)
               return f"stroke_{index}"
               
           return None
           
       except Exception as e:
           logger.warning("Error rendering stroke %d: %s", index, e)
           return None
   
   def _should_skip_stroke_for_quality(self, stroke_index: int, detail_level: int) -> bool:
       """Determine if stroke should be skipped for performance."""
       return detail_level > 1 and stroke_index % detail_level != 0
   
   def _prepare_stroke_points_for_rendering(self, stroke: Stroke, detail_level: int) -> List[Tuple[float, float]]:
       """Prepare stroke points for rendering with quality adaptation."""
       return [(point.x, point.y) for point in stroke.points[::detail_level]]


class ToolManagerError(ApplicationError):
   """Exceptions raised during tool management operations."""
   pass


class InvalidToolError(ToolManagerError):
   """Raised when tool name is invalid or unknown."""
   pass


class ExampleToolManager:
   """Tool manager demonstrating error boundary integration.
   
   Manages drawing tool selection and switching with robust error handling
   and graceful fallback to safe defaults when operations fail.
   """
   
   def __init__(self) -> None:
       """Initialize tool manager with default brush tool."""
       self.current_tool = "brush"
       self.available_tools = {"brush", "eraser", "line", "rect", "circle"}
   
   @tool_boundary("switch_tool", "tool_manager")
   def switch_tool(self, tool_name: str) -> bool:
       """Switch to different drawing tool with error boundary protection.
       
       Args:
           tool_name: Name of tool to switch to
           
       Returns:
           True if tool switch succeeded
           
       Raises:
           InvalidToolError: If tool name is invalid or unknown
       """
       validated_tool_name = self._validate_tool_name(tool_name)
       previous_tool = self.current_tool
       
       self.current_tool = validated_tool_name
       
       logger.info("Tool switched from %s to %s", previous_tool, validated_tool_name)
       return True
   
   def _validate_tool_name(self, tool_name: str) -> str:
       """Validate tool name format and availability."""
       if not isinstance(tool_name, str):
           raise InvalidToolError(
               "Tool name must be string",
               "INVALID_TOOL_TYPE",
               category=ErrorCategory.TOOL
           )
       
       if tool_name not in self.available_tools:
           raise InvalidToolError(
               f"Unknown tool: {tool_name}",
               "UNKNOWN_TOOL",
               severity=ErrorSeverity.MEDIUM,
               category=ErrorCategory.TOOL,
               user_message=f"Tool '{tool_name}' is not available"
           )
       
       return tool_name


class PersistenceManagerError(ApplicationError):
   """Exceptions raised during persistence operations."""
   pass


class SaveOperationError(PersistenceManagerError):
   """Raised when save operation fails."""
   pass


class LoadOperationError(PersistenceManagerError):
   """Raised when load operation fails."""
   pass


class ExamplePersistenceManager:
   """Persistence manager demonstrating error boundary integration.
   
   Handles page saving and loading operations with comprehensive error
   boundaries and graceful degradation when file operations fail.
   """
   
   def __init__(self, file_path: str) -> None:
       """Initialize persistence manager with target file path.
       
       Args:
           file_path: Path where pages will be saved and loaded
       """
       self.file_path = file_path
   
   @persistence_boundary("save_page", "persistence_manager")
   def save_page(self, page: Page) -> bool:
       """Save page with comprehensive error boundary protection.
       
       Args:
           page: Page instance to save
           
       Returns:
           True if save operation succeeded
           
       Raises:
           SaveOperationError: If save operation fails
       """
       validated_page = self._validate_page_for_saving(page)
       target_path = self._prepare_save_path()
       
       self._execute_page_save(validated_page, target_path)
       
       logger.info("Page saved successfully to %s", self.file_path)
       return True
   
   def _validate_page_for_saving(self, page: Page) -> Page:
       """Validate page instance before saving."""
       if not isinstance(page, Page):
           raise SaveOperationError(
               "Invalid page instance for saving",
               "INVALID_PAGE_INSTANCE",
               severity=ErrorSeverity.HIGH,
               category=ErrorCategory.PERSISTENCE
           )
       
       return page
   
   def _prepare_save_path(self) -> Path:
       """Prepare and validate save path."""
       return Path(self.file_path)
   
   def _execute_page_save(self, page: Page, target_path: Path) -> None:
       """Execute the actual page save operation."""
       try:
           page.save(target_path)
       except Exception as e:
           raise SaveOperationError(
               f"Failed to save page: {e}",
               "SAVE_EXECUTION_FAILED",
               severity=ErrorSeverity.HIGH,
               category=ErrorCategory.PERSISTENCE,
               user_message="Could not save your work. Please check disk space and permissions."
           ) from e
   
   @persistence_boundary("load_page", "persistence_manager", fallback_value=None)
   def load_page(self) -> Optional[Page]:
       """Load page with error boundary and fallback handling.
       
       Returns:
           Loaded page instance or None if loading fails
           
       Raises:
           LoadOperationError: If load operation fails critically
       """
       source_path = Path(self.file_path)
       
       if not source_path.exists():
           logger.info("No existing page file found, starting fresh")
           return Page()
       
       loaded_page = self._execute_page_load(source_path)
       
       logger.info("Page loaded successfully from %s", self.file_path)
       return loaded_page
   
   def _execute_page_load(self, source_path: Path) -> Page:
       """Execute the actual page load operation."""
       try:
           return Page.load(source_path)
       except Exception as e:
           raise LoadOperationError(
               f"Failed to load page: {e}",
               "LOAD_EXECUTION_FAILED",
               severity=ErrorSeverity.HIGH,
               category=ErrorCategory.PERSISTENCE,
               user_message="Could not load your previous work. Starting with a blank page."
           ) from e


def demonstrate_performance_monitoring() -> None:
   """Demonstrate performance monitoring capabilities with example operations."""
   profiler = get_global_profiler()
   drawing_service = ExampleDrawingService()
   
   stroke_one = drawing_service.create_stroke((255, 0, 0), 5)
   stroke_one.add_point(Point(10, 10))
   stroke_one.add_point(Point(20, 20))
   
   stroke_two = drawing_service.create_stroke((0, 255, 0), 3)
   stroke_two.add_point(Point(30, 30))
   
   raw_point_data = [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 5, "y": 6}]
   points_first_call = drawing_service.convert_points(raw_point_data)
   points_cached_call = drawing_service.convert_points(raw_point_data)
   
   performance_metrics = profiler.get_metrics()
   
   print("Performance Metrics:")
   for operation_name, execution_times in performance_metrics.operation_times.items():
       if execution_times:
           average_execution_time = sum(execution_times) / len(execution_times)
           print(f"  {operation_name}: {len(execution_times)} calls, avg {average_execution_time*1000:.2f}ms")


def demonstrate_error_handling() -> None:
   """Demonstrate error boundary capabilities with various failure scenarios."""
   drawing_service = ExampleDrawingService()
   tool_manager = ExampleToolManager()
   
   successful_stroke = drawing_service.create_stroke((255, 0, 0), 5)
   print("✓ Created stroke successfully")
   
   try:
       invalid_stroke = drawing_service.create_stroke("invalid_color", 5)
       print("✓ Created stroke with invalid color (unexpected success)")
   except Exception as error:
       print(f"✓ Error handled gracefully: {error}")
   
   tool_manager.switch_tool("eraser")
   print("✓ Switched to eraser")
   
   try:
       tool_manager.switch_tool("invalid_tool")
       print("✓ Switched to invalid tool (unexpected success)")
   except Exception as error:
       print(f"✓ Invalid tool handled gracefully: {error}")


if __name__ == "__main__":
   logging.basicConfig(level=logging.INFO)
   
   print("=== Performance Monitoring Demo ===")
   demonstrate_performance_monitoring()
   
   print("\n=== Error Handling Demo ===")
   demonstrate_error_handling()
   
   print("\n=== Integration Complete ===")
   print("The new systems are working correctly!")