"""
Consolidated Utilities Module
Eliminates ALL utility duplication through unified utility services.

This module consolidates patterns from grid.py, calculator.py, and scattered
utility functions into a single, comprehensive utility framework.
"""

import logging
import math
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union, Callable, Protocol
from enum import Enum
from pathlib import Path

from .core import UniversalService, ServiceConfiguration, ValidationService, EventBus, StorageProvider

logger = logging.getLogger(__name__)


class UtilityError(Exception):
    """Base exception for utility operations."""
    pass


class GridRenderingError(UtilityError):
    """Raised when grid rendering fails."""
    pass


class MathEngineError(UtilityError):
    """Raised when mathematical operations fail."""
    pass


class ConfigurationError(UtilityError):
    """Raised when configuration operations fail."""
    pass


# =============================================================================
# GRID RENDERING SYSTEM - Replaces entire grid.py
# =============================================================================

class GridStyle(Enum):
    """Grid visual styles."""
    DOTS = "dots"
    LINES = "lines"
    CROSSES = "crosses"
    MIXED = "mixed"


@dataclass(frozen=True)
class GridConfiguration:
    """Immutable grid rendering configuration."""
    spacing: int = 40
    color: Tuple[int, int, int] = (30, 30, 30)
    secondary_color: Tuple[int, int, int] = (60, 60, 60)
    style: GridStyle = GridStyle.LINES
    show_origin: bool = True
    origin_color: Tuple[int, int, int] = (100, 100, 100)
    major_grid_interval: int = 5
    line_width: int = 1
    alpha: float = 0.5
    
    def __post_init__(self):
        if self.spacing <= 0:
            raise ValueError("Grid spacing must be positive")
        if not (0.0 <= self.alpha <= 1.0):
            raise ValueError("Alpha must be between 0.0 and 1.0")


class GridRenderer:
    """
    Universal grid rendering system eliminating all grid duplication.
    
    Provides efficient, configurable grid rendering with multiple styles,
    viewport integration, and performance optimization.
    """
    
    def __init__(self, config: GridConfiguration = None):
        self.config = config or GridConfiguration()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cached_grid_lines: Optional[List[Tuple[Tuple[int, int], Tuple[int, int]]]] = None
        self.last_viewport_state = None
        
    def render_grid(
        self, 
        backend: Any, 
        screen_width: int, 
        screen_height: int,
        viewport_offset: Tuple[float, float] = (0.0, 0.0),
        viewport_scale: float = 1.0
    ):
        """Render grid to backend with viewport transformations."""
        try:
            if self.config.style == GridStyle.DOTS:
                self._render_dot_grid(backend, screen_width, screen_height, viewport_offset, viewport_scale)
            elif self.config.style == GridStyle.LINES:
                self._render_line_grid(backend, screen_width, screen_height, viewport_offset, viewport_scale)
            elif self.config.style == GridStyle.CROSSES:
                self._render_cross_grid(backend, screen_width, screen_height, viewport_offset, viewport_scale)
            elif self.config.style == GridStyle.MIXED:
                self._render_mixed_grid(backend, screen_width, screen_height, viewport_offset, viewport_scale)
                
        except Exception as error:
            raise GridRenderingError(f"Grid rendering failed: {error}") from error
    
    def _render_line_grid(self, backend, width, height, offset, scale):
        """Render line-based grid."""
        adjusted_spacing = int(self.config.spacing * scale)
        
        if adjusted_spacing < 2:  # Skip rendering if too small
            return
        
        offset_x, offset_y = offset
        start_x = int(-offset_x % adjusted_spacing - adjusted_spacing)
        start_y = int(-offset_y % adjusted_spacing - adjusted_spacing)
        
        # Vertical lines
        x = start_x
        line_count = 0
        while x < width and line_count < 200:  # Limit lines for performance
            screen_x = int(x)
            if 0 <= screen_x < width:
                color = self._get_line_color(x, adjusted_spacing)
                backend.draw_line(
                    (screen_x, 0), 
                    (screen_x, height),
                    self.config.line_width,
                    color
                )
            x += adjusted_spacing
            line_count += 1
        
        # Horizontal lines
        y = start_y
        line_count = 0
        while y < height and line_count < 200:  # Limit lines for performance
            screen_y = int(y)
            if 0 <= screen_y < height:
                color = self._get_line_color(y, adjusted_spacing)
                backend.draw_line(
                    (0, screen_y),
                    (width, screen_y),
                    self.config.line_width,
                    color
                )
            y += adjusted_spacing
            line_count += 1
        
        # Render origin if enabled
        if self.config.show_origin:
            self._render_origin(backend, width, height, offset)
    
    def _render_dot_grid(self, backend, width, height, offset, scale):
        """Render dot-based grid."""
        adjusted_spacing = int(self.config.spacing * scale)
        
        if adjusted_spacing < 4:  # Skip rendering if too small
            return
        
        offset_x, offset_y = offset
        start_x = int(-offset_x % adjusted_spacing - adjusted_spacing)
        start_y = int(-offset_y % adjusted_spacing - adjusted_spacing)
        
        dot_radius = max(1, self.config.line_width)
        
        y = start_y
        dot_count = 0
        while y < height and dot_count < 10000:  # Limit dots for performance
            x = start_x
            while x < width and dot_count < 10000:
                screen_x, screen_y = int(x), int(y)
                if 0 <= screen_x < width and 0 <= screen_y < height:
                    color = self._get_line_color(x + y, adjusted_spacing)
                    backend.draw_circle(
                        (screen_x, screen_y),
                        dot_radius,
                        color
                    )
                    dot_count += 1
                x += adjusted_spacing
            y += adjusted_spacing
    
    def _render_cross_grid(self, backend, width, height, offset, scale):
        """Render cross-based grid."""
        adjusted_spacing = int(self.config.spacing * scale)
        
        if adjusted_spacing < 8:  # Skip rendering if too small
            return
        
        offset_x, offset_y = offset
        start_x = int(-offset_x % adjusted_spacing - adjusted_spacing)
        start_y = int(-offset_y % adjusted_spacing - adjusted_spacing)
        
        cross_size = max(2, self.config.line_width * 2)
        
        y = start_y
        cross_count = 0
        while y < height and cross_count < 5000:  # Limit crosses for performance
            x = start_x
            while x < width and cross_count < 5000:
                screen_x, screen_y = int(x), int(y)
                if 0 <= screen_x < width and 0 <= screen_y < height:
                    color = self._get_line_color(x + y, adjusted_spacing)
                    # Draw cross
                    backend.draw_line(
                        (screen_x - cross_size, screen_y),
                        (screen_x + cross_size, screen_y),
                        self.config.line_width, color
                    )
                    backend.draw_line(
                        (screen_x, screen_y - cross_size),
                        (screen_x, screen_y + cross_size),
                        self.config.line_width, color
                    )
                    cross_count += 1
                x += adjusted_spacing
            y += adjusted_spacing
    
    def _render_mixed_grid(self, backend, width, height, offset, scale):
        """Render mixed grid (lines + dots)."""
        # Render lines first
        temp_config = GridConfiguration(
            spacing=self.config.spacing * self.config.major_grid_interval,
            color=self.config.secondary_color,
            style=GridStyle.LINES,
            line_width=max(1, self.config.line_width - 1)
        )
        temp_renderer = GridRenderer(temp_config)
        temp_renderer._render_line_grid(backend, width, height, offset, scale)
        
        # Then render dots
        self._render_dot_grid(backend, width, height, offset, scale)
    
    def _render_origin(self, backend, width, height, offset):
        """Render coordinate system origin."""
        offset_x, offset_y = offset
        origin_x = int(width / 2 - offset_x)
        origin_y = int(height / 2 - offset_y)
        
        if 0 <= origin_x < width and 0 <= origin_y < height:
            # Draw origin cross
            cross_size = self.config.spacing // 2
            backend.draw_line(
                (origin_x - cross_size, origin_y),
                (origin_x + cross_size, origin_y),
                max(2, self.config.line_width + 1),
                self.config.origin_color
            )
            backend.draw_line(
                (origin_x, origin_y - cross_size),
                (origin_x, origin_y + cross_size),
                max(2, self.config.line_width + 1),
                self.config.origin_color
            )
    
    def _get_line_color(self, position: float, spacing: int) -> Tuple[int, int, int]:
        """Get line color based on position (major vs minor grid)."""
        if abs(position) % (spacing * self.config.major_grid_interval) == 0:
            return self.config.secondary_color
        return self.config.color


# =============================================================================
# MATH ENGINE SYSTEM - Replaces calculator.py mathematical operations
# =============================================================================

class MathOperationType(Enum):
    """Mathematical operation types."""
    ARITHMETIC = "arithmetic"
    GEOMETRIC = "geometric"
    TRIGONOMETRIC = "trigonometric"
    ALGEBRAIC = "algebraic"
    STATISTICAL = "statistical"


@dataclass
class MathResult:
    """Result of mathematical operation."""
    value: Union[float, complex, List[float], Dict[str, Any]]
    operation_type: MathOperationType
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def success_result(cls, value: Any, op_type: MathOperationType, **metadata):
        """Create successful result."""
        return cls(value, op_type, True, None, metadata)
    
    @classmethod
    def error_result(cls, error_msg: str, op_type: MathOperationType):
        """Create error result."""
        return cls(None, op_type, False, error_msg)


class GeometryCalculator:
    """Specialized calculator for geometric operations."""
    
    @staticmethod
    def distance_between_points(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate distance between two points."""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return math.sqrt(dx * dx + dy * dy)
    
    @staticmethod
    def angle_between_points(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate angle between two points in radians."""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return math.atan2(dy, dx)
    
    @staticmethod
    def midpoint(p1: Tuple[float, float], p2: Tuple[float, float]) -> Tuple[float, float]:
        """Calculate midpoint between two points."""
        return ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    
    @staticmethod
    def line_length(points: List[Tuple[float, float]]) -> float:
        """Calculate total length of connected line segments."""
        if len(points) < 2:
            return 0.0
        
        total_length = 0.0
        for i in range(len(points) - 1):
            total_length += GeometryCalculator.distance_between_points(points[i], points[i + 1])
        
        return total_length
    
    @staticmethod
    def interpolate_points(p1: Tuple[float, float], p2: Tuple[float, float], t: float) -> Tuple[float, float]:
        """Interpolate between two points (t from 0 to 1)."""
        t = max(0.0, min(1.0, t))  # Clamp t
        return (
            p1[0] + (p2[0] - p1[0]) * t,
            p1[1] + (p2[1] - p1[1]) * t
        )
    
    @staticmethod
    def circle_area(radius: float) -> float:
        """Calculate circle area."""
        return math.pi * radius * radius
    
    @staticmethod
    def circle_circumference(radius: float) -> float:
        """Calculate circle circumference."""
        return 2 * math.pi * radius


class MathEngine:
    """
    Universal mathematical engine eliminating all math operation duplication.
    
    Provides comprehensive mathematical operations with error handling,
    result caching, and extensible operation registration.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.geometry = GeometryCalculator()
        self.operation_cache: Dict[str, MathResult] = {}
        self.cache_enabled = True
        self.max_cache_size = 1000
    
    def evaluate_expression(self, expression: str) -> MathResult:
        """Safely evaluate mathematical expression."""
        try:
            # Cache check
            if self.cache_enabled and expression in self.operation_cache:
                return self.operation_cache[expression]
            
            # Sanitize expression
            sanitized = self._sanitize_expression(expression)
            
            # Evaluate safely
            result = eval(sanitized, {"__builtins__": {}, "math": math})
            
            math_result = MathResult.success_result(
                result, 
                MathOperationType.ARITHMETIC,
                expression=expression
            )
            
            # Cache result
            self._cache_result(expression, math_result)
            
            return math_result
            
        except Exception as error:
            self.logger.error(f"Expression evaluation failed: {expression} - {error}")
            return MathResult.error_result(str(error), MathOperationType.ARITHMETIC)
    
    def solve_linear_equation(self, a: float, b: float, c: float) -> MathResult:
        """Solve linear equation ax + b = c."""
        try:
            if abs(a) < 1e-10:  # Avoid division by zero
                if abs(b - c) < 1e-10:
                    return MathResult.success_result(
                        "infinite_solutions", 
                        MathOperationType.ALGEBRAIC
                    )
                else:
                    return MathResult.success_result(
                        "no_solution", 
                        MathOperationType.ALGEBRAIC
                    )
            
            x = (c - b) / a
            return MathResult.success_result(x, MathOperationType.ALGEBRAIC)
            
        except Exception as error:
            return MathResult.error_result(str(error), MathOperationType.ALGEBRAIC)
    
    def solve_quadratic_equation(self, a: float, b: float, c: float) -> MathResult:
        """Solve quadratic equation ax² + bx + c = 0."""
        try:
            if abs(a) < 1e-10:
                return self.solve_linear_equation(b, c, 0)
            
            discriminant = b * b - 4 * a * c
            
            if discriminant < 0:
                # Complex solutions
                real_part = -b / (2 * a)
                imag_part = math.sqrt(-discriminant) / (2 * a)
                solutions = [
                    complex(real_part, imag_part),
                    complex(real_part, -imag_part)
                ]
            elif discriminant == 0:
                # One solution
                solutions = [-b / (2 * a)]
            else:
                # Two real solutions
                sqrt_disc = math.sqrt(discriminant)
                solutions = [
                    (-b + sqrt_disc) / (2 * a),
                    (-b - sqrt_disc) / (2 * a)
                ]
            
            return MathResult.success_result(
                solutions, 
                MathOperationType.ALGEBRAIC,
                discriminant=discriminant
            )
            
        except Exception as error:
            return MathResult.error_result(str(error), MathOperationType.ALGEBRAIC)
    
    def calculate_statistics(self, data: List[float]) -> MathResult:
        """Calculate basic statistics for dataset."""
        try:
            if not data:
                return MathResult.error_result("Empty dataset", MathOperationType.STATISTICAL)
            
            n = len(data)
            mean = sum(data) / n
            
            # Calculate variance and standard deviation
            variance = sum((x - mean) ** 2 for x in data) / n
            std_dev = math.sqrt(variance)
            
            # Calculate median
            sorted_data = sorted(data)
            if n % 2 == 0:
                median = (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2
            else:
                median = sorted_data[n // 2]
            
            stats = {
                'count': n,
                'mean': mean,
                'median': median,
                'min': min(data),
                'max': max(data),
                'variance': variance,
                'std_dev': std_dev,
                'range': max(data) - min(data)
            }
            
            return MathResult.success_result(stats, MathOperationType.STATISTICAL)
            
        except Exception as error:
            return MathResult.error_result(str(error), MathOperationType.STATISTICAL)
    
    def plot_function(self, expression: str, x_range: Tuple[float, float], num_points: int = 100) -> MathResult:
        """Generate points for plotting mathematical function."""
        try:
            x_min, x_max = x_range
            if x_min >= x_max:
                return MathResult.error_result("Invalid x range", MathOperationType.ARITHMETIC)
            
            points = []
            step = (x_max - x_min) / (num_points - 1)
            
            for i in range(num_points):
                x = x_min + i * step
                
                # Replace 'x' with actual value in expression
                expr_with_x = expression.replace('x', str(x))
                result = self.evaluate_expression(expr_with_x)
                
                if result.success and isinstance(result.value, (int, float)):
                    points.append((x, float(result.value)))
                else:
                    # Skip invalid points
                    continue
            
            return MathResult.success_result(
                points, 
                MathOperationType.ARITHMETIC,
                expression=expression,
                x_range=x_range
            )
            
        except Exception as error:
            return MathResult.error_result(str(error), MathOperationType.ARITHMETIC)
    
    def _sanitize_expression(self, expression: str) -> str:
        """Sanitize mathematical expression for safe evaluation."""
        # Remove dangerous functions/keywords
        dangerous = ['import', 'exec', 'eval', 'open', 'file', '__']
        expr = expression.lower()
        
        for danger in dangerous:
            if danger in expr:
                raise ValueError(f"Unsafe expression: contains '{danger}'")
        
        # Replace common mathematical functions
        replacements = {
            'sin': 'math.sin',
            'cos': 'math.cos', 
            'tan': 'math.tan',
            'sqrt': 'math.sqrt',
            'log': 'math.log',
            'exp': 'math.exp',
            'pi': 'math.pi',
            'e': 'math.e'
        }
        
        sanitized = expression
        for old, new in replacements.items():
            sanitized = re.sub(r'\b' + old + r'\b', new, sanitized)
        
        return sanitized
    
    def _cache_result(self, key: str, result: MathResult):
        """Cache computation result."""
        if not self.cache_enabled:
            return
        
        if len(self.operation_cache) >= self.max_cache_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self.operation_cache))
            del self.operation_cache[oldest_key]
        
        self.operation_cache[key] = result


# =============================================================================
# CONFIGURATION MANAGER - Unified configuration handling
# =============================================================================

class ConfigurationManager:
    """
    Universal configuration management eliminating config duplication.
    
    Provides type-safe configuration loading, validation, and hot-reloading
    with comprehensive error handling and environment integration.
    """
    
    def __init__(self, storage: StorageProvider, validation_service: ValidationService = None):
        self.storage = storage
        self.validation_service = validation_service
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_cache: Dict[str, Any] = {}
        self.watchers: Dict[str, List[Callable]] = {}
    
    def set_config(self, section: str, key: str, value: Any, validate: bool = True) -> bool:
        """Set configuration value with optional validation."""
        try:
            if validate and self.validation_service:
                # Validate based on key naming convention
                validator_name = self._get_validator_name(key)
                if validator_name:
                    result = self.validation_service.validate(validator_name, value)
                    if not result.is_valid:
                        raise ConfigurationError(f"Validation failed for {section}.{key}: {result.error_message}")
                    value = result.normalized_value
            
            config_key = f"{section}.{key}"
            self.storage.store(config_key, value)
            self.config_cache[config_key] = value
            
            # Notify watchers
            self._notify_watchers(config_key, value)
            
            self.logger.debug(f"Configuration set: {config_key} = {value}")
            return True
            
        except Exception as error:
            self.logger.error(f"Failed to set config {section}.{key}: {error}")
            raise ConfigurationError(f"Config set failed: {error}") from error
    
    def get_config(self, section: str, key: str, default: Any = None, type_hint: type = None) -> Any:
        """Get configuration value with type conversion."""
        try:
            config_key = f"{section}.{key}"
            
            # Check cache first
            if config_key in self.config_cache:
                value = self.config_cache[config_key]
            else:
                # Load from storage
                if self.storage.exists(config_key):
                    value = self.storage.retrieve(config_key)
                    self.config_cache[config_key] = value
                else:
                    value = default
            
            # Apply type conversion if requested
            if type_hint and value is not None:
                value = self._convert_type(value, type_hint)
            
            return value
            
        except Exception as error:
            self.logger.error(f"Failed to get config {section}.{key}: {error}")
            return default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section."""
        try:
            section_data = {}
            prefix = f"{section}."
            
            # Get from storage
            for key in self.storage.list_keys():
                if key.startswith(prefix):
                    config_key = key[len(prefix):]
                    section_data[config_key] = self.storage.retrieve(key)
            
            return section_data
            
        except Exception as error:
            self.logger.error(f"Failed to get section {section}: {error}")
            return {}
    
    def watch_config(self, section: str, key: str, callback: Callable[[Any], None]):
        """Watch configuration changes."""
        config_key = f"{section}.{key}"
        if config_key not in self.watchers:
            self.watchers[config_key] = []
        self.watchers[config_key].append(callback)
        
        self.logger.debug(f"Added watcher for {config_key}")
    
    def reload_config(self, section: str = None):
        """Reload configuration from storage."""
        try:
            if section:
                # Reload specific section
                prefix = f"{section}."
                keys_to_remove = [k for k in self.config_cache.keys() if k.startswith(prefix)]
                for key in keys_to_remove:
                    del self.config_cache[key]
            else:
                # Reload all
                self.config_cache.clear()
            
            self.logger.info(f"Configuration reloaded: {section or 'all'}")
            
        except Exception as error:
            self.logger.error(f"Failed to reload config: {error}")
    
    def _get_validator_name(self, key: str) -> Optional[str]:
        """Get validator name based on key naming convention."""
        key_lower = key.lower()
        
        if 'color' in key_lower:
            return 'color'
        elif 'coordinate' in key_lower or key_lower in ['x', 'y', 'position']:
            return 'coordinate'
        elif 'width' in key_lower or 'size' in key_lower:
            return 'brush_width'
        elif 'tool' in key_lower:
            return 'tool_key'
        elif 'path' in key_lower or 'file' in key_lower:
            return 'file_path'
        
        return None
    
    def _convert_type(self, value: Any, target_type: type) -> Any:
        """Convert value to target type."""
        if isinstance(value, target_type):
            return value
        
        try:
            if target_type == bool:
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                return bool(value)
            elif target_type == int:
                return int(float(value))  # Handle "5.0" -> 5
            elif target_type == float:
                return float(value)
            elif target_type == str:
                return str(value)
            else:
                return target_type(value)
                
        except Exception as error:
            self.logger.warning(f"Type conversion failed {value} -> {target_type}: {error}")
            return value
    
    def _notify_watchers(self, config_key: str, new_value: Any):
        """Notify configuration watchers."""
        if config_key in self.watchers:
            for callback in self.watchers[config_key]:
                try:
                    callback(new_value)
                except Exception as error:
                    self.logger.error(f"Watcher callback failed for {config_key}: {error}")


# =============================================================================
# UTILITY SERVICE - Unified access to all utilities
# =============================================================================

class UtilityService(UniversalService):
    """
    Universal utility service eliminating all utility duplication.
    
    Provides unified access to grid rendering, mathematical operations,
    configuration management, and other utility functions.
    """
    
    def __init__(
        self,
        config: ServiceConfiguration,
        storage: StorageProvider,
        validation_service: ValidationService = None,
        event_bus: EventBus = None
    ):
        super().__init__(config, validation_service, event_bus, storage)
        
        self.grid_renderer: Optional[GridRenderer] = None
        self.math_engine: Optional[MathEngine] = None
        self.configuration_manager: Optional[ConfigurationManager] = None
    
    def _initialize_service(self) -> None:
        """Initialize utility service components."""
        # Initialize grid renderer
        grid_config = GridConfiguration()
        self.grid_renderer = GridRenderer(grid_config)
        
        # Initialize math engine
        self.math_engine = MathEngine()
        
        # Initialize configuration manager
        self.configuration_manager = ConfigurationManager(
            self.storage_provider,
            self.validation_service
        )
        
        # Subscribe to relevant events
        if self.event_bus:
            self.event_bus.subscribe('grid_config_changed', self._handle_grid_config_change)
            self.event_bus.subscribe('math_calculation_requested', self._handle_math_request)
        
        self.logger.info("Utility service initialized")
    
    def _cleanup_service(self) -> None:
        """Clean up utility service resources."""
        if self.math_engine:
            self.math_engine.operation_cache.clear()
        
        self.logger.info("Utility service cleaned up")
    
    def render_grid(self, backend, width, height, viewport_offset=(0.0, 0.0), viewport_scale=1.0):
        """Render grid using current configuration."""
        if self.grid_renderer:
            return self.grid_renderer.render_grid(backend, width, height, viewport_offset, viewport_scale)
    
    def calculate_distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate distance between points."""
        if self.math_engine:
            return self.math_engine.geometry.distance_between_points(p1, p2)
        return 0.0
    
    def interpolate_line(self, p1: Tuple[float, float], p2: Tuple[float, float], t: float) -> Tuple[float, float]:
        """Interpolate between points."""
        if self.math_engine:
            return self.math_engine.geometry.interpolate_points(p1, p2, t)
        return p1
    
    def solve_equation(self, expression: str) -> MathResult:
        """Solve mathematical equation."""
        if self.math_engine:
            return self.math_engine.evaluate_expression(expression)
        return MathResult.error_result("Math engine not available", MathOperationType.ARITHMETIC)
    
    def plot_function(self, expression: str, x_range: Tuple[float, float], num_points: int = 100) -> MathResult:
        """Generate function plot points."""
        if self.math_engine:
            return self.math_engine.plot_function(expression, x_range, num_points)
        return MathResult.error_result("Math engine not available", MathOperationType.ARITHMETIC)
    
    def get_config(self, section: str, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        if self.configuration_manager:
            return self.configuration_manager.get_config(section, key, default)
        return default
    
    def set_config(self, section: str, key: str, value: Any) -> bool:
        """Set configuration value."""
        if self.configuration_manager:
            return self.configuration_manager.set_config(section, key, value)
        return False
    
    def _handle_grid_config_change(self, data: Dict[str, Any]):
        """Handle grid configuration change."""
        if self.grid_renderer:
            # Update grid configuration
            spacing = data.get('spacing', self.grid_renderer.config.spacing)
            color = data.get('color', self.grid_renderer.config.color)
            style = data.get('style', self.grid_renderer.config.style)
            
            new_config = GridConfiguration(spacing=spacing, color=color, style=style)
            self.grid_renderer = GridRenderer(new_config)
    
    def _handle_math_request(self, data: Dict[str, Any]):
        """Handle mathematical calculation request."""
        operation = data.get('operation')
        args = data.get('args', [])
        
        if operation == 'distance' and len(args) >= 2:
            result = self.calculate_distance(args[0], args[1])
            if self.event_bus:
                self.event_bus.publish('math_result', {'result': result})


# =============================================================================
# FACTORY FUNCTIONS AND CONVENIENCE INTERFACES
# =============================================================================

def create_grid_renderer(
    spacing: int = 40,
    color: Tuple[int, int, int] = (30, 30, 30),
    style: GridStyle = GridStyle.LINES
) -> GridRenderer:
    """Create grid renderer with standard configuration."""
    config = GridConfiguration(spacing=spacing, color=color, style=style)
    return GridRenderer(config)


def create_math_engine() -> MathEngine:
    """Create math engine with standard configuration."""
    return MathEngine()


def create_utility_service(
    storage: StorageProvider,
    validation_service: ValidationService = None,
    event_bus: EventBus = None
) -> UtilityService:
    """Create utility service with standard configuration."""
    config = ServiceConfiguration(
        service_name="utility_service",
        debug_mode=False,
        auto_start=True
    )
    
    return UtilityService(
        config=config,
        storage=storage,
        validation_service=validation_service,
        event_bus=event_bus
    )


# Convenience functions for common operations
def calculate_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate distance between two points."""
    return GeometryCalculator.distance_between_points(p1, p2)


def interpolate_line(p1: Tuple[float, float], p2: Tuple[float, float], t: float) -> Tuple[float, float]:
    """Interpolate between two points."""
    return GeometryCalculator.interpolate_points(p1, p2, t)


def solve_equation(expression: str) -> MathResult:
    """Solve mathematical equation using temporary engine."""
    engine = MathEngine()
    return engine.evaluate_expression(expression)


def plot_function(expression: str, x_range: Tuple[float, float], num_points: int = 100) -> MathResult:
    """Generate function plot points using temporary engine."""
    engine = MathEngine()
    return engine.plot_function(expression, x_range, num_points)