"""
Enhanced drawing canvas with live rendering support.

CRITICAL FIXES:
1. Live stroke point tracking
2. Real-time stroke preview
3. Enhanced shape support
4. Better stroke generation
"""

import logging
from typing import List, Optional, Any, Tuple
from .models import Page, Stroke, Point
from .stroke_generator import BasicStrokeGenerator

logger = logging.getLogger(__name__)


class DrawingCanvas:
    """Canvas that manages drawing operations with live rendering support."""
    
    def __init__(self):
        self.page = Page()
        self.stroke_generator = BasicStrokeGenerator()
        self._current_brush_width = 5
        self._current_brush_color = (255, 255, 255)
        self._current_tool = "brush"
        
        # Live rendering support - CRITICAL FIX
        self._live_stroke_points = []
        self._is_live_drawing = False
        
    def start_drawing(self, x: int, y: int) -> bool:
        """Start drawing at position with live tracking."""
        success = self.stroke_generator.start_stroke(
            x, y, self._current_brush_width, self._current_brush_color, self._current_tool
        )
        
        if success:
            # Start live tracking - CRITICAL FIX
            self._is_live_drawing = True
            self._live_stroke_points = [(x, y)]
            logger.debug("Started live drawing at (%d, %d)", x, y)
        
        return success
    
    def continue_drawing(self, x: int, y: int) -> bool:
        """Continue drawing to position with live tracking."""
        success = self.stroke_generator.add_point(x, y)
        
        if success and self._is_live_drawing:
            # Add to live tracking - CRITICAL FIX
            self._live_stroke_points.append((x, y))
            
            # Limit live points to prevent memory issues
            if len(self._live_stroke_points) > 1000:
                self._live_stroke_points = self._live_stroke_points[-500:]
        
        return success
    
    def end_drawing(self) -> bool:
        """End drawing and add stroke to page."""
        stroke = self.stroke_generator.end_stroke()
        success = False
        
        if stroke:
            self.page.strokes.append(stroke)
            success = True
            logger.debug("Added stroke to page, total strokes: %d", len(self.page.strokes))
        
        # Clear live tracking - CRITICAL FIX
        self._is_live_drawing = False
        self._live_stroke_points = []
        
        return success
    
    def get_live_stroke_points(self) -> List[Tuple[int, int]]:
        """Get current live stroke points - CRITICAL FIX."""
        return self._live_stroke_points.copy() if self._is_live_drawing else []
    
    def is_live_drawing(self) -> bool:
        """Check if currently in live drawing mode - CRITICAL FIX."""
        return self._is_live_drawing
    
    def clear(self) -> None:
        """Clear the canvas."""
        self.page.clear()
        self._live_stroke_points = []
        self._is_live_drawing = False
        logger.info("Canvas cleared")
    
    def set_brush_width(self, width: int) -> None:
        """Set brush width."""
        if 1 <= width <= 200:
            self._current_brush_width = width
            # Update stroke generator for dynamic width changes
            self.stroke_generator.update_brush_width(width)
    
    def set_brush_color(self, color: Tuple[int, int, int]) -> None:
        """Set brush color."""
        self._current_brush_color = color
    
    def set_tool(self, tool: str) -> None:
        """Set current tool."""
        self._current_tool = tool
        logger.debug("Tool set to: %s", tool)
    
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
        """Render all strokes to the given renderer with live preview."""
        try:
            # Render completed strokes
            for stroke in self.page.strokes:
                if not stroke.points:
                    continue
                    
                # Convert stroke points for rendering
                points = [(int(p.x), int(p.y)) for p in stroke.points]
                
                if len(points) == 1:
                    # Single point - draw as circle
                    if hasattr(renderer, 'draw_circle'):
                        radius = max(1, stroke.width // 2)
                        renderer.draw_circle(points[0], radius, stroke.color)
                elif len(points) > 1:
                    # Multi-point stroke
                    if hasattr(renderer, 'draw_stroke_enhanced'):
                        renderer.draw_stroke_enhanced(points, stroke.color, stroke.width)
                    elif hasattr(renderer, 'draw_line'):
                        # Fallback to line segments
                        for i in range(len(points) - 1):
                            renderer.draw_line(points[i], points[i + 1], stroke.width, stroke.color)
                        
                        # Add end caps for smooth appearance
                        if stroke.width > 2 and hasattr(renderer, 'draw_circle'):
                            cap_radius = max(1, stroke.width // 2)
                            renderer.draw_circle(points[0], cap_radius, stroke.color)
                            renderer.draw_circle(points[-1], cap_radius, stroke.color)
            
            # Render live stroke preview - CRITICAL FIX
            self._render_live_preview(renderer)
                            
        except Exception as e:
            logger.error("Error rendering strokes: %s", e)
    
    def _render_live_preview(self, renderer) -> None:
        """Render live stroke preview - CRITICAL FIX."""
        try:
            if not self._is_live_drawing or len(self._live_stroke_points) < 2:
                return
            
            # Use current brush settings for live preview
            preview_color = self._current_brush_color
            preview_width = self._current_brush_width
            
            # Make eraser preview visible (red instead of black)
            if self._current_tool == 'eraser':
                preview_color = (255, 100, 100)  # Red preview for eraser
            
            # Render live stroke
            if hasattr(renderer, 'draw_stroke_enhanced'):
                renderer.draw_stroke_enhanced(self._live_stroke_points, preview_color, preview_width)
            else:
                # Fallback to line segments
                for i in range(len(self._live_stroke_points) - 1):
                    start = self._live_stroke_points[i]
                    end = self._live_stroke_points[i + 1]
                    renderer.draw_line(start, end, preview_width, preview_color)
                
                # Add end caps
                if preview_width > 2 and hasattr(renderer, 'draw_circle'):
                    cap_radius = max(1, preview_width // 2)
                    renderer.draw_circle(self._live_stroke_points[0], cap_radius, preview_color)
                    renderer.draw_circle(self._live_stroke_points[-1], cap_radius, preview_color)
            
            logger.debug("Rendered live preview with %d points", len(self._live_stroke_points))
            
        except Exception as e:
            logger.error("Error rendering live preview: %s", e)