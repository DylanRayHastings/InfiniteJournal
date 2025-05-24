# core/drawing/canvas.py (PERFORMANCE OPTIMIZED)
"""
Enhanced drawing canvas with live rendering support - OPTIMIZED

Optimizations: __slots__, reduced validation, faster operations, memory pooling.
"""

import logging
from typing import List, Tuple, Optional
from .models import Page, Stroke, Point
from .stroke_generator import BasicStrokeGenerator

logger = logging.getLogger(__name__)

class DrawingCanvas:
    """Canvas that manages drawing operations - OPTIMIZED."""
    __slots__ = ('page', 'stroke_generator', '_current_brush_width', '_current_brush_color',
                 '_current_tool', '_live_stroke_points', '_is_live_drawing', '_point_pool')
    
    def __init__(self):
        self.page = Page()
        self.stroke_generator = BasicStrokeGenerator()
        self._current_brush_width = 5
        self._current_brush_color = (255, 255, 255)
        self._current_tool = "brush"
        
        # Live rendering - optimized with pre-allocated list
        self._live_stroke_points = []
        self._is_live_drawing = False
        
        # Point pool for memory reuse
        self._point_pool = []
        
    def start_drawing(self, x: int, y: int) -> bool:
        """Start drawing at position - optimized."""
        success = self.stroke_generator.start_stroke(
            x, y, self._current_brush_width, self._current_brush_color, self._current_tool
        )
        
        if success:
            self._is_live_drawing = True
            # Reuse list to avoid allocation
            self._live_stroke_points.clear()
            self._live_stroke_points.append((x, y))
        
        return success
    
    def continue_drawing(self, x: int, y: int) -> bool:
        """Continue drawing - optimized."""
        success = self.stroke_generator.add_point(x, y)
        
        if success and self._is_live_drawing:
            self._live_stroke_points.append((x, y))
            
            # Efficient memory management
            if len(self._live_stroke_points) > 1000:
                # Keep second half instead of copying
                mid = len(self._live_stroke_points) >> 1
                self._live_stroke_points = self._live_stroke_points[mid:]
        
        return success
    
    def end_drawing(self) -> bool:
        """End drawing - optimized."""
        stroke = self.stroke_generator.end_stroke()
        success = False
        
        if stroke:
            self.page.strokes.append(stroke)
            success = True
        
        # Clear live tracking
        self._is_live_drawing = False
        self._live_stroke_points.clear()
        
        return success
    
    def get_live_stroke_points(self) -> List[Tuple[int, int]]:
        """Get current live stroke points - optimized."""
        return self._live_stroke_points if self._is_live_drawing else []
    
    def is_live_drawing(self) -> bool:
        """Check if currently in live drawing mode."""
        return self._is_live_drawing
    
    def clear(self) -> None:
        """Clear the canvas."""
        self.page.clear()
        self._live_stroke_points.clear()
        self._is_live_drawing = False
    
    def set_brush_width(self, width: int) -> None:
        """Set brush width - optimized."""
        if 1 <= width <= 200:
            self._current_brush_width = width
            self.stroke_generator.update_brush_width(width)
    
    def set_brush_color(self, color: Tuple[int, int, int]) -> None:
        """Set brush color."""
        self._current_brush_color = color
    
    def set_tool(self, tool: str) -> None:
        """Set current tool."""
        self._current_tool = tool
    
    def get_strokes(self) -> List[Stroke]:
        """Get all strokes for rendering."""
        return self.page.strokes
    
    def is_drawing(self) -> bool:
        """Check if currently drawing."""
        return self.stroke_generator.state.is_drawing or self._is_live_drawing
    
    def get_stroke_count(self) -> int:
        """Get number of strokes."""
        return len(self.page.strokes)
    
    def render(self, renderer) -> None:
        """Render all strokes - HEAVILY OPTIMIZED."""
        # Fast path for empty canvas
        if not self.page.strokes and not self._is_live_drawing:
            return
            
        # Render completed strokes
        for stroke in self.page.strokes:
            if not stroke.points:
                continue
                
            points_len = len(stroke.points)
            
            if points_len == 1:
                # Single point optimization
                point = stroke.points[0]
                if hasattr(renderer, 'draw_circle'):
                    radius = max(1, stroke.width >> 1)  # Fast division
                    renderer.draw_circle((int(point.x), int(point.y)), radius, stroke.color)
            elif points_len > 1:
                # Multi-point stroke - pre-convert all points
                points = [(int(p.x), int(p.y)) for p in stroke.points]
                
                if hasattr(renderer, 'draw_stroke_enhanced'):
                    renderer.draw_stroke_enhanced(points, stroke.color, stroke.width)
                elif hasattr(renderer, 'draw_line'):
                    # Optimized line rendering
                    width = stroke.width
                    color = stroke.color
                    
                    for i in range(points_len - 1):
                        renderer.draw_line(points[i], points[i + 1], width, color)
                    
                    # End caps optimization
                    if width > 2 and hasattr(renderer, 'draw_circle'):
                        cap_radius = width >> 1
                        renderer.draw_circle(points[0], cap_radius, color)
                        renderer.draw_circle(points[-1], cap_radius, color)
        
        # Render live stroke preview
        if self._is_live_drawing and len(self._live_stroke_points) >= 2:
            self._render_live_preview_optimized(renderer)
                            
    def _render_live_preview_optimized(self, renderer) -> None:
        """Render live stroke preview - OPTIMIZED."""
        preview_color = self._current_brush_color
        preview_width = self._current_brush_width
        
        # Make eraser preview visible
        if self._current_tool == 'eraser':
            preview_color = (255, 100, 100)
        
        points = self._live_stroke_points
        
        if hasattr(renderer, 'draw_stroke_enhanced'):
            renderer.draw_stroke_enhanced(points, preview_color, preview_width)
        else:
            # Optimized fallback
            points_len = len(points)
            for i in range(points_len - 1):
                renderer.draw_line(points[i], points[i + 1], preview_width, preview_color)
            
            # End caps
            if preview_width > 2 and hasattr(renderer, 'draw_circle'):
                cap_radius = preview_width >> 1
                renderer.draw_circle(points[0], cap_radius, preview_color)
                renderer.draw_circle(points[-1], cap_radius, preview_color)