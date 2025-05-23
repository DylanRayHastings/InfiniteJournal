"""
Production-ready drawing application framework with integrated error boundaries and performance monitoring.

This module provides a complete foundation for building drawing applications with enterprise-level
error handling, performance optimization, and team development readiness. Every component follows
strict production standards with clear expansion points for team collaboration.

Quick Start:
    factory = DrawingApplicationFactory()
    app = factory.create_production_application()
    
    service = app.get_drawing_service()
    stroke = service.create_stroke_safely((255, 0, 0), 3)
    
Extension Points:
    - Add stroke types: Extend StrokeType enum and StrokeFactory
    - Add validation rules: Create new validate_* functions
    - Add drawing tools: Implement ToolProvider interface
    - Add storage backends: Implement DrawingRepository interface
    - Add rendering engines: Implement RenderingEngine interface
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Tuple, Any, Union, Iterator
from functools import wraps
import time
import uuid
import weakref


logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for monitoring and alerting."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification and handling."""
    DRAWING = "drawing"
    TOOL = "tool" 
    PERSISTENCE = "persistence"
    RENDERING = "rendering"
    VALIDATION = "validation"
    SYSTEM = "system"


class ApplicationError(Exception):
    """Base application error with structured context information."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.category = category
        self.user_message = user_message or message
        self.context = context or {}
        self.timestamp = datetime.now(timezone.utc)


@dataclass(frozen=True)
class Point:
    """Immutable point representation for drawing operations."""
    x: float
    y: float
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Point':
        """Create point from dictionary data."""
        return cls(
            x=float(data['x']),
            y=float(data['y'])
        )
    
    def to_dict(self) -> Dict[str, float]:
        """Convert point to dictionary representation."""
        return {'x': self.x, 'y': self.y}


class StrokeType(Enum):
    """Available stroke types for drawing operations."""
    BRUSH = "brush"
    PEN = "pen"
    MARKER = "marker"
    PENCIL = "pencil"


@dataclass(frozen=True)
class Stroke:
    """Immutable stroke representation with complete drawing data."""
    id: str
    stroke_type: StrokeType
    color: Tuple[int, int, int]
    width: int
    points: Tuple[Point, ...]
    created_at: datetime
    
    @classmethod
    def create_new(
        cls,
        stroke_type: StrokeType,
        color: Tuple[int, int, int],
        width: int,
        points: Optional[List[Point]] = None
    ) -> 'Stroke':
        """Create new stroke with generated ID and timestamp."""
        return cls(
            id=str(uuid.uuid4()),
            stroke_type=stroke_type,
            color=color,
            width=width,
            points=tuple(points or []),
            created_at=datetime.now(timezone.utc)
        )
    
    def add_point(self, point: Point) -> 'Stroke':
        """Create new stroke with additional point."""
        return Stroke(
            id=self.id,
            stroke_type=self.stroke_type,
            color=self.color,
            width=self.width,
            points=self.points + (point,),
            created_at=self.created_at
        )


@dataclass
class Page:
    """Drawing page containing strokes and metadata."""
    id: str
    strokes: List[Stroke] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def add_stroke(self, stroke: Stroke) -> None:
        """Add stroke to page and update modification time."""
        self.strokes.append(stroke)
        self.modified_at = datetime.now(timezone.utc)
    
    def remove_stroke(self, stroke_id: str) -> bool:
        """Remove stroke by ID and return success status."""
        original_count = len(self.strokes)
        self.strokes = [s for s in self.strokes if s.id != stroke_id]
        
        if len(self.strokes) < original_count:
            self.modified_at = datetime.now(timezone.utc)
            return True
        
        return False
    
    def get_stroke_count(self) -> int:
        """Get total number of strokes on page."""
        return len(self.strokes)


class DrawingError(ApplicationError):
    """Base error for drawing operations."""
    pass


class InvalidColorError(DrawingError):
    """Invalid color format or values provided."""
    pass


class InvalidWidthError(DrawingError):
    """Invalid stroke width provided."""
    pass


class StrokeCreationError(DrawingError):
    """Failed to create stroke instance."""
    pass


class ToolError(ApplicationError):
    """Base error for tool operations."""
    pass


class InvalidToolError(ToolError):
    """Invalid or unavailable tool specified."""
    pass


class PersistenceError(ApplicationError):
    """Base error for persistence operations."""
    pass


class SaveOperationError(PersistenceError):
    """Failed to save data to storage."""
    pass


class LoadOperationError(PersistenceError):
    """Failed to load data from storage."""
    pass


class RenderingError(ApplicationError):
    """Base error for rendering operations."""
    pass


class PerformanceMonitor:
    """Thread-safe performance monitoring and metrics collection."""
    
    def __init__(self):
        self._operation_times: Dict[str, List[float]] = {}
        self._operation_counts: Dict[str, int] = {}
        self._cache_hits: Dict[str, int] = {}
        self._cache_misses: Dict[str, int] = {}
    
    def record_operation_time(self, operation_name: str, duration_seconds: float) -> None:
        """Record execution time for operation."""
        if operation_name not in self._operation_times:
            self._operation_times[operation_name] = []
            self._operation_counts[operation_name] = 0
        
        self._operation_times[operation_name].append(duration_seconds)
        self._operation_counts[operation_name] += 1
        
        if len(self._operation_times[operation_name]) > 1000:
            self._operation_times[operation_name] = self._operation_times[operation_name][-500:]
    
    def record_cache_hit(self, cache_name: str) -> None:
        """Record cache hit for monitoring."""
        self._cache_hits[cache_name] = self._cache_hits.get(cache_name, 0) + 1
    
    def record_cache_miss(self, cache_name: str) -> None:
        """Record cache miss for monitoring."""
        self._cache_misses[cache_name] = self._cache_misses.get(cache_name, 0) + 1
    
    def get_operation_statistics(self, operation_name: str) -> Optional[Dict[str, float]]:
        """Get comprehensive statistics for operation."""
        if operation_name not in self._operation_times:
            return None
        
        times = self._operation_times[operation_name]
        if not times:
            return None
        
        return {
            'count': len(times),
            'average_seconds': sum(times) / len(times),
            'min_seconds': min(times),
            'max_seconds': max(times),
            'total_seconds': sum(times)
        }
    
    def get_cache_statistics(self, cache_name: str) -> Dict[str, int]:
        """Get cache hit/miss statistics."""
        hits = self._cache_hits.get(cache_name, 0)
        misses = self._cache_misses.get(cache_name, 0)
        total = hits + misses
        
        return {
            'hits': hits,
            'misses': misses,
            'total': total,
            'hit_rate_percent': int((hits / total * 100) if total > 0 else 0)
        }
    
    def get_all_operation_names(self) -> List[str]:
        """Get list of all monitored operations."""
        return list(self._operation_times.keys())


class SimpleCache:
    """Simple in-memory cache with size limits and basic eviction."""
    
    def __init__(self, max_size: int = 100):
        self._max_size = max_size
        self._cache: Dict[str, Any] = {}
        self._access_order: List[str] = []
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self._cache:
            self._update_access_order(key)
            return self._cache[key]
        return None
    
    def put(self, key: str, value: Any) -> None:
        """Store value in cache with size management."""
        if key in self._cache:
            self._cache[key] = value
            self._update_access_order(key)
            return
        
        if len(self._cache) >= self._max_size:
            self._evict_least_recently_used()
        
        self._cache[key] = value
        self._access_order.append(key)
    
    def _update_access_order(self, key: str) -> None:
        """Update access order for LRU tracking."""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def _evict_least_recently_used(self) -> None:
        """Remove least recently used item."""
        if self._access_order:
            oldest_key = self._access_order.pop(0)
            del self._cache[oldest_key]
    
    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()
        self._access_order.clear()
    
    def get_size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


global_performance_monitor = PerformanceMonitor()


def monitor_performance(operation_name: str):
    """Decorator to monitor function execution performance."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                global_performance_monitor.record_operation_time(operation_name, duration)
        return wrapper
    return decorator


def handle_errors(
    operation_name: str,
    component_name: str,
    fallback_value: Any = None,
    suppress_errors: bool = False
):
    """Decorator for comprehensive error handling with monitoring."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ApplicationError:
                logger.warning(f"Application error in {component_name}.{operation_name}")
                raise
            except Exception as error:
                logger.error(f"Unexpected error in {component_name}.{operation_name}: {error}")
                
                if suppress_errors:
                    logger.info(f"Returning fallback value for {operation_name}")
                    return fallback_value
                
                raise ApplicationError(
                    message=f"Operation {operation_name} failed: {error}",
                    error_code=f"{operation_name.upper()}_FAILED",
                    severity=ErrorSeverity.HIGH,
                    category=ErrorCategory.SYSTEM,
                    context={'component': component_name, 'operation': operation_name}
                ) from error
        return wrapper
    return decorator


def validate_color_format(color: Any) -> None:
    """Validate color format and raise specific error if invalid."""
    if not isinstance(color, (tuple, list)) or len(color) != 3:
        raise InvalidColorError(
            "Color must be RGB tuple with exactly 3 values",
            "INVALID_COLOR_FORMAT",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION
        )


def validate_color_values(color: Tuple[int, int, int]) -> None:
    """Validate RGB color value ranges."""
    for value in color:
        if not isinstance(value, int) or not (0 <= value <= 255):
            raise InvalidColorError(
                f"Color values must be integers between 0-255, got {color}",
                "INVALID_COLOR_VALUES",
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.VALIDATION
            )


def validate_stroke_width(width: Any) -> None:
    """Validate stroke width type and range."""
    if not isinstance(width, int):
        raise InvalidWidthError(
            f"Width must be integer, got {type(width).__name__}",
            "INVALID_WIDTH_TYPE",
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION
        )
    
    if not (1 <= width <= 200):
        raise InvalidWidthError(
            f"Width must be between 1-200 pixels, got {width}",
            "WIDTH_OUT_OF_RANGE",
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION
        )


def validate_stroke_type(stroke_type: Any) -> None:
    """Validate stroke type is supported."""
    if not isinstance(stroke_type, StrokeType):
        if isinstance(stroke_type, str):
            try:
                StrokeType(stroke_type.lower())
                return
            except ValueError:
                pass
        
        valid_types = [t.value for t in StrokeType]
        raise DrawingError(
            f"Invalid stroke type. Must be one of: {valid_types}",
            "INVALID_STROKE_TYPE",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION
        )


def create_validated_stroke(
    stroke_type: StrokeType,
    color: Tuple[int, int, int],
    width: int
) -> Stroke:
    """Create stroke with pre-validated parameters."""
    try:
        return Stroke.create_new(stroke_type, color, width)
    except Exception as error:
        raise StrokeCreationError(
            f"Failed to create stroke: {error}",
            "STROKE_CREATION_FAILED",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DRAWING
        ) from error


def convert_raw_point_to_point(raw_point: Any) -> Optional[Point]:
    """Convert various point formats to Point instance."""
    try:
        if isinstance(raw_point, dict):
            return Point.from_dict(raw_point)
        
        if isinstance(raw_point, (tuple, list)) and len(raw_point) >= 2:
            return Point(float(raw_point[0]), float(raw_point[1]))
        
        logger.warning(f"Unsupported point format: {type(raw_point)}")
        return None
        
    except (ValueError, KeyError, TypeError) as error:
        logger.warning(f"Failed to convert point {raw_point}: {error}")
        return None


class ToolProvider(Protocol):
    """Protocol for tool management implementations."""
    
    def get_current_tool(self) -> str:
        """Get currently active tool name."""
        ...
    
    def switch_tool(self, tool_name: str) -> bool:
        """Switch to specified tool."""
        ...
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        ...


class RenderingEngine(Protocol):
    """Protocol for rendering engine implementations."""
    
    def draw_stroke(self, points: List[Tuple[float, float]], color: Tuple[int, int, int], width: int) -> str:
        """Render stroke and return render ID."""
        ...
    
    def clear_canvas(self) -> None:
        """Clear entire canvas."""
        ...
    
    def get_canvas_size(self) -> Tuple[int, int]:
        """Get canvas dimensions."""
        ...


class DrawingRepository(Protocol):
    """Protocol for drawing data persistence."""
    
    def save_page(self, page: Page) -> None:
        """Save page to storage."""
        ...
    
    def load_page(self, page_id: str) -> Optional[Page]:
        """Load page from storage."""
        ...
    
    def delete_page(self, page_id: str) -> bool:
        """Delete page from storage."""
        ...
    
    def list_pages(self) -> List[str]:
        """List all available page IDs."""
        ...


class DrawingService:
    """
    Core drawing service with comprehensive validation and error handling.
    
    This service handles all drawing operations including stroke creation, point management,
    and canvas operations. Every operation includes validation, error handling, and 
    performance monitoring.
    
    Extension Points:
        - Add stroke validation: Create new validate_* functions
        - Add stroke operations: Add methods following the validate -> execute -> log pattern
        - Add caching: Use cached_operation decorator on expensive operations
    """
    
    def __init__(self, cache_size: int = 200):
        self._strokes: List[Stroke] = []
        self._point_conversion_cache = SimpleCache(cache_size)
    
    @handle_errors("create_stroke", "drawing_service")
    @monitor_performance("stroke_creation")
    def create_stroke_safely(
        self,
        color: Tuple[int, int, int],
        width: int = 3,
        stroke_type: Union[StrokeType, str] = StrokeType.BRUSH
    ) -> Stroke:
        """
        Create new stroke with comprehensive validation and monitoring.
        
        Args:
            color: RGB color tuple with values between 0-255
            width: Stroke width in pixels, must be between 1-200
            stroke_type: Type of stroke to create
            
        Returns:
            Newly created and validated stroke instance
            
        Raises:
            InvalidColorError: When color format or values are invalid
            InvalidWidthError: When width is outside valid range
            StrokeCreationError: When stroke instantiation fails
        """
        normalized_stroke_type = self._normalize_stroke_type(stroke_type)
        validated_color = self._validate_and_normalize_color(color)
        validated_width = self._validate_and_normalize_width(width)
        
        stroke = create_validated_stroke(normalized_stroke_type, validated_color, validated_width)
        self._add_stroke_to_collection(stroke)
        
        logger.debug(f"Created stroke {stroke.id} with color {validated_color}, width {validated_width}")
        return stroke
    
    def _normalize_stroke_type(self, stroke_type: Union[StrokeType, str]) -> StrokeType:
        """Normalize stroke type to enum value."""
        if isinstance(stroke_type, str):
            validate_stroke_type(stroke_type)
            return StrokeType(stroke_type.lower())
        
        validate_stroke_type(stroke_type)
        return stroke_type
    
    def _validate_and_normalize_color(self, color: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Validate and normalize color values."""
        validate_color_format(color)
        validated_color = tuple(int(c) for c in color)
        validate_color_values(validated_color)
        return validated_color
    
    def _validate_and_normalize_width(self, width: int) -> int:
        """Validate and normalize width value."""
        validate_stroke_width(width)
        return int(width)
    
    def _add_stroke_to_collection(self, stroke: Stroke) -> None:
        """Add stroke to internal collection."""
        self._strokes.append(stroke)
        self._invalidate_related_caches()
    
    def _invalidate_related_caches(self) -> None:
        """Invalidate caches when stroke collection changes."""
        self._point_conversion_cache.clear()
    
    @monitor_performance("point_conversion")
    def convert_points_with_caching(self, raw_points: List[Any]) -> List[Point]:
        """
        Convert raw point data to validated Point objects with caching.
        
        Args:
            raw_points: Collection of raw point data in various formats
            
        Returns:
            List of successfully converted Point objects
        """
        cache_key = self._generate_points_cache_key(raw_points)
        
        cached_result = self._point_conversion_cache.get(cache_key)
        if cached_result is not None:
            global_performance_monitor.record_cache_hit("point_conversion")
            return cached_result
        
        global_performance_monitor.record_cache_miss("point_conversion")
        converted_points = self._convert_points_without_cache(raw_points)
        
        self._point_conversion_cache.put(cache_key, converted_points)
        
        logger.debug(f"Converted {len(converted_points)}/{len(raw_points)} points successfully")
        return converted_points
    
    def _generate_points_cache_key(self, raw_points: List[Any]) -> str:
        """Generate cache key for point conversion."""
        return str(hash(str(raw_points)))
    
    def _convert_points_without_cache(self, raw_points: List[Any]) -> List[Point]:
        """Convert points without caching."""
        converted_points = []
        
        for raw_point in raw_points:
            converted_point = convert_raw_point_to_point(raw_point)
            if converted_point is not None:
                converted_points.append(converted_point)
        
        return converted_points
    
    @handle_errors("render_strokes", "drawing_service", fallback_value=[])
    @monitor_performance("stroke_rendering")
    def render_all_strokes(self, rendering_engine: RenderingEngine) -> List[str]:
        """
        Render all strokes using provided rendering engine.
        
        Args:
            rendering_engine: Engine implementation for rendering operations
            
        Returns:
            List of successfully rendered stroke identifiers
        """
        rendered_stroke_ids = []
        
        for stroke_index, stroke in enumerate(self._strokes):
            rendered_id = self._render_single_stroke_safely(rendering_engine, stroke, stroke_index)
            if rendered_id is not None:
                rendered_stroke_ids.append(rendered_id)
        
        logger.debug(f"Rendered {len(rendered_stroke_ids)}/{len(self._strokes)} strokes successfully")
        return rendered_stroke_ids
    
    def _render_single_stroke_safely(
        self,
        rendering_engine: RenderingEngine,
        stroke: Stroke,
        stroke_index: int
    ) -> Optional[str]:
        """Render individual stroke with error isolation."""
        try:
            if not stroke.points:
                logger.debug(f"Skipping stroke {stroke_index} - no points")
                return None
            
            point_coordinates = [(p.x, p.y) for p in stroke.points]
            render_id = rendering_engine.draw_stroke(point_coordinates, stroke.color, stroke.width)
            
            return f"stroke_{stroke_index}_{render_id}"
            
        except Exception as error:
            logger.warning(f"Failed to render stroke {stroke_index}: {error}")
            return None
    
    def get_stroke_count(self) -> int:
        """Get total number of strokes in collection."""
        return len(self._strokes)
    
    def get_all_strokes(self) -> List[Stroke]:
        """Get copy of all strokes in collection."""
        return self._strokes.copy()
    
    def clear_all_strokes(self) -> int:
        """Clear all strokes and return count of removed strokes."""
        removed_count = len(self._strokes)
        self._strokes.clear()
        self._invalidate_related_caches()
        
        logger.info(f"Cleared {removed_count} strokes")
        return removed_count


class StandardToolManager:
    """
    Standard tool management with validation and error handling.
    
    Manages drawing tool selection and switching with comprehensive validation
    and graceful fallback behavior when tool operations fail.
    
    Extension Points:
        - Add new tools: Add to AVAILABLE_TOOLS and implement validation
        - Add tool properties: Extend tool data structure
        - Add tool switching logic: Modify switch_tool_safely method
    """
    
    AVAILABLE_TOOLS = {"brush", "eraser", "line", "rectangle", "circle", "pencil", "marker"}
    DEFAULT_TOOL = "brush"
    
    def __init__(self):
        self._current_tool = self.DEFAULT_TOOL
    
    @handle_errors("switch_tool", "tool_manager")
    def switch_tool_safely(self, tool_name: str) -> bool:
        """
        Switch to different drawing tool with complete validation.
        
        Args:
            tool_name: Name of tool to activate
            
        Returns:
            True when tool switch completes successfully
            
        Raises:
            InvalidToolError: When tool name is invalid or unavailable
        """
        validated_tool_name = self._validate_and_normalize_tool_name(tool_name)
        previous_tool = self._current_tool
        
        self._update_current_tool(validated_tool_name)
        
        logger.info(f"Tool switched from {previous_tool} to {validated_tool_name}")
        return True
    
    def _validate_and_normalize_tool_name(self, tool_name: str) -> str:
        """Validate tool name format and availability."""
        if not isinstance(tool_name, str):
            raise InvalidToolError(
                f"Tool name must be string, got {type(tool_name).__name__}",
                "INVALID_TOOL_TYPE",
                category=ErrorCategory.TOOL,
                severity=ErrorSeverity.LOW
            )
        
        normalized_name = tool_name.lower().strip()
        
        if not self._is_tool_available(normalized_name):
            available_tools = ", ".join(sorted(self.AVAILABLE_TOOLS))
            raise InvalidToolError(
                f"Tool '{tool_name}' is not available. Available tools: {available_tools}",
                "UNKNOWN_TOOL",
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.TOOL,
                user_message=f"Tool '{tool_name}' is not available"
            )
        
        return normalized_name
    
    def _is_tool_available(self, tool_name: str) -> bool:
        """Check if specified tool is in available tools collection."""
        return tool_name in self.AVAILABLE_TOOLS
    
    def _update_current_tool(self, tool_name: str) -> None:
        """Update the current active tool."""
        self._current_tool = tool_name
    
    def get_current_tool(self) -> str:
        """Get currently active tool name."""
        return self._current_tool
    
    def get_available_tools(self) -> List[str]:
        """Get list of all available tool names."""
        return sorted(self.AVAILABLE_TOOLS)
    
    def reset_to_default_tool(self) -> str:
        """Reset to default tool and return tool name."""
        self._current_tool = self.DEFAULT_TOOL
        logger.info(f"Tool reset to default: {self.DEFAULT_TOOL}")
        return self._current_tool


class FilePersistenceManager:
    """
    File-based persistence manager with comprehensive error handling.
    
    Handles page saving and loading operations with robust error boundaries
    and graceful degradation when file system operations encounter issues.
    
    Extension Points:
        - Add file formats: Extend save/load methods with format detection
        - Add compression: Add compression options to save operations
        - Add backup: Implement automatic backup creation
        - Add validation: Add data integrity checks on load
    """
    
    def __init__(self, base_directory: Union[str, Path]):
        self._base_directory = Path(base_directory)
        self._ensure_directory_exists()
    
    def _ensure_directory_exists(self) -> None:
        """Create base directory if it does not exist."""
        try:
            self._base_directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {self._base_directory}")
        except Exception as error:
            raise PersistenceError(
                f"Failed to create directory {self._base_directory}: {error}",
                "DIRECTORY_CREATION_FAILED",
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.PERSISTENCE
            ) from error
    
    @handle_errors("save_page", "persistence_manager")
    def save_page_safely(self, page: Page, filename: Optional[str] = None) -> bool:
        """
        Save page data with comprehensive error protection.
        
        Args:
            page: Page instance containing data to persist
            filename: Optional filename, defaults to page ID
            
        Returns:
            True when save operation completes successfully
            
        Raises:
            SaveOperationError: When save operation fails critically
        """
        validated_page = self._validate_page_instance(page)
        target_path = self._prepare_target_path(filename or page.id)
        
        self._execute_save_operation(validated_page, target_path)
        
        logger.info(f"Page saved successfully to {target_path}")
        return True
    
    def _validate_page_instance(self, page: Page) -> Page:
        """Validate page instance before save operation."""
        if not isinstance(page, Page):
            raise SaveOperationError(
                f"Expected Page instance, got {type(page).__name__}",
                "INVALID_PAGE_INSTANCE",
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.PERSISTENCE
            )
        
        return page
    
    def _prepare_target_path(self, filename: str) -> Path:
        """Prepare and validate target path for save operation."""
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        
        return self._base_directory / filename
    
    def _execute_save_operation(self, page: Page, target_path: Path) -> None:
        """Execute the actual page persistence operation."""
        import json
        
        page_data = {
            'id': page.id,
            'created_at': page.created_at.isoformat(),
            'modified_at': page.modified_at.isoformat(),
            'strokes': [
                {
                    'id': stroke.id,
                    'stroke_type': stroke.stroke_type.value,
                    'color': stroke.color,
                    'width': stroke.width,
                    'created_at': stroke.created_at.isoformat(),
                    'points': [point.to_dict() for point in stroke.points]
                }
                for stroke in page.strokes
            ]
        }
        
        try:
            with target_path.open('w', encoding='utf-8') as file:
                json.dump(page_data, file, indent=2)
                
        except PermissionError as error:
            raise SaveOperationError(
                f"Permission denied writing to {target_path}: {error}",
                "SAVE_PERMISSION_DENIED",
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.PERSISTENCE,
                user_message="Cannot save file. Please check folder permissions."
            ) from error
            
        except OSError as error:
            raise SaveOperationError(
                f"File system error during save: {error}",
                "SAVE_FILESYSTEM_ERROR",
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.PERSISTENCE,
                user_message="Could not save file. Please check disk space and try again."
            ) from error
    
    @handle_errors("load_page", "persistence_manager", fallback_value=None)
    def load_page_safely(self, page_id: str) -> Optional[Page]:
        """
        Load page data with fallback handling for missing files.
        
        Args:
            page_id: Identifier of page to load
            
        Returns:
            Loaded page instance or None if file does not exist
            
        Raises:
            LoadOperationError: When load operation fails critically
        """
        source_path = self._prepare_source_path(page_id)
        
        if not self._does_source_file_exist(source_path):
            logger.info(f"No existing page file found for {page_id}")
            return None
        
        loaded_page = self._execute_load_operation(source_path)
        
        logger.info(f"Page loaded successfully from {source_path}")
        return loaded_page
    
    def _prepare_source_path(self, page_id: str) -> Path:
        """Prepare source path for load operation."""
        if not page_id.endswith('.json'):
            page_id = f"{page_id}.json"
        
        return self._base_directory / page_id
    
    def _does_source_file_exist(self, source_path: Path) -> bool:
        """Check if source file exists for loading."""
        return source_path.exists() and source_path.is_file()
    
    def _execute_load_operation(self, source_path: Path) -> Page:
        """Execute the actual page loading operation."""
        import json
        
        try:
            with source_path.open('r', encoding='utf-8') as file:
                page_data = json.load(file)
            
            return self._reconstruct_page_from_data(page_data)
            
        except PermissionError as error:
            raise LoadOperationError(
                f"Permission denied reading from {source_path}: {error}",
                "LOAD_PERMISSION_DENIED",
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.PERSISTENCE,
                user_message="Cannot read file. Please check file permissions."
            ) from error
            
        except (json.JSONDecodeError, KeyError, ValueError) as error:
            raise LoadOperationError(
                f"Invalid page data format in {source_path}: {error}",
                "LOAD_INVALID_FORMAT",
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.PERSISTENCE,
                user_message="File appears to be corrupted."
            ) from error
    
    def _reconstruct_page_from_data(self, page_data: Dict[str, Any]) -> Page:
        """Reconstruct Page instance from loaded data."""
        strokes = []
        
        for stroke_data in page_data.get('strokes', []):
            points = [Point.from_dict(p) for p in stroke_data['points']]
            
            stroke = Stroke(
                id=stroke_data['id'],
                stroke_type=StrokeType(stroke_data['stroke_type']),
                color=tuple(stroke_data['color']),
                width=stroke_data['width'],
                points=tuple(points),
                created_at=datetime.fromisoformat(stroke_data['created_at'])
            )
            strokes.append(stroke)
        
        return Page(
            id=page_data['id'],
            strokes=strokes,
            created_at=datetime.fromisoformat(page_data['created_at']),
            modified_at=datetime.fromisoformat(page_data['modified_at'])
        )
    
    def list_available_pages(self) -> List[str]:
        """List all available page IDs in storage."""
        try:
            json_files = list(self._base_directory.glob('*.json'))
            page_ids = [f.stem for f in json_files]
            
            logger.debug(f"Found {len(page_ids)} available pages")
            return sorted(page_ids)
            
        except Exception as error:
            logger.warning(f"Failed to list pages: {error}")
            return []
    
    def delete_page_safely(self, page_id: str) -> bool:
        """Delete page file safely with error handling."""
        try:
            source_path = self._prepare_source_path(page_id)
            
            if self._does_source_file_exist(source_path):
                source_path.unlink()
                logger.info(f"Page deleted: {page_id}")
                return True
            else:
                logger.warning(f"Page not found for deletion: {page_id}")
                return False
                
        except Exception as error:
            logger.error(f"Failed to delete page {page_id}: {error}")
            return False


class DrawingApplication:
    """
    Main drawing application coordinator with integrated services.
    
    This class orchestrates all drawing operations by coordinating between the drawing service,
    tool manager, and persistence manager. It provides a unified interface for drawing
    application functionality with comprehensive error handling and monitoring.
    
    Extension Points:
        - Add new services: Inject additional services through constructor
        - Add application operations: Add methods following validate -> coordinate -> monitor pattern
        - Add configuration: Extend constructor with configuration parameters
        - Add event handling: Add event notification capabilities
    """
    
    def __init__(
        self,
        drawing_service: DrawingService,
        tool_manager: StandardToolManager,
        persistence_manager: FilePersistenceManager
    ):
        self._drawing_service = drawing_service
        self._tool_manager = tool_manager
        self._persistence_manager = persistence_manager
        self._current_page: Optional[Page] = None
        
        logger.info("Drawing application initialized successfully")
    
    def get_drawing_service(self) -> DrawingService:
        """Get drawing service instance."""
        return self._drawing_service
    
    def get_tool_manager(self) -> StandardToolManager:
        """Get tool manager instance."""
        return self._tool_manager
    
    def get_persistence_manager(self) -> FilePersistenceManager:
        """Get persistence manager instance."""
        return self._persistence_manager
    
    @handle_errors("create_new_page", "drawing_application")
    def create_new_page(self, page_id: Optional[str] = None) -> Page:
        """Create new drawing page with optional custom ID."""
        page_id = page_id or str(uuid.uuid4())
        
        new_page = Page(id=page_id)
        self._current_page = new_page
        
        logger.info(f"Created new page: {page_id}")
        return new_page
    
    @handle_errors("load_existing_page", "drawing_application")
    def load_existing_page(self, page_id: str) -> Optional[Page]:
        """Load existing page from storage."""
        loaded_page = self._persistence_manager.load_page_safely(page_id)
        
        if loaded_page is not None:
            self._current_page = loaded_page
            logger.info(f"Loaded existing page: {page_id}")
        else:
            logger.warning(f"Page not found: {page_id}")
        
        return loaded_page
    
    @handle_errors("save_current_page", "drawing_application")
    def save_current_page(self) -> bool:
        """Save currently active page to storage."""
        if self._current_page is None:
            logger.warning("No current page to save")
            return False
        
        success = self._persistence_manager.save_page_safely(self._current_page)
        
        if success:
            logger.info(f"Current page saved: {self._current_page.id}")
        
        return success
    
    @handle_errors("add_stroke_to_current_page", "drawing_application")
    def add_stroke_to_current_page(
        self,
        color: Tuple[int, int, int],
        width: int = 3,
        stroke_type: Union[StrokeType, str] = StrokeType.BRUSH
    ) -> Optional[Stroke]:
        """Add new stroke to current page."""
        if self._current_page is None:
            self._current_page = self.create_new_page()
        
        stroke = self._drawing_service.create_stroke_safely(color, width, stroke_type)
        self._current_page.add_stroke(stroke)
        
        logger.debug(f"Added stroke {stroke.id} to page {self._current_page.id}")
        return stroke
    
    def get_current_page(self) -> Optional[Page]:
        """Get currently active page."""
        return self._current_page
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance monitoring summary."""
        summary = {
            'operations': {},
            'cache_stats': {},
            'system_info': {
                'current_page_id': self._current_page.id if self._current_page else None,
                'current_tool': self._tool_manager.get_current_tool(),
                'total_strokes': self._drawing_service.get_stroke_count()
            }
        }
        
        for operation_name in global_performance_monitor.get_all_operation_names():
            stats = global_performance_monitor.get_operation_statistics(operation_name)
            if stats:
                summary['operations'][operation_name] = stats
        
        cache_stats = global_performance_monitor.get_cache_statistics("point_conversion")
        summary['cache_stats']['point_conversion'] = cache_stats
        
        return summary


class DrawingApplicationFactory:
    """
    Factory for creating configured drawing application instances.
    
    Provides convenient methods for creating application instances with different
    configurations for production, testing, and development environments.
    
    Extension Points:
        - Add environment configurations: Create new create_*_application methods
        - Add custom services: Extend factory methods with service options
        - Add configuration validation: Add validation in factory methods
    """
    
    @staticmethod
    def create_production_application(
        storage_directory: Union[str, Path] = "./drawings",
        cache_size: int = 200
    ) -> DrawingApplication:
        """Create production-ready application instance."""
        drawing_service = DrawingService(cache_size=cache_size)
        tool_manager = StandardToolManager()
        persistence_manager = FilePersistenceManager(storage_directory)
        
        application = DrawingApplication(drawing_service, tool_manager, persistence_manager)
        
        logger.info("Production drawing application created")
        return application
    
    @staticmethod
    def create_test_application() -> DrawingApplication:
        """Create application instance optimized for testing."""
        import tempfile
        
        drawing_service = DrawingService(cache_size=10)
        tool_manager = StandardToolManager()
        
        temp_dir = tempfile.mkdtemp()
        persistence_manager = FilePersistenceManager(temp_dir)
        
        application = DrawingApplication(drawing_service, tool_manager, persistence_manager)
        
        logger.info("Test drawing application created")
        return application
    
    @staticmethod
    def create_development_application(
        storage_directory: Union[str, Path] = "./dev_drawings"
    ) -> DrawingApplication:
        """Create application instance for development with debug features."""
        drawing_service = DrawingService(cache_size=50)
        tool_manager = StandardToolManager()
        persistence_manager = FilePersistenceManager(storage_directory)
        
        application = DrawingApplication(drawing_service, tool_manager, persistence_manager)
        
        logger.info("Development drawing application created")
        return application


def demonstrate_error_handling_capabilities() -> None:
    """Demonstrate comprehensive error handling with controlled scenarios."""
    logger.info("Starting error handling demonstration")
    
    factory = DrawingApplicationFactory()
    app = factory.create_test_application()
    
    drawing_service = app.get_drawing_service()
    tool_manager = app.get_tool_manager()
    
    try:
        valid_stroke = drawing_service.create_stroke_safely((255, 0, 0), 5)
        logger.info(f"✓ Created valid stroke: {valid_stroke.id}")
    except Exception as error:
        logger.error(f"✗ Unexpected error with valid stroke: {error}")
    
    try:
        drawing_service.create_stroke_safely("invalid_color", 5)
        logger.warning("✗ Should have failed with invalid color")
    except InvalidColorError:
        logger.info("✓ Invalid color handled gracefully")
    except Exception as error:
        logger.error(f"✗ Wrong exception type: {error}")
    
    try:
        tool_manager.switch_tool_safely("eraser")
        logger.info("✓ Switched to valid tool successfully")
    except Exception as error:
        logger.error(f"✗ Unexpected error with valid tool: {error}")
    
    try:
        tool_manager.switch_tool_safely("invalid_tool")
        logger.warning("✗ Should have failed with invalid tool")
    except InvalidToolError:
        logger.info("✓ Invalid tool handled gracefully")
    except Exception as error:
        logger.error(f"✗ Wrong exception type: {error}")
    
    logger.info("Error handling demonstration completed")


def demonstrate_performance_monitoring_capabilities() -> None:
    """Demonstrate performance monitoring with realistic operations."""
    logger.info("Starting performance monitoring demonstration")
    
    factory = DrawingApplicationFactory()
    app = factory.create_test_application()
    
    drawing_service = app.get_drawing_service()
    
    stroke_one = drawing_service.create_stroke_safely((255, 0, 0), 5)
    stroke_two = drawing_service.create_stroke_safely((0, 255, 0), 3)
    stroke_three = drawing_service.create_stroke_safely((0, 0, 255), 7)
    
    raw_point_data = [
        {"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 5, "y": 6},
        (7, 8), (9, 10), [11, 12]
    ]
    
    drawing_service.convert_points_with_caching(raw_point_data)
    drawing_service.convert_points_with_caching(raw_point_data)
    drawing_service.convert_points_with_caching([{"x": 13, "y": 14}])
    
    performance_summary = app.get_performance_summary()
    
    logger.info("Performance Monitoring Results:")
    for operation_name, stats in performance_summary['operations'].items():
        logger.info(
            f"  {operation_name}: {stats['count']} calls, "
            f"avg {stats['average_seconds']*1000:.2f}ms"
        )
    
    for cache_name, stats in performance_summary['cache_stats'].items():
        logger.info(
            f"  {cache_name} cache: {stats['hit_rate_percent']}% hit rate "
            f"({stats['hits']} hits, {stats['misses']} misses)"
        )
    
    logger.info("Performance monitoring demonstration completed")


def run_comprehensive_demonstration() -> None:
    """Execute complete demonstration of integrated framework capabilities."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("=" * 60)
    logger.info("PRODUCTION-READY DRAWING FRAMEWORK DEMONSTRATION")
    logger.info("=" * 60)
    
    try:
        demonstrate_error_handling_capabilities()
        logger.info("-" * 40)
        demonstrate_performance_monitoring_capabilities()
        
        logger.info("=" * 60)
        logger.info("FRAMEWORK DEMONSTRATION COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
    except Exception as error:
        logger.error(f"Demonstration failed: {error}")
        raise


if __name__ == "__main__":
    run_comprehensive_demonstration()