"""
Drawing canvas that manages strokes independently of renderer.
"""

import logging
from typing import List, Optional, Any, Tuple
from .models import Page, Stroke
from .stroke_generator import BasicStrokeGenerator

logger = logging.getLogger(__name__)


class DrawingCanvas:
    """Canvas that manages drawing operations independently of rendering."""
    
    def __init__(self):
        self.page = Page()
        self.stroke_generator = BasicStrokeGenerator()
        self._current_brush_width = 5
        self._current_brush_color = (255, 255, 255)
        self._current_tool = "brush"
        
    def start_drawing(self, x: int, y: int) -> bool:
        """Start drawing at position."""
        return self.stroke_generator.start_stroke(
            x, y, self._current_brush_width, self._current_brush_color, self._current_tool
        )
    
    def continue_drawing(self, x: int, y: int) -> bool:
        """Continue drawing to position."""
        return self.stroke_generator.add_point(x, y)
    
    def end_drawing(self) -> bool:
        """End drawing and add stroke to page."""
        stroke = self.stroke_generator.end_stroke()
        if stroke:
            self.page.strokes.append(stroke)
            logger.debug("Added stroke to page, total strokes: %d", len(self.page.strokes))
            return True
        return False
    
    def clear(self) -> None:
        """Clear the canvas."""
        self.page.clear()
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
    
    def get_strokes(self) -> List[Stroke]:
        """Get all strokes for rendering."""
        return self.page.strokes
    
    def is_drawing(self) -> bool:
        """Check if currently drawing."""
        return self.stroke_generator.state.is_drawing
    
    def get_stroke_count(self) -> int:
        """Get number of strokes."""
        return len(self.page.strokes)
    
    def render(self, renderer) -> None:
        """Render all strokes to the given renderer."""
        try:
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
                            
        except Exception as e:
            logger.error("Error rendering strokes: %s", e)