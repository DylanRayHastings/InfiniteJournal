"""
Optimized Utilities Module.

Clean, efficient utility functions for drawing applications.
Eliminates complexity while maintaining full functionality.
"""

import logging
import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class UtilityError(Exception):
    """Base exception for utility operations."""
    pass


# =============================================================================
# CORE GEOMETRY UTILITIES
# =============================================================================

def calculate_distance(point_a: Tuple[float, float], point_b: Tuple[float, float]) -> float:
    """Calculate distance between two points."""
    dx = point_b[0] - point_a[0]
    dy = point_b[1] - point_a[1]
    return math.sqrt(dx * dx + dy * dy)


def calculate_angle(point_a: Tuple[float, float], point_b: Tuple[float, float]) -> float:
    """Calculate angle between two points in radians."""
    dx = point_b[0] - point_a[0]
    dy = point_b[1] - point_a[1]
    return math.atan2(dy, dx)


def find_midpoint(point_a: Tuple[float, float], point_b: Tuple[float, float]) -> Tuple[float, float]:
    """Find midpoint between two points."""
    return ((point_a[0] + point_b[0]) / 2, (point_a[1] + point_b[1]) / 2)


def interpolate_points(point_a: Tuple[float, float], point_b: Tuple[float, float], ratio: float) -> Tuple[float, float]:
    """Interpolate between two points using ratio (0.0 to 1.0)."""
    ratio = max(0.0, min(1.0, ratio))
    return (
        point_a[0] + (point_b[0] - point_a[0]) * ratio,
        point_a[1] + (point_b[1] - point_a[1]) * ratio
    )


def calculate_line_length(points: List[Tuple[float, float]]) -> float:
    """Calculate total length of connected line segments."""
    if len(points) < 2:
        return 0.0
    
    total_length = 0.0
    for i in range(len(points) - 1):
        total_length += calculate_distance(points[i], points[i + 1])
    
    return total_length


def is_point_in_circle(point: Tuple[float, float], center: Tuple[float, float], radius: float) -> bool:
    """Check if point is inside circle."""
    distance = calculate_distance(point, center)
    return distance <= radius


def calculate_circle_area(radius: float) -> float:
    """Calculate circle area."""
    return math.pi * radius * radius


def calculate_circle_circumference(radius: float) -> float:
    """Calculate circle circumference."""
    return 2 * math.pi * radius


# =============================================================================
# MATH OPERATIONS
# =============================================================================

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers avoiding division by zero."""
    if abs(denominator) < 1e-10:
        return default
    return numerator / denominator


def clamp_value(value: float, min_value: float, max_value: float) -> float:
    """Clamp value between minimum and maximum bounds."""
    return max(min_value, min(max_value, value))


def normalize_angle(angle: float) -> float:
    """Normalize angle to range [0, 2π)."""
    return angle % (2 * math.pi)


def degrees_to_radians(degrees: float) -> float:
    """Convert degrees to radians."""
    return degrees * math.pi / 180.0


def radians_to_degrees(radians: float) -> float:
    """Convert radians to degrees."""
    return radians * 180.0 / math.pi


def evaluate_simple_expression(expression: str) -> Optional[float]:
    """Safely evaluate simple mathematical expressions."""
    if not expression:
        return None
    
    try:
        # Remove dangerous content
        if any(danger in expression.lower() for danger in ['import', 'exec', 'eval', '__']):
            return None
        
        # Replace mathematical functions
        safe_expression = expression.replace('sin', 'math.sin')
        safe_expression = safe_expression.replace('cos', 'math.cos')
        safe_expression = safe_expression.replace('tan', 'math.tan')
        safe_expression = safe_expression.replace('sqrt', 'math.sqrt')
        safe_expression = safe_expression.replace('pi', 'math.pi')
        
        result = eval(safe_expression, {"__builtins__": {}, "math": math})
        return float(result)
        
    except Exception as error:
        logger.warning(f"Expression evaluation failed: {expression} - {error}")
        return None


def solve_linear_equation(coefficient_a: float, coefficient_b: float, constant_c: float) -> Optional[float]:
    """Solve linear equation ax + b = c for x."""
    if abs(coefficient_a) < 1e-10:
        return None
    
    return (constant_c - coefficient_b) / coefficient_a


def solve_quadratic_equation(coefficient_a: float, coefficient_b: float, coefficient_c: float) -> List[Union[float, complex]]:
    """Solve quadratic equation ax² + bx + c = 0."""
    if abs(coefficient_a) < 1e-10:
        # Linear equation
        linear_solution = solve_linear_equation(coefficient_b, coefficient_c, 0)
        return [linear_solution] if linear_solution is not None else []
    
    discriminant = coefficient_b * coefficient_b - 4 * coefficient_a * coefficient_c
    
    if discriminant < 0:
        # Complex solutions
        real_part = -coefficient_b / (2 * coefficient_a)
        imaginary_part = math.sqrt(-discriminant) / (2 * coefficient_a)
        return [
            complex(real_part, imaginary_part),
            complex(real_part, -imaginary_part)
        ]
    
    if discriminant == 0:
        # One solution
        return [-coefficient_b / (2 * coefficient_a)]
    
    # Two real solutions
    sqrt_discriminant = math.sqrt(discriminant)
    return [
        (-coefficient_b + sqrt_discriminant) / (2 * coefficient_a),
        (-coefficient_b - sqrt_discriminant) / (2 * coefficient_a)
    ]


def calculate_basic_statistics(data: List[float]) -> Dict[str, float]:
    """Calculate basic statistics for dataset."""
    if not data:
        return {}
    
    sorted_data = sorted(data)
    count = len(data)
    total = sum(data)
    mean = total / count
    
    # Calculate median
    if count % 2 == 0:
        median = (sorted_data[count // 2 - 1] + sorted_data[count // 2]) / 2
    else:
        median = sorted_data[count // 2]
    
    # Calculate variance and standard deviation
    variance = sum((x - mean) ** 2 for x in data) / count
    standard_deviation = math.sqrt(variance)
    
    return {
        'count': count,
        'sum': total,
        'mean': mean,
        'median': median,
        'min': min(data),
        'max': max(data),
        'range': max(data) - min(data),
        'variance': variance,
        'std_dev': standard_deviation
    }


# =============================================================================
# GRID RENDERING
# =============================================================================

class GridStyle(Enum):
    """Available grid rendering styles."""
    DOTS = "dots"
    LINES = "lines"
    CROSSES = "crosses"


@dataclass
class GridSettings:
    """Grid rendering configuration."""
    spacing: int = 40
    color: Tuple[int, int, int] = (30, 30, 30)
    style: GridStyle = GridStyle.LINES
    line_width: int = 1
    show_origin: bool = True
    origin_color: Tuple[int, int, int] = (100, 100, 100)
    
    def __post_init__(self):
        if self.spacing <= 0:
            raise ValueError("Grid spacing must be positive")


def render_grid_lines(backend, width: int, height: int, settings: GridSettings, 
                     offset: Tuple[float, float] = (0.0, 0.0), scale: float = 1.0) -> None:
    """Render grid using lines."""
    adjusted_spacing = int(settings.spacing * scale)
    
    if adjusted_spacing < 2:
        return
    
    offset_x, offset_y = offset
    start_x = int(-offset_x % adjusted_spacing - adjusted_spacing)
    start_y = int(-offset_y % adjusted_spacing - adjusted_spacing)
    
    # Draw vertical lines
    x_position = start_x
    line_count = 0
    while x_position < width and line_count < 200:
        if 0 <= x_position < width:
            backend.draw_line(
                (x_position, 0),
                (x_position, height),
                settings.line_width,
                settings.color
            )
        x_position += adjusted_spacing
        line_count += 1
    
    # Draw horizontal lines
    y_position = start_y
    line_count = 0
    while y_position < height and line_count < 200:
        if 0 <= y_position < height:
            backend.draw_line(
                (0, y_position),
                (width, y_position),
                settings.line_width,
                settings.color
            )
        y_position += adjusted_spacing
        line_count += 1


def render_grid_dots(backend, width: int, height: int, settings: GridSettings,
                    offset: Tuple[float, float] = (0.0, 0.0), scale: float = 1.0) -> None:
    """Render grid using dots."""
    adjusted_spacing = int(settings.spacing * scale)
    
    if adjusted_spacing < 4:
        return
    
    offset_x, offset_y = offset
    start_x = int(-offset_x % adjusted_spacing - adjusted_spacing)
    start_y = int(-offset_y % adjusted_spacing - adjusted_spacing)
    
    dot_radius = max(1, settings.line_width)
    dot_count = 0
    
    y_position = start_y
    while y_position < height and dot_count < 5000:
        x_position = start_x
        while x_position < width and dot_count < 5000:
            if 0 <= x_position < width and 0 <= y_position < height:
                backend.draw_circle(
                    (x_position, y_position),
                    dot_radius,
                    settings.color
                )
                dot_count += 1
            x_position += adjusted_spacing
        y_position += adjusted_spacing


def render_grid_crosses(backend, width: int, height: int, settings: GridSettings,
                       offset: Tuple[float, float] = (0.0, 0.0), scale: float = 1.0) -> None:
    """Render grid using crosses."""
    adjusted_spacing = int(settings.spacing * scale)
    
    if adjusted_spacing < 8:
        return
    
    offset_x, offset_y = offset
    start_x = int(-offset_x % adjusted_spacing - adjusted_spacing)
    start_y = int(-offset_y % adjusted_spacing - adjusted_spacing)
    
    cross_size = max(2, settings.line_width * 2)
    cross_count = 0
    
    y_position = start_y
    while y_position < height and cross_count < 2500:
        x_position = start_x
        while x_position < width and cross_count < 2500:
            if 0 <= x_position < width and 0 <= y_position < height:
                # Draw horizontal line of cross
                backend.draw_line(
                    (x_position - cross_size, y_position),
                    (x_position + cross_size, y_position),
                    settings.line_width,
                    settings.color
                )
                # Draw vertical line of cross
                backend.draw_line(
                    (x_position, y_position - cross_size),
                    (x_position, y_position + cross_size),
                    settings.line_width,
                    settings.color
                )
                cross_count += 1
            x_position += adjusted_spacing
        y_position += adjusted_spacing


def render_origin_marker(backend, width: int, height: int, settings: GridSettings,
                        offset: Tuple[float, float] = (0.0, 0.0)) -> None:
    """Render coordinate system origin marker."""
    if not settings.show_origin:
        return
    
    offset_x, offset_y = offset
    origin_x = int(width / 2 - offset_x)
    origin_y = int(height / 2 - offset_y)
    
    if not (0 <= origin_x < width and 0 <= origin_y < height):
        return
    
    cross_size = settings.spacing // 2
    origin_line_width = max(2, settings.line_width + 1)
    
    # Draw origin cross
    backend.draw_line(
        (origin_x - cross_size, origin_y),
        (origin_x + cross_size, origin_y),
        origin_line_width,
        settings.origin_color
    )
    backend.draw_line(
        (origin_x, origin_y - cross_size),
        (origin_x, origin_y + cross_size),
        origin_line_width,
        settings.origin_color
    )


def render_grid(backend, width: int, height: int, settings: GridSettings = None,
               offset: Tuple[float, float] = (0.0, 0.0), scale: float = 1.0) -> None:
    """Render complete grid based on settings."""
    if settings is None:
        settings = GridSettings()
    
    try:
        if settings.style == GridStyle.DOTS:
            render_grid_dots(backend, width, height, settings, offset, scale)
        elif settings.style == GridStyle.LINES:
            render_grid_lines(backend, width, height, settings, offset, scale)
        elif settings.style == GridStyle.CROSSES:
            render_grid_crosses(backend, width, height, settings, offset, scale)
        
        render_origin_marker(backend, width, height, settings, offset)
        
    except Exception as error:
        logger.error(f"Grid rendering failed: {error}")
        raise UtilityError(f"Grid rendering failed: {error}") from error


# =============================================================================
# CONFIGURATION UTILITIES
# =============================================================================

def validate_positive_number(value: Any, field_name: str) -> float:
    """Validate and convert value to positive number."""
    try:
        number = float(value)
        if number <= 0:
            raise ValueError(f"{field_name} must be positive")
        return number
    except (ValueError, TypeError) as error:
        raise ValueError(f"Invalid {field_name}: {error}") from error


def validate_color_tuple(value: Any, field_name: str) -> Tuple[int, int, int]:
    """Validate and convert value to RGB color tuple."""
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{field_name} must be RGB tuple with 3 values")
    
    try:
        rgb = tuple(int(clamp_value(component, 0, 255)) for component in value)
        return rgb
    except (ValueError, TypeError) as error:
        raise ValueError(f"Invalid {field_name}: {error}") from error


def validate_coordinate(value: Any, field_name: str) -> float:
    """Validate and convert value to coordinate."""
    try:
        return float(value)
    except (ValueError, TypeError) as error:
        raise ValueError(f"Invalid {field_name}: {error}") from error


def parse_config_value(value: str, target_type: type) -> Any:
    """Parse configuration string value to target type."""
    if target_type == bool:
        return value.lower() in ('true', '1', 'yes', 'on')
    
    if target_type == int:
        return int(float(value))
    
    if target_type == float:
        return float(value)
    
    if target_type == str:
        return value
    
    return target_type(value)


def create_default_grid_settings() -> GridSettings:
    """Create default grid settings for drawing applications."""
    return GridSettings(
        spacing=40,
        color=(30, 30, 30),
        style=GridStyle.LINES,
        line_width=1,
        show_origin=True,
        origin_color=(100, 100, 100)
    )


def create_grid_settings_from_dict(config_dict: Dict[str, Any]) -> GridSettings:
    """Create grid settings from configuration dictionary."""
    spacing = config_dict.get('spacing', 40)
    color = config_dict.get('color', (30, 30, 30))
    style_name = config_dict.get('style', 'lines')
    line_width = config_dict.get('line_width', 1)
    show_origin = config_dict.get('show_origin', True)
    origin_color = config_dict.get('origin_color', (100, 100, 100))
    
    # Convert style string to enum
    try:
        style = GridStyle(style_name.lower())
    except ValueError:
        style = GridStyle.LINES
    
    return GridSettings(
        spacing=int(spacing),
        color=validate_color_tuple(color, 'color'),
        style=style,
        line_width=int(line_width),
        show_origin=bool(show_origin),
        origin_color=validate_color_tuple(origin_color, 'origin_color')
    )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_point_list_from_coordinates(coordinates: List[float]) -> List[Tuple[float, float]]:
    """Create point list from flat coordinate list [x1, y1, x2, y2, ...]."""
    if len(coordinates) % 2 != 0:
        raise ValueError("Coordinate list must have even number of elements")
    
    points = []
    for i in range(0, len(coordinates), 2):
        points.append((coordinates[i], coordinates[i + 1]))
    
    return points


def flatten_point_list(points: List[Tuple[float, float]]) -> List[float]:
    """Flatten point list to coordinate list [x1, y1, x2, y2, ...]."""
    coordinates = []
    for point in points:
        coordinates.extend([point[0], point[1]])
    return coordinates


def snap_point_to_grid(point: Tuple[float, float], grid_spacing: int) -> Tuple[float, float]:
    """Snap point to nearest grid intersection."""
    snapped_x = round(point[0] / grid_spacing) * grid_spacing
    snapped_y = round(point[1] / grid_spacing) * grid_spacing
    return (snapped_x, snapped_y)


def generate_smooth_curve_points(control_points: List[Tuple[float, float]], 
                                num_segments: int = 50) -> List[Tuple[float, float]]:
    """Generate smooth curve points using simple interpolation."""
    if len(control_points) < 2:
        return control_points
    
    if len(control_points) == 2:
        # Simple linear interpolation
        curve_points = []
        for i in range(num_segments + 1):
            t = i / num_segments
            point = interpolate_points(control_points[0], control_points[1], t)
            curve_points.append(point)
        return curve_points
    
    # For multiple points, create segments between consecutive points
    curve_points = []
    points_per_segment = max(1, num_segments // (len(control_points) - 1))
    
    for i in range(len(control_points) - 1):
        for j in range(points_per_segment):
            t = j / points_per_segment
            point = interpolate_points(control_points[i], control_points[i + 1], t)
            curve_points.append(point)
    
    # Add final point
    curve_points.append(control_points[-1])
    return curve_points


def calculate_bounding_box(points: List[Tuple[float, float]]) -> Tuple[float, float, float, float]:
    """Calculate bounding box for list of points."""
    if not points:
        return (0.0, 0.0, 0.0, 0.0)
    
    x_coordinates = [point[0] for point in points]
    y_coordinates = [point[1] for point in points]
    
    min_x = min(x_coordinates)
    max_x = max(x_coordinates)
    min_y = min(y_coordinates)
    max_y = max(y_coordinates)
    
    return (min_x, min_y, max_x, max_y)


def is_point_in_bounding_box(point: Tuple[float, float], 
                           bounding_box: Tuple[float, float, float, float]) -> bool:
    """Check if point is inside bounding box."""
    x, y = point
    min_x, min_y, max_x, max_y = bounding_box
    return min_x <= x <= max_x and min_y <= y <= max_y