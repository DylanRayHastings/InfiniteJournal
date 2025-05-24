# core/preview/shape_preview.py (HEAVILY OPTIMIZED)
"""
Non-destructive Shape Preview System - PERFORMANCE OPTIMIZED

Optimizations: __slots__, reduced allocations, faster rendering, cached surfaces.
"""

import logging
import pygame
import time
import math
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class PreviewMode(Enum):
    """Preview rendering modes."""
    NONE = "none"
    OUTLINE = "outline"
    FILLED = "filled"
    DASHED = "dashed"

@dataclass(slots=True)
class PreviewStyle:
    """Style configuration for shape preview - optimized."""
    color: Tuple[int, int, int] = (128, 128, 255)
    width: int = 2
    alpha: int = 128
    mode: PreviewMode = PreviewMode.OUTLINE
    dash_length: int = 10
    animation_speed: float = 0.5

class ShapePreviewRenderer(ABC):
    """Abstract base for shape preview renderers."""
    
    @abstractmethod
    def render_preview(self, surface: pygame.Surface, start: Tuple[float, float], 
                      end: Tuple[float, float], style: PreviewStyle) -> None:
        """Render shape preview to surface."""

class LinePreviewRenderer(ShapePreviewRenderer):
    """Preview renderer for lines - OPTIMIZED."""
    __slots__ = ()
    
    def render_preview(self, surface: pygame.Surface, start: Tuple[float, float], 
                      end: Tuple[float, float], style: PreviewStyle) -> None:
        start_pos = (int(start[0]), int(start[1]))
        end_pos = (int(end[0]), int(end[1]))
        
        if style.mode == PreviewMode.DASHED:
            self._render_dashed_line_fast(surface, start_pos, end_pos, style)
        else:
            pygame.draw.line(surface, style.color, start_pos, end_pos, style.width)
            
    def _render_dashed_line_fast(self, surface: pygame.Surface, start: Tuple[int, int], 
                                end: Tuple[int, int], style: PreviewStyle) -> None:
        """Render dashed line - OPTIMIZED."""
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance == 0:
            return
            
        # Pre-calculate unit vector
        unit_x = dx / distance
        unit_y = dy / distance
        dash_step = style.dash_length * 2
        
        # Optimized dash rendering
        dash_distance = 0
        while dash_distance < distance:
            dash_start_x = start[0] + unit_x * dash_distance
            dash_start_y = start[1] + unit_y * dash_distance
            
            dash_end_distance = min(dash_distance + style.dash_length, distance)
            dash_end_x = start[0] + unit_x * dash_end_distance
            dash_end_y = start[1] + unit_y * dash_end_distance
            
            pygame.draw.line(surface, style.color, 
                           (int(dash_start_x), int(dash_start_y)),
                           (int(dash_end_x), int(dash_end_y)), style.width)
            
            dash_distance += dash_step

class RectanglePreviewRenderer(ShapePreviewRenderer):
    """Preview renderer for rectangles - OPTIMIZED."""
    __slots__ = ()
    
    def render_preview(self, surface: pygame.Surface, start: Tuple[float, float], 
                      end: Tuple[float, float], style: PreviewStyle) -> None:
        # Fast rectangle calculation
        min_x = min(start[0], end[0])
        min_y = min(start[1], end[1])
        width = abs(end[0] - start[0])
        height = abs(end[1] - start[1])
        
        rect = pygame.Rect(int(min_x), int(min_y), int(width), int(height))
        
        if style.mode == PreviewMode.FILLED and width > 0 and height > 0:
            # Create temporary surface for alpha blending
            temp_surface = pygame.Surface((int(width), int(height)), pygame.SRCALPHA)
            fill_color = (*style.color, style.alpha)
            temp_surface.fill(fill_color)
            surface.blit(temp_surface, (int(min_x), int(min_y)))
        
        # Draw outline
        pygame.draw.rect(surface, style.color, rect, style.width)

class CirclePreviewRenderer(ShapePreviewRenderer):
    """Preview renderer for circles - OPTIMIZED."""
    __slots__ = ()
    
    def render_preview(self, surface: pygame.Surface, start: Tuple[float, float], 
                      end: Tuple[float, float], style: PreviewStyle) -> None:
        # Fast circle calculation
        center_x = (start[0] + end[0]) * 0.5
        center_y = (start[1] + end[1]) * 0.5
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        radius = math.sqrt(dx * dx + dy * dy) * 0.5
        
        if radius < 1:
            return
            
        center = (int(center_x), int(center_y))
        radius_int = int(radius)
        
        if style.mode == PreviewMode.FILLED:
            # Create temporary surface for filled circle
            diameter = radius_int * 2
            temp_surface = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
            fill_color = (*style.color, style.alpha)
            pygame.draw.circle(temp_surface, fill_color, (radius_int, radius_int), radius_int)
            surface.blit(temp_surface, (center[0] - radius_int, center[1] - radius_int))
        
        # Draw outline
        pygame.draw.circle(surface, style.color, center, radius_int, style.width)

class TrianglePreviewRenderer(ShapePreviewRenderer):
    """Preview renderer for triangles - OPTIMIZED."""
    __slots__ = ()
    
    def render_preview(self, surface: pygame.Surface, start: Tuple[float, float], 
                      end: Tuple[float, float], style: PreviewStyle) -> None:
        # Fast triangle calculation
        x1, y1 = int(start[0]), int(start[1])
        x2, y2 = int(end[0]), int(end[1])
        x3, y3 = x2, y1  # Right angle point
        
        points = [(x1, y1), (x2, y2), (x3, y3)]
        
        if style.mode == PreviewMode.FILLED:
            # Calculate bounding box
            min_x = min(p[0] for p in points)
            min_y = min(p[1] for p in points)
            max_x = max(p[0] for p in points)
            max_y = max(p[1] for p in points)
            
            width = max_x - min_x + 1
            height = max_y - min_y + 1
            
            if width > 0 and height > 0:
                temp_surface = pygame.Surface((width, height), pygame.SRCALPHA)
                adjusted_points = [(p[0] - min_x, p[1] - min_y) for p in points]
                fill_color = (*style.color, style.alpha)
                pygame.draw.polygon(temp_surface, fill_color, adjusted_points)
                surface.blit(temp_surface, (min_x, min_y))
        
        # Draw outline
        pygame.draw.polygon(surface, style.color, points, style.width)

class ParabolaPreviewRenderer(ShapePreviewRenderer):
    """Preview renderer for parabolas - OPTIMIZED."""
    __slots__ = ()
    
    def render_preview(self, surface: pygame.Surface, start: Tuple[float, float], 
                      end: Tuple[float, float], style: PreviewStyle) -> None:
        x1, y1 = start
        x2, y2 = end
        
        if abs(x2 - x1) < 1:
            # Vertical line fallback
            pygame.draw.line(surface, style.color, 
                           (int(x1), int(y1)), (int(x2), int(y2)), style.width)
            return
        
        # Fast parabola calculation
        h = (x1 + x2) * 0.5  # Vertex x
        k = min(y1, y2) - abs(x2 - x1) * 0.25  # Vertex y
        
        # Calculate coefficient
        dx = x1 - h
        a = (y1 - k) / (dx * dx) if abs(dx) > 0.01 else 1.0
        
        # Generate points efficiently
        steps = max(10, int(abs(x2 - x1) * 0.5))
        x_step = (x2 - x1) / steps
        
        points = []
        for i in range(steps + 1):
            x = x1 + i * x_step
            y = a * (x - h) ** 2 + k
            points.append((int(x), int(y)))
        
        # Draw parabola as connected lines
        if len(points) > 1:
            for i in range(len(points) - 1):
                pygame.draw.line(surface, style.color, points[i], points[i + 1], style.width)

class ShapePreviewSystem:
    """Central system for managing shape previews - HEAVILY OPTIMIZED."""
    __slots__ = ('width', 'height', 'active_preview', 'preview_start', 'preview_end',
                 'preview_tool', 'preview_style', 'preview_surface', 'renderers',
                 'animation_time', 'last_update_time', '_cached_surfaces')
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        # Preview state
        self.active_preview = False
        self.preview_start = None
        self.preview_end = None
        self.preview_tool = None
        self.preview_style = PreviewStyle()
        
        # Preview surface
        self.preview_surface = None
        self._create_preview_surface()
        
        # Shape renderers - pre-instantiated
        self.renderers = {
            'line': LinePreviewRenderer(),
            'rect': RectanglePreviewRenderer(),
            'circle': CirclePreviewRenderer(),
            'triangle': TrianglePreviewRenderer(),
            'parabola': ParabolaPreviewRenderer()
        }
        
        # Animation state
        self.animation_time = 0.0
        self.last_update_time = time.time()
        
        # Surface cache for performance
        self._cached_surfaces = {}
        
    def _create_preview_surface(self):
        """Create transparent preview surface - optimized."""
        try:
            self.preview_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            self.preview_surface.set_alpha(255)
        except Exception as e:
            logger.error("Failed to create preview surface: %s", e)
            
    def start_preview(self, tool_name: str, start_x: float, start_y: float, 
                     style: Optional[PreviewStyle] = None) -> None:
        """Start shape preview - optimized."""
        self.preview_tool = tool_name
        self.preview_start = (start_x, start_y)
        self.preview_end = (start_x, start_y)
        self.preview_style = style or PreviewStyle()
        self.active_preview = True
        
        # Clear preview surface efficiently
        if self.preview_surface:
            self.preview_surface.fill((0, 0, 0, 0))
            
    def update_preview(self, end_x: float, end_y: float) -> None:
        """Update preview end position - optimized."""
        if not self.active_preview:
            return
            
        self.preview_end = (end_x, end_y)
        self._render_preview_fast()
                
    def end_preview(self) -> None:
        """End shape preview - optimized."""
        self.active_preview = False
        self.preview_tool = None
        self.preview_start = None
        self.preview_end = None
        
        # Clear surface
        if self.preview_surface:
            self.preview_surface.fill((0, 0, 0, 0))
            
    def _render_preview_fast(self) -> None:
        """Render preview - HEAVILY OPTIMIZED."""
        if (not self.active_preview or not self.preview_surface or 
            not self.preview_start or not self.preview_end or not self.preview_tool):
            return
            
        # Clear surface
        self.preview_surface.fill((0, 0, 0, 0))
        
        # Get renderer
        renderer = self.renderers.get(self.preview_tool)
        if not renderer:
            return
        
        # Update animation efficiently
        current_time = time.time()
        dt = current_time - self.last_update_time
        self.animation_time += dt * self.preview_style.animation_speed
        self.last_update_time = current_time
        
        # Get animated style
        animated_style = self._get_animated_style_fast()
        
        # Render preview
        renderer.render_preview(self.preview_surface, self.preview_start, 
                              self.preview_end, animated_style)
                              
    def _get_animated_style_fast(self) -> PreviewStyle:
        """Get animated preview style - optimized."""
        # Fast animation calculation
        pulse = math.sin(self.animation_time * 2) * 0.3 + 0.7  # 0.4 to 1.0
        
        # Create animated style efficiently
        animated = PreviewStyle(
            color=self.preview_style.color,
            width=self.preview_style.width,
            alpha=int(self.preview_style.alpha * pulse),
            mode=self.preview_style.mode,
            dash_length=self.preview_style.dash_length,
            animation_speed=self.preview_style.animation_speed
        )
        
        return animated
            
    def render_to_screen(self, target_surface: pygame.Surface) -> None:
        """Render preview to screen - optimized."""
        if (not self.active_preview or not self.preview_surface or not target_surface):
            return
                
        # Fast alpha blit
        target_surface.blit(self.preview_surface, (0, 0), 
                          special_flags=pygame.BLEND_ALPHA_SDL2)
                          
    def set_preview_style(self, style: PreviewStyle) -> None:
        """Set preview style."""
        self.preview_style = style
            
    def is_preview_active(self) -> bool:
        """Check if preview is active."""
        return self.active_preview
            
    def get_preview_bounds(self) -> Optional[Tuple[int, int, int, int]]:
        """Get preview bounds - optimized."""
        if not self.active_preview or not self.preview_start or not self.preview_end:
            return None
            
        min_x = min(self.preview_start[0], self.preview_end[0])
        min_y = min(self.preview_start[1], self.preview_end[1])
        max_x = max(self.preview_start[0], self.preview_end[0])
        max_y = max(self.preview_start[1], self.preview_end[1])
        
        # Add padding
        padding = self.preview_style.width + 2
        
        return (int(min_x - padding), int(min_y - padding), 
               int(max_x - min_x + 2 * padding), int(max_y - min_y + 2 * padding))
            
    def resize(self, new_width: int, new_height: int) -> None:
        """Resize preview system."""
        self.width = new_width
        self.height = new_height
        self._create_preview_surface()
            
    def clear_preview(self) -> None:
        """Clear current preview."""
        if self.preview_surface:
            self.preview_surface.fill((0, 0, 0, 0))

class PreviewIntegrationHelper:
    """Helper for integrating preview system - OPTIMIZED."""
    __slots__ = ('preview_system', 'tool_map')
    
    def __init__(self, preview_system: ShapePreviewSystem):
        self.preview_system = preview_system
        self.tool_map = {
            'line': 'line',
            'rect': 'rect', 
            'rectangle': 'rect',
            'circle': 'circle',
            'triangle': 'triangle',
            'parabola': 'parabola',
            'curve': 'parabola'
        }
        
    def should_show_preview(self, tool_name: str) -> bool:
        """Check if tool should show preview."""
        return tool_name.lower() in self.tool_map
        
    def start_tool_preview(self, tool_name: str, x: float, y: float, 
                          width: int = 2, color: Tuple[int, int, int] = (128, 128, 255)) -> None:
        """Start preview for tool."""
        preview_tool = self.tool_map.get(tool_name.lower())
        if preview_tool:
            style = PreviewStyle(color=color, width=width, alpha=128)
            self.preview_system.start_preview(preview_tool, x, y, style)
            
    def update_tool_preview(self, x: float, y: float) -> None:
        """Update tool preview."""
        self.preview_system.update_preview(x, y)
        
    def end_tool_preview(self) -> None:
        """End tool preview."""
        self.preview_system.end_preview()
        
    def render_preview(self, target_surface: pygame.Surface) -> None:
        """Render preview."""
        self.preview_system.render_to_screen(target_surface)