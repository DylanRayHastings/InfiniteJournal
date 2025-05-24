"""
Pure Python stroke generation system - OPTIMIZED

Optimizations: __slots__, faster math, reduced validation, algorithm improvements.
"""

import logging
import math
from typing import List, Tuple, Optional
from dataclasses import dataclass
from .models import Point, Stroke

logger = logging.getLogger(__name__)

@dataclass(slots=True)
class DrawingState:
    """Current state of drawing operation - OPTIMIZED."""
    is_drawing: bool = False
    current_stroke: Optional[Stroke] = None
    start_point: Optional[Point] = None
    last_point: Optional[Point] = None
    brush_width: int = 5
    brush_color: Tuple[int, int, int] = (255, 255, 255)
    tool_mode: str = "brush"

class BasicStrokeGenerator:
    """Generates strokes from input points - HEAVILY OPTIMIZED."""
    __slots__ = ('state', '_last_x', '_last_y', '_distance_threshold_sq')
    
    def __init__(self):
        self.state = DrawingState()
        self._last_x = 0.0
        self._last_y = 0.0
        self._distance_threshold_sq = 4.0  # Pre-computed square for distance check
        
    def start_stroke(self, x: int, y: int, width: int, color: Tuple[int, int, int], tool: str) -> bool:
        """Start a new stroke - optimized."""
        self.state.is_drawing = True
        self.state.brush_width = width
        self.state.brush_color = color if tool != 'eraser' else (0, 0, 0)
        self.state.tool_mode = tool
        
        # Create initial point
        fx, fy = float(x), float(y)
        self.state.start_point = Point(fx, fy, 0.0, width)
        self.state.last_point = self.state.start_point
        self._last_x, self._last_y = fx, fy
        
        # Create stroke for simple tools
        if tool in ('brush', 'eraser'):
            self.state.current_stroke = Stroke(self.state.brush_color, width=width)
            self.state.current_stroke.add_point(self.state.start_point)
            
        return True
    
    def add_point(self, x: int, y: int) -> bool:
        """Add point to current stroke - HEAVILY OPTIMIZED."""
        if not self.state.is_drawing:
            return False
            
        fx, fy = float(x), float(y)
        
        # Fast distance check using pre-computed threshold
        dx = fx - self._last_x
        dy = fy - self._last_y
        distance_sq = dx * dx + dy * dy
        
        # Dynamic threshold based on brush width
        threshold = max(self._distance_threshold_sq, self.state.brush_width * 0.25)
        
        if distance_sq < threshold:
            return True  # Skip point if too close
        
        # For simple tools, add point directly
        if self.state.tool_mode in ('brush', 'eraser') and self.state.current_stroke:
            point = Point(fx, fy, 0.0, self.state.brush_width)
            self.state.current_stroke.add_point(point)
            self.state.last_point = point
            self._last_x, self._last_y = fx, fy
            return True
                
        return False
    
    def end_stroke(self) -> Optional[Stroke]:
        """End current stroke - optimized."""
        if not self.state.is_drawing:
            return None
            
        completed_stroke = None
        
        if self.state.tool_mode in ('brush', 'eraser'):
            completed_stroke = self.state.current_stroke
        elif self.state.start_point and self.state.last_point:
            completed_stroke = self._generate_shape_stroke()
        
        # Reset state
        self.state = DrawingState()
        
        return completed_stroke if completed_stroke and completed_stroke.points else None
    
    def _generate_shape_stroke(self) -> Optional[Stroke]:
        """Generate stroke for shape tools - optimized."""
        if not self.state.start_point or not self.state.last_point:
            return None
            
        tool = self.state.tool_mode
        start = (self.state.start_point.x, self.state.start_point.y)
        end = (self.state.last_point.x, self.state.last_point.y)
        
        # Route to optimized shape generators
        points = []
        if tool == 'line':
            points = self._generate_line_fast(start, end)
        elif tool == 'rect':
            points = self._generate_rectangle_fast(start, end)
        elif tool == 'circle':
            points = self._generate_circle_fast(start, end)
        elif tool == 'triangle':
            points = self._generate_triangle_fast(start, end)
        elif tool == 'parabola':
            points = self._generate_parabola_fast(start, end)
        
        if points:
            stroke = Stroke((255, 255, 255), width=self.state.brush_width)
            # Fast point creation
            stroke.points = [Point(x, y, 0.0, self.state.brush_width) for x, y in points]
            return stroke
                
        return None
    
    def _generate_line_fast(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Generate line points - OPTIMIZED."""
        x1, y1 = start
        x2, y2 = end
        
        # Calculate optimal step count
        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        steps = max(2, int(distance * 0.5))
        
        # Pre-calculate increments
        dx = (x2 - x1) / steps
        dy = (y2 - y1) / steps
        
        return [(x1 + i * dx, y1 + i * dy) for i in range(steps + 1)]
    
    def _generate_rectangle_fast(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Generate rectangle outline - OPTIMIZED."""
        x1, y1 = start
        x2, y2 = end
        
        min_x, max_x = (x1, x2) if x1 <= x2 else (x2, x1)
        min_y, max_y = (y1, y2) if y1 <= y2 else (y2, y1)
        
        # Generate corners and connect
        corners = [(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y), (min_x, min_y)]
        
        points = []
        for i in range(len(corners) - 1):
            points.extend(self._generate_line_fast(corners[i], corners[i + 1])[:-1])  # Avoid duplicates
        points.append(corners[0])  # Close the rectangle
        
        return points
    
    def _generate_circle_fast(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Generate circle outline - OPTIMIZED."""
        center_x = (start[0] + end[0]) * 0.5
        center_y = (start[1] + end[1]) * 0.5
        radius = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2) * 0.5
        
        if radius < 1:
            return [start, end]
        
        # Optimal point count based on radius
        num_points = max(12, min(64, int(radius * 0.3)))
        angle_step = 2 * math.pi / num_points
        
        return [(center_x + radius * math.cos(i * angle_step),
                 center_y + radius * math.sin(i * angle_step)) for i in range(num_points + 1)]
    
    def _generate_triangle_fast(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Generate triangle outline - OPTIMIZED."""
        x1, y1 = start
        x2, y2 = end
        x3, y3 = x2, y1  # Right angle triangle
        
        # Connect vertices
        points = []
        points.extend(self._generate_line_fast((x1, y1), (x2, y2))[:-1])
        points.extend(self._generate_line_fast((x2, y2), (x3, y3))[:-1])
        points.extend(self._generate_line_fast((x3, y3), (x1, y1)))
        
        return points
    
    def _generate_parabola_fast(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Generate parabola curve - OPTIMIZED."""
        x1, y1 = start
        x2, y2 = end
        
        if abs(x2 - x1) < 1:
            return self._generate_line_fast(start, end)
        
        # Fast parabola calculation
        h = (x1 + x2) * 0.5  # Vertex x
        k = min(y1, y2) - abs(x2 - x1) * 0.25  # Vertex y
        
        # Calculate coefficient
        a = (y1 - k) / ((x1 - h) ** 2) if abs(x1 - h) > 0.01 else 1.0
        
        # Generate points efficiently
        steps = 30
        dx = (x2 - x1) / steps
        
        points = []
        for i in range(steps + 1):
            x = x1 + i * dx
            y = a * (x - h) ** 2 + k
            points.append((x, y))
            
        return points
    
    def update_brush_width(self, new_width: int) -> None:
        """Update brush width - optimized."""
        if 1 <= new_width <= 200:
            self.state.brush_width = new_width
            if self.state.is_drawing and self.state.current_stroke:
                self.state.current_stroke.width = new_width