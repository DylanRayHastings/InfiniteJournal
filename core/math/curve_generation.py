# core/math/curve_generation.py (HEAVILY OPTIMIZED)
"""
Mathematical Curve Generation Framework - PERFORMANCE OPTIMIZED

Optimizations: __slots__, vectorized operations, pre-computed values, fast math.
"""

import logging
import math
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)

class CurveType(Enum):
    """Types of mathematical curves."""
    PARABOLA = "parabola"
    BEZIER_QUADRATIC = "bezier_quadratic"
    BEZIER_CUBIC = "bezier_cubic"
    CIRCLE = "circle"
    ELLIPSE = "ellipse"
    SINE_WAVE = "sine_wave"
    SPIRAL = "spiral"

@dataclass(slots=True)
class CurveParameters:
    """Parameters for curve generation - optimized with slots."""
    # General parameters
    resolution: int = 50
    start_x: float = 0.0
    start_y: float = 0.0
    end_x: float = 100.0
    end_y: float = 100.0
    
    # Parabola parameters
    parabola_a: float = 1.0
    parabola_b: float = 0.0
    parabola_c: float = 0.0
    vertex_x: Optional[float] = None
    vertex_y: Optional[float] = None
    curvature: float = 1.0
    
    # Bezier parameters
    control_points: Optional[List[Tuple[float, float]]] = None
    
    # Circle/Ellipse parameters
    center_x: float = 50.0
    center_y: float = 50.0
    radius_x: float = 50.0
    radius_y: float = 50.0
    
    # Wave parameters
    amplitude: float = 20.0
    frequency: float = 1.0
    phase: float = 0.0
    
    # Spiral parameters
    spiral_a: float = 1.0
    spiral_b: float = 0.1
    turns: float = 3.0
    
    def __post_init__(self):
        if self.control_points is None:
            self.control_points = []

class MathematicalCurve(ABC):
    """Abstract base class for mathematical curves."""
    
    @abstractmethod
    def generate_points(self, params: CurveParameters) -> List[Tuple[float, float]]:
        """Generate curve points based on parameters."""
    
    @abstractmethod
    def get_equation_string(self, params: CurveParameters) -> str:
        """Get human-readable equation string."""
        
    def validate_parameters(self, params: CurveParameters) -> bool:
        """Fast parameter validation."""
        return (params.resolution > 0 and 
               (params.start_x != params.end_x or params.start_y != params.end_y))

class ParabolaCurve(MathematicalCurve):
    """Mathematically accurate parabola generation - OPTIMIZED."""
    
    def generate_points(self, params: CurveParameters) -> List[Tuple[float, float]]:
        """Generate parabola points - HEAVILY OPTIMIZED."""
        if params.vertex_x is not None and params.vertex_y is not None:
            return self._generate_vertex_form_fast(params)
        else:
            return self._generate_fitted_parabola_fast(params)
            
    def _generate_vertex_form_fast(self, params: CurveParameters) -> List[Tuple[float, float]]:
        """Generate vertex form parabola - optimized."""
        h = params.vertex_x
        k = params.vertex_y
        a = params.parabola_a * params.curvature
        
        x_min = min(params.start_x, params.end_x)
        x_range = abs(params.end_x - params.start_x)
        resolution = params.resolution
        
        # Vectorized calculation
        points = []
        dx = x_range / resolution
        
        for i in range(resolution + 1):
            x = x_min + i * dx
            y = a * (x - h) ** 2 + k
            points.append((x, y))
            
        return points
            
    def _generate_fitted_parabola_fast(self, params: CurveParameters) -> List[Tuple[float, float]]:
        """Generate fitted parabola - HEAVILY OPTIMIZED."""
        x1, y1 = params.start_x, params.start_y
        x2, y2 = params.end_x, params.end_y
        
        # Fast calculations
        h = (x1 + x2) * 0.5  # Vertex x
        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        curvature_offset = distance * params.curvature * 0.25
        mid_y = (y1 + y2) * 0.5
        k = mid_y - curvature_offset
        
        # Calculate 'a' coefficient
        dx = x1 - h
        a = (y1 - k) / (dx * dx) if abs(dx) > 0.001 else params.curvature
            
        # Fast point generation
        x_range = x2 - x1
        resolution = params.resolution
        points = []
        
        for i in range(resolution + 1):
            t = i / resolution
            x = x1 + t * x_range
            y = a * (x - h) ** 2 + k
            points.append((x, y))
            
        return points
            
    def get_equation_string(self, params: CurveParameters) -> str:
        """Get parabola equation string."""
        if params.vertex_x is not None and params.vertex_y is not None:
            a = params.parabola_a * params.curvature
            return f"y = {a:.3f}(x - {params.vertex_x:.1f})² + {params.vertex_y:.1f}"
        else:
            return "y = a(x - h)² + k"

class BezierCurve(MathematicalCurve):
    """Bezier curve generation - OPTIMIZED."""
    
    def generate_points(self, params: CurveParameters) -> List[Tuple[float, float]]:
        """Generate Bezier curve points - optimized."""
        control_points = params.control_points
        
        if len(control_points) == 3:
            return self._generate_quadratic_bezier_fast(params)
        elif len(control_points) == 4:
            return self._generate_cubic_bezier_fast(params)
        else:
            return self._generate_default_bezier_fast(params)
            
    def _generate_quadratic_bezier_fast(self, params: CurveParameters) -> List[Tuple[float, float]]:
        """Generate quadratic Bezier - OPTIMIZED."""
        p0, p1, p2 = params.control_points[:3]
        resolution = params.resolution
        points = []
        
        # Pre-calculate for performance
        p0x, p0y = p0
        p1x, p1y = p1
        p2x, p2y = p2
        
        for i in range(resolution + 1):
            t = i / resolution
            mt = 1.0 - t
            mt2 = mt * mt
            t2 = t * t
            mt2t = 2 * mt * t
            
            x = mt2 * p0x + mt2t * p1x + t2 * p2x
            y = mt2 * p0y + mt2t * p1y + t2 * p2y
            
            points.append((x, y))
            
        return points
            
    def _generate_cubic_bezier_fast(self, params: CurveParameters) -> List[Tuple[float, float]]:
        """Generate cubic Bezier - OPTIMIZED."""
        p0, p1, p2, p3 = params.control_points[:4]
        resolution = params.resolution
        points = []
        
        # Pre-calculate coordinates
        p0x, p0y = p0
        p1x, p1y = p1
        p2x, p2y = p2
        p3x, p3y = p3
        
        for i in range(resolution + 1):
            t = i / resolution
            t2 = t * t
            t3 = t2 * t
            mt = 1.0 - t
            mt2 = mt * mt
            mt3 = mt2 * mt
            
            # Optimized cubic Bezier calculation
            x = mt3 * p0x + 3 * mt2 * t * p1x + 3 * mt * t2 * p2x + t3 * p3x
            y = mt3 * p0y + 3 * mt2 * t * p1y + 3 * mt * t2 * p2y + t3 * p3y
            
            points.append((x, y))
            
        return points
            
    def _generate_default_bezier_fast(self, params: CurveParameters) -> List[Tuple[float, float]]:
        """Generate default Bezier - optimized."""
        x1, y1 = params.start_x, params.start_y
        x2, y2 = params.end_x, params.end_y
        
        # Fast control point calculation
        dx = x2 - x1
        dy = y2 - y1
        offset = math.sqrt(dx*dx + dy*dy) * 0.25
        
        cp1_x = x1 + dx / 3
        cp1_y = y1 + dy / 3 - offset
        cp2_x = x1 + 2 * dx / 3
        cp2_y = y1 + 2 * dy / 3 + offset
        
        # Use optimized cubic generation
        temp_params = CurveParameters(
            resolution=params.resolution,
            control_points=[(x1, y1), (cp1_x, cp1_y), (cp2_x, cp2_y), (x2, y2)]
        )
        
        return self._generate_cubic_bezier_fast(temp_params)
            
    def get_equation_string(self, params: CurveParameters) -> str:
        """Get Bezier equation string."""
        if len(params.control_points) == 3:
            return "Quadratic Bezier"
        elif len(params.control_points) == 4:
            return "Cubic Bezier"
        else:
            return "Bezier curve"

class CircleCurve(MathematicalCurve):
    """Circle and ellipse generation - OPTIMIZED."""
    
    def generate_points(self, params: CurveParameters) -> List[Tuple[float, float]]:
        """Generate circle/ellipse points - optimized."""
        center_x = params.center_x
        center_y = params.center_y
        radius_x = params.radius_x
        radius_y = params.radius_y
        resolution = params.resolution
        
        # Pre-calculate angle step
        angle_step = 2 * math.pi / resolution
        
        points = []
        for i in range(resolution + 1):
            angle = i * angle_step
            cos_angle = math.cos(angle)
            sin_angle = math.sin(angle)
            
            x = center_x + radius_x * cos_angle
            y = center_y + radius_y * sin_angle
            
            points.append((x, y))
            
        return points
            
    def get_equation_string(self, params: CurveParameters) -> str:
        """Get circle/ellipse equation string."""
        if abs(params.radius_x - params.radius_y) < 0.001:
            return f"Circle: r = {params.radius_x:.1f}"
        else:
            return f"Ellipse: rx = {params.radius_x:.1f}, ry = {params.radius_y:.1f}"

class SineWaveCurve(MathematicalCurve):
    """Sine wave generation - OPTIMIZED."""
    
    def generate_points(self, params: CurveParameters) -> List[Tuple[float, float]]:
        """Generate sine wave points - optimized."""
        x_min = min(params.start_x, params.end_x)
        x_range = abs(params.end_x - params.start_x)
        resolution = params.resolution
        amplitude = params.amplitude
        frequency = params.frequency
        phase = params.phase
        
        points = []
        dx = x_range / resolution
        
        for i in range(resolution + 1):
            x = x_min + i * dx
            y = amplitude * math.sin(frequency * x + phase)
            points.append((x, y))
            
        return points
            
    def get_equation_string(self, params: CurveParameters) -> str:
        """Get sine wave equation string."""
        return f"y = {params.amplitude:.1f} × sin({params.frequency:.1f}x + {params.phase:.1f})"

class SpiralCurve(MathematicalCurve):
    """Spiral generation - OPTIMIZED."""
    
    def generate_points(self, params: CurveParameters) -> List[Tuple[float, float]]:
        """Generate spiral points - optimized."""
        center_x = params.center_x
        center_y = params.center_y
        spiral_a = params.spiral_a
        spiral_b = params.spiral_b
        turns = params.turns
        resolution = params.resolution
        
        max_theta = 2 * math.pi * turns
        theta_step = max_theta / resolution
        
        points = []
        for i in range(resolution + 1):
            theta = i * theta_step
            r = spiral_a + spiral_b * theta
            
            cos_theta = math.cos(theta)
            sin_theta = math.sin(theta)
            
            x = center_x + r * cos_theta
            y = center_y + r * sin_theta
            
            points.append((x, y))
            
        return points
            
    def get_equation_string(self, params: CurveParameters) -> str:
        """Get spiral equation string."""
        return f"Archimedean Spiral: r = {params.spiral_a:.1f} + {params.spiral_b:.1f}θ"

class CurveGenerationFramework:
    """Central framework for mathematical curve generation - OPTIMIZED."""
    __slots__ = ('curve_generators',)
    
    def __init__(self):
        self.curve_generators = {
            CurveType.PARABOLA: ParabolaCurve(),
            CurveType.BEZIER_QUADRATIC: BezierCurve(),
            CurveType.BEZIER_CUBIC: BezierCurve(),
            CurveType.CIRCLE: CircleCurve(),
            CurveType.ELLIPSE: CircleCurve(),
            CurveType.SINE_WAVE: SineWaveCurve(),
            CurveType.SPIRAL: SpiralCurve()
        }
        
    def generate_curve(self, curve_type: CurveType, params: CurveParameters) -> List[Tuple[float, float]]:
        """Generate curve points - optimized."""
        generator = self.curve_generators.get(curve_type)
        if not generator or not generator.validate_parameters(params):
            return []
            
        return generator.generate_points(params)
            
    def get_curve_equation(self, curve_type: CurveType, params: CurveParameters) -> str:
        """Get mathematical equation string."""
        generator = self.curve_generators.get(curve_type)
        return generator.get_equation_string(params) if generator else "Unknown curve"
            
    def fit_parabola_to_points(self, start: Tuple[float, float], end: Tuple[float, float], 
                              curvature: float = 1.0, resolution: int = 50) -> List[Tuple[float, float]]:
        """Fit parabola to two points - optimized."""
        params = CurveParameters(
            resolution=resolution,
            start_x=start[0], start_y=start[1],
            end_x=end[0], end_y=end[1],
            curvature=curvature
        )
        
        return self.generate_curve(CurveType.PARABOLA, params)
            
    def create_bezier_from_points(self, points: List[Tuple[float, float]], 
                                 resolution: int = 50) -> List[Tuple[float, float]]:
        """Create Bezier curve from control points - optimized."""
        if len(points) < 2:
            return points
                
        curve_type = CurveType.BEZIER_QUADRATIC if len(points) == 3 else CurveType.BEZIER_CUBIC
        params = CurveParameters(resolution=resolution, control_points=points)
        
        return self.generate_curve(curve_type, params)
            
    def create_circle_from_bounds(self, center: Tuple[float, float], radius: float, 
                                 resolution: int = 50) -> List[Tuple[float, float]]:
        """Create circle from center and radius - optimized."""
        params = CurveParameters(
            resolution=resolution,
            center_x=center[0], center_y=center[1],
            radius_x=radius, radius_y=radius
        )
        
        return self.generate_curve(CurveType.CIRCLE, params)
            
    def get_supported_curve_types(self) -> List[str]:
        """Get list of supported curve types."""
        return [curve_type.value for curve_type in self.curve_generators.keys()]

# Optimized convenience functions
def get_parabola(start_x: float, start_y: float, end_x: float, end_y: float, 
                curvature: float = 1.0, resolution: int = 50) -> List[Tuple[float, float]]:
    """Generate parabola points - optimized."""
    framework = CurveGenerationFramework()
    return framework.fit_parabola_to_points((start_x, start_y), (end_x, end_y), curvature, resolution)

def get_bezier_curve(control_points: List[Tuple[float, float]], 
                    resolution: int = 50) -> List[Tuple[float, float]]:
    """Generate Bezier curve points - optimized."""
    framework = CurveGenerationFramework()
    return framework.create_bezier_from_points(control_points, resolution)

def get_circle_curve(center_x: float, center_y: float, radius: float, 
                    resolution: int = 50) -> List[Tuple[float, float]]:
    """Generate circle curve points - optimized."""
    framework = CurveGenerationFramework()
    return framework.create_circle_from_bounds((center_x, center_y), radius, resolution)