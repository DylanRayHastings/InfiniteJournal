"""
Pure Python stroke generation system - independent of rendering backend.

Provides clean drawing logic that can work with any renderer.
"""

import logging
import math
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from .models import Point, Stroke

logger = logging.getLogger(__name__)


@dataclass
class DrawingState:
    """Current state of drawing operation."""
    is_drawing: bool = False
    current_stroke: Optional[Stroke] = None
    start_point: Optional[Point] = None
    last_point: Optional[Point] = None
    brush_width: int = 5
    brush_color: Tuple[int, int, int] = (255, 255, 255)
    tool_mode: str = "brush"


class BasicStrokeGenerator:
    """Generates strokes from input points - pure Python, no dependencies."""
    
    def __init__(self):
        self.state = DrawingState()
        
    def start_stroke(self, x: int, y: int, width: int, color: Tuple[int, int, int], tool: str) -> bool:
        """Start a new stroke."""
        try:
            self.state.is_drawing = True
            self.state.brush_width = width
            self.state.brush_color = color if tool != 'eraser' else (0, 0, 0)
            self.state.tool_mode = tool
            
            # Create initial point
            self.state.start_point = Point(float(x), float(y), 0.0, width)
            self.state.last_point = self.state.start_point
            
            # Create stroke for simple tools
            if tool in ['brush', 'eraser']:
                self.state.current_stroke = Stroke(self.state.brush_color, width=width)
                self.state.current_stroke.add_point(self.state.start_point)
                
            logger.debug("Started stroke: tool=%s, width=%d, pos=(%d,%d)", tool, width, x, y)
            return True
            
        except Exception as e:
            logger.error("Error starting stroke: %s", e)
            self.state.is_drawing = False
            return False
    
    def add_point(self, x: int, y: int) -> bool:
        """Add point to current stroke."""
        if not self.state.is_drawing:
            return False
            
        try:
            point = Point(float(x), float(y), 0.0, self.state.brush_width)
            
            # For simple tools, add point directly
            if self.state.tool_mode in ['brush', 'eraser'] and self.state.current_stroke:
                # Simple distance check to avoid too many points
                if self.state.last_point:
                    dx = x - self.state.last_point.x
                    dy = y - self.state.last_point.y
                    distance_sq = dx * dx + dy * dy
                    
                    # Skip if too close
                    threshold = max(1, self.state.brush_width // 4)
                    if distance_sq < threshold:
                        return True
                
                self.state.current_stroke.add_point(point)
                self.state.last_point = point
                return True
                
        except Exception as e:
            logger.error("Error adding point: %s", e)
            
        return False
    
    def end_stroke(self) -> Optional[Stroke]:
        """End current stroke and return completed stroke."""
        if not self.state.is_drawing:
            return None
            
        try:
            completed_stroke = None
            
            if self.state.tool_mode in ['brush', 'eraser']:
                completed_stroke = self.state.current_stroke
            elif self.state.start_point and self.state.last_point:
                # Generate shape stroke
                completed_stroke = self._generate_shape_stroke()
            
            # Reset state
            self.state = DrawingState()
            
            if completed_stroke and completed_stroke.points:
                logger.debug("Completed stroke with %d points", len(completed_stroke.points))
                return completed_stroke
                
        except Exception as e:
            logger.error("Error ending stroke: %s", e)
            
        # Reset state even on error
        self.state = DrawingState()
        return None
    
    def _generate_shape_stroke(self) -> Optional[Stroke]:
        """Generate stroke for shape tools."""
        if not self.state.start_point or not self.state.last_point:
            return None
            
        try:
            tool = self.state.tool_mode
            start = (self.state.start_point.x, self.state.start_point.y)
            end = (self.state.last_point.x, self.state.last_point.y)
            
            points = []
            
            if tool == 'line':
                points = self._generate_line(start, end)
            elif tool == 'rect':
                points = self._generate_rectangle(start, end)
            elif tool == 'circle':
                points = self._generate_circle(start, end)
            elif tool == 'triangle':
                points = self._generate_triangle(start, end)
            elif tool == 'parabola':
                points = self._generate_parabola(start, end)
            
            if points:
                stroke = Stroke((255, 255, 255), width=self.state.brush_width)
                for x, y in points:
                    stroke.add_point(Point(x, y, 0.0, self.state.brush_width))
                return stroke
                
        except Exception as e:
            logger.error("Error generating shape stroke: %s", e)
            
        return None
    
    def _generate_line(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Generate line points."""
        points = []
        steps = max(2, int(math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2) / 2))
        
        for i in range(steps + 1):
            t = i / steps
            x = start[0] + t * (end[0] - start[0])
            y = start[1] + t * (end[1] - start[1])
            points.append((x, y))
            
        return points
    
    def _generate_rectangle(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Generate rectangle outline."""
        x1, y1 = start
        x2, y2 = end
        
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)
        
        points = []
        # Top, right, bottom, left edges
        points.extend(self._generate_line((min_x, min_y), (max_x, min_y)))
        points.extend(self._generate_line((max_x, min_y), (max_x, max_y)))
        points.extend(self._generate_line((max_x, max_y), (min_x, max_y)))
        points.extend(self._generate_line((min_x, max_y), (min_x, min_y)))
        
        return points
    
    def _generate_circle(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Generate circle outline."""
        center_x = (start[0] + end[0]) / 2
        center_y = (start[1] + end[1]) / 2
        radius = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2) / 2
        
        if radius < 1:
            return [start, end]
        
        points = []
        num_points = max(12, int(radius * 0.5))
        
        for i in range(num_points + 1):
            angle = 2 * math.pi * i / num_points
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            points.append((x, y))
            
        return points
    
    def _generate_triangle(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Generate triangle outline."""
        x1, y1 = start
        x2, y2 = end
        x3, y3 = x2, y1  # Right angle triangle
        
        points = []
        points.extend(self._generate_line((x1, y1), (x2, y2)))
        points.extend(self._generate_line((x2, y2), (x3, y3)))
        points.extend(self._generate_line((x3, y3), (x1, y1)))
        
        return points
    
    def _generate_parabola(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Generate parabola curve."""
        x1, y1 = start
        x2, y2 = end
        
        if abs(x2 - x1) < 1:
            return self._generate_line(start, end)
        
        # Simple parabola fitting
        h = (x1 + x2) / 2  # Vertex x
        k = min(y1, y2) - abs(x2 - x1) / 4  # Vertex y
        
        # Calculate coefficient
        if abs(x1 - h) > 0.01:
            a = (y1 - k) / ((x1 - h) ** 2)
        else:
            a = 1.0
        
        points = []
        steps = 30
        
        for i in range(steps + 1):
            t = i / steps
            x = x1 + t * (x2 - x1)
            y = a * (x - h) ** 2 + k
            points.append((x, y))
            
        return points
    
    def update_brush_width(self, new_width: int) -> None:
        """Update brush width during drawing."""
        if 1 <= new_width <= 200:
            self.state.brush_width = new_width
            
            # Update current stroke if drawing
            if self.state.is_drawing and self.state.current_stroke:
                self.state.current_stroke.width = new_width