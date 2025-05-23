# core/preview/shape_preview.py (NEW FILE - Non-destructive shape preview system)
"""
Non-destructive Shape Preview System

Provides real-time shape preview without contaminating permanent drawing data.
Uses separate preview surface with alpha blending for temporary overlays.

CRITICAL FIX: Eliminates gray line artifacts by using proper surface management.
"""

import logging
import pygame
import threading
import time
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


@dataclass
class PreviewStyle:
    """Style configuration for shape preview."""
    color: Tuple[int, int, int] = (128, 128, 255)  # Light blue instead of gray
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
        pass


class LinePreviewRenderer(ShapePreviewRenderer):
    """Preview renderer for lines."""
    
    def render_preview(self, surface: pygame.Surface, start: Tuple[float, float], 
                      end: Tuple[float, float], style: PreviewStyle) -> None:
        try:
            start_pos = (int(start[0]), int(start[1]))
            end_pos = (int(end[0]), int(end[1]))
            
            if style.mode == PreviewMode.DASHED:
                self._render_dashed_line(surface, start_pos, end_pos, style)
            else:
                pygame.draw.line(surface, style.color, start_pos, end_pos, style.width)
                
        except Exception as e:
            logger.error("Error rendering line preview: %s", e)
            
    def _render_dashed_line(self, surface: pygame.Surface, start: Tuple[int, int], 
                           end: Tuple[int, int], style: PreviewStyle) -> None:
        """Render dashed line preview."""
        try:
            import math
            
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance == 0:
                return
                
            # Normalize direction
            unit_x = dx / distance
            unit_y = dy / distance
            
            # Draw dashes
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
                
                dash_distance += style.dash_length * 2  # Gap between dashes
                
        except Exception as e:
            logger.error("Error rendering dashed line: %s", e)


class RectanglePreviewRenderer(ShapePreviewRenderer):
    """Preview renderer for rectangles."""
    
    def render_preview(self, surface: pygame.Surface, start: Tuple[float, float], 
                      end: Tuple[float, float], style: PreviewStyle) -> None:
        try:
            # Calculate rectangle bounds
            min_x = min(start[0], end[0])
            min_y = min(start[1], end[1])
            width = abs(end[0] - start[0])
            height = abs(end[1] - start[1])
            
            rect = pygame.Rect(int(min_x), int(min_y), int(width), int(height))
            
            if style.mode == PreviewMode.FILLED:
                # Create transparent surface for filled rectangle
                temp_surface = pygame.Surface((int(width), int(height)), pygame.SRCALPHA)
                fill_color = (*style.color, style.alpha)
                temp_surface.fill(fill_color)
                surface.blit(temp_surface, (int(min_x), int(min_y)))
                
            # Always draw outline
            pygame.draw.rect(surface, style.color, rect, style.width)
            
        except Exception as e:
            logger.error("Error rendering rectangle preview: %s", e)


class CirclePreviewRenderer(ShapePreviewRenderer):
    """Preview renderer for circles."""
    
    def render_preview(self, surface: pygame.Surface, start: Tuple[float, float], 
                      end: Tuple[float, float], style: PreviewStyle) -> None:
        try:
            import math
            
            # Calculate circle center and radius
            center_x = (start[0] + end[0]) / 2
            center_y = (start[1] + end[1]) / 2
            radius = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2) / 2
            
            if radius < 1:
                return
                
            center = (int(center_x), int(center_y))
            radius = int(radius)
            
            if style.mode == PreviewMode.FILLED:
                # Create transparent surface for filled circle
                temp_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                fill_color = (*style.color, style.alpha)
                pygame.draw.circle(temp_surface, fill_color, (radius, radius), radius)
                surface.blit(temp_surface, (center[0] - radius, center[1] - radius))
                
            # Always draw outline
            pygame.draw.circle(surface, style.color, center, radius, style.width)
            
        except Exception as e:
            logger.error("Error rendering circle preview: %s", e)


class TrianglePreviewRenderer(ShapePreviewRenderer):
    """Preview renderer for triangles."""
    
    def render_preview(self, surface: pygame.Surface, start: Tuple[float, float], 
                      end: Tuple[float, float], style: PreviewStyle) -> None:
        try:
            # Create right angle triangle
            x1, y1 = start
            x2, y2 = end
            x3, y3 = x2, y1  # Right angle point
            
            points = [(int(x1), int(y1)), (int(x2), int(y2)), (int(x3), int(y3))]
            
            if style.mode == PreviewMode.FILLED:
                # Create transparent surface for filled triangle
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
                
            # Always draw outline
            pygame.draw.polygon(surface, style.color, points, style.width)
            
        except Exception as e:
            logger.error("Error rendering triangle preview: %s", e)


class ParabolaPreviewRenderer(ShapePreviewRenderer):
    """Preview renderer for parabolas."""
    
    def render_preview(self, surface: pygame.Surface, start: Tuple[float, float], 
                      end: Tuple[float, float], style: PreviewStyle) -> None:
        try:
            import math
            
            # Generate parabola points
            x1, y1 = start
            x2, y2 = end
            
            if abs(x2 - x1) < 1:
                # Vertical line fallback
                pygame.draw.line(surface, style.color, 
                               (int(x1), int(y1)), (int(x2), int(y2)), style.width)
                return
                
            # Calculate parabola parameters
            # Form: y = a(x - h)² + k where (h, k) is vertex
            h = (x1 + x2) / 2  # Vertex x-coordinate (midpoint)
            k = min(y1, y2) - abs(x2 - x1) / 4  # Vertex y-coordinate (below midpoint)
            
            # Calculate 'a' coefficient
            if abs(x1 - h) > 0.01:  # Avoid division by zero
                a = (y1 - k) / ((x1 - h) ** 2)
            else:
                a = 1.0
                
            # Generate points along parabola
            points = []
            steps = max(10, int(abs(x2 - x1) / 2))  # Adaptive resolution
            
            for i in range(steps + 1):
                t = i / steps
                x = x1 + t * (x2 - x1)
                y = a * (x - h) ** 2 + k
                points.append((int(x), int(y)))
                
            # Draw parabola as connected lines
            if len(points) > 1:
                for i in range(len(points) - 1):
                    pygame.draw.line(surface, style.color, points[i], points[i + 1], style.width)
                    
        except Exception as e:
            logger.error("Error rendering parabola preview: %s", e)


class ShapePreviewSystem:
    """
    Central system for managing shape previews.
    
    Provides non-destructive real-time preview of shapes being drawn
    without affecting permanent drawing data.
    """
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        # Preview state
        self.active_preview = None
        self.preview_start = None
        self.preview_end = None
        self.preview_tool = None
        self.preview_style = PreviewStyle()
        
        # Preview surface
        self.preview_surface = None
        self._create_preview_surface()
        
        # Shape renderers
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
        
        # Threading
        self._lock = threading.Lock()
        
        logger.info("Shape preview system initialized")
        
    def _create_preview_surface(self):
        """Create transparent preview surface."""
        try:
            self.preview_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            self.preview_surface.set_alpha(255)  # Full alpha for blending control
        except Exception as e:
            logger.error("Failed to create preview surface: %s", e)
            
    def start_preview(self, tool_name: str, start_x: float, start_y: float, 
                     style: Optional[PreviewStyle] = None) -> None:
        """Start shape preview."""
        try:
            with self._lock:
                self.preview_tool = tool_name
                self.preview_start = (start_x, start_y)
                self.preview_end = (start_x, start_y)
                self.preview_style = style or PreviewStyle()
                self.active_preview = True
                
                # Clear preview surface
                if self.preview_surface:
                    self.preview_surface.fill((0, 0, 0, 0))  # Transparent
                    
                logger.debug("Started preview for tool: %s at (%.1f, %.1f)", 
                           tool_name, start_x, start_y)
                           
        except Exception as e:
            logger.error("Error starting preview: %s", e)
            
    def update_preview(self, end_x: float, end_y: float) -> None:
        """Update preview end position."""
        try:
            with self._lock:
                if not self.active_preview:
                    return
                    
                self.preview_end = (end_x, end_y)
                self._render_preview()
                
        except Exception as e:
            logger.error("Error updating preview: %s", e)
            
    def end_preview(self) -> None:
        """End shape preview."""
        try:
            with self._lock:
                self.active_preview = False
                self.preview_tool = None
                self.preview_start = None
                self.preview_end = None
                
                # Clear preview surface
                if self.preview_surface:
                    self.preview_surface.fill((0, 0, 0, 0))
                    
                logger.debug("Ended shape preview")
                
        except Exception as e:
            logger.error("Error ending preview: %s", e)
            
    def _render_preview(self) -> None:
        """Render current preview to surface."""
        try:
            if (not self.active_preview or not self.preview_surface or 
                not self.preview_start or not self.preview_end or not self.preview_tool):
                return
                
            # Clear preview surface
            self.preview_surface.fill((0, 0, 0, 0))
            
            # Get appropriate renderer
            renderer = self.renderers.get(self.preview_tool)
            if not renderer:
                logger.warning("No renderer for tool: %s", self.preview_tool)
                return
                
            # Update animation
            current_time = time.time()
            self.animation_time += (current_time - self.last_update_time) * self.preview_style.animation_speed
            self.last_update_time = current_time
            
            # Animate preview color
            animated_style = self._get_animated_style()
            
            # Render preview
            renderer.render_preview(self.preview_surface, self.preview_start, 
                                  self.preview_end, animated_style)
                                  
        except Exception as e:
            logger.error("Error rendering preview: %s", e)
            
    def _get_animated_style(self) -> PreviewStyle:
        """Get animated preview style."""
        try:
            import math
            
            # Create copy of style
            animated = PreviewStyle(
                color=self.preview_style.color,
                width=self.preview_style.width,
                alpha=self.preview_style.alpha,
                mode=self.preview_style.mode,
                dash_length=self.preview_style.dash_length,
                animation_speed=self.preview_style.animation_speed
            )
            
            # Animate alpha for pulsing effect
            pulse = math.sin(self.animation_time * 2) * 0.3 + 0.7  # 0.4 to 1.0
            animated.alpha = int(self.preview_style.alpha * pulse)
            
            return animated
            
        except Exception as e:
            logger.error("Error creating animated style: %s", e)
            return self.preview_style
            
    def render_to_screen(self, target_surface: pygame.Surface) -> None:
        """Render preview surface to target screen surface."""
        try:
            if (not self.active_preview or not self.preview_surface or 
                not target_surface):
                return
                
            with self._lock:
                # Blit preview surface with alpha blending
                target_surface.blit(self.preview_surface, (0, 0), 
                                  special_flags=pygame.BLEND_ALPHA_SDL2)
                                  
        except Exception as e:
            logger.error("Error rendering preview to screen: %s", e)
            
    def set_preview_style(self, style: PreviewStyle) -> None:
        """Set preview style."""
        try:
            with self._lock:
                self.preview_style = style
                logger.debug("Preview style updated")
                
        except Exception as e:
            logger.error("Error setting preview style: %s", e)
            
    def is_preview_active(self) -> bool:
        """Check if preview is currently active."""
        with self._lock:
            return bool(self.active_preview)
            
    def get_preview_bounds(self) -> Optional[Tuple[int, int, int, int]]:
        """Get bounding rectangle of current preview."""
        try:
            with self._lock:
                if not self.active_preview or not self.preview_start or not self.preview_end:
                    return None
                    
                min_x = min(self.preview_start[0], self.preview_end[0])
                min_y = min(self.preview_start[1], self.preview_end[1])
                max_x = max(self.preview_start[0], self.preview_end[0])
                max_y = max(self.preview_start[1], self.preview_end[1])
                
                # Add padding for line width
                padding = self.preview_style.width + 2
                
                return (int(min_x - padding), int(min_y - padding), 
                       int(max_x - min_x + 2 * padding), int(max_y - min_y + 2 * padding))
                       
        except Exception as e:
            logger.error("Error getting preview bounds: %s", e)
            return None
            
    def resize(self, new_width: int, new_height: int) -> None:
        """Resize preview system."""
        try:
            with self._lock:
                self.width = new_width
                self.height = new_height
                
                # Recreate preview surface
                self._create_preview_surface()
                
                logger.debug("Preview system resized to %dx%d", new_width, new_height)
                
        except Exception as e:
            logger.error("Error resizing preview system: %s", e)
            
    def clear_preview(self) -> None:
        """Clear current preview without ending it."""
        try:
            with self._lock:
                if self.preview_surface:
                    self.preview_surface.fill((0, 0, 0, 0))
                    
        except Exception as e:
            logger.error("Error clearing preview: %s", e)
            
    def get_preview_info(self) -> Dict[str, Any]:
        """Get information about current preview."""
        try:
            with self._lock:
                return {
                    'active': self.active_preview,
                    'tool': self.preview_tool,
                    'start': self.preview_start,
                    'end': self.preview_end,
                    'style': {
                        'color': self.preview_style.color,
                        'width': self.preview_style.width,
                        'alpha': self.preview_style.alpha,
                        'mode': self.preview_style.mode.value
                    },
                    'animation_time': self.animation_time
                }
        except Exception as e:
            logger.error("Error getting preview info: %s", e)
            return {}


class PreviewIntegrationHelper:
    """Helper class for integrating preview system with existing codebase."""
    
    def __init__(self, preview_system: ShapePreviewSystem):
        self.preview_system = preview_system
        self.tool_to_preview_map = {
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
        return tool_name.lower() in self.tool_to_preview_map
        
    def start_tool_preview(self, tool_name: str, x: float, y: float, 
                          width: int = 2, color: Tuple[int, int, int] = (128, 128, 255)) -> None:
        """Start preview for specific tool."""
        preview_tool = self.tool_to_preview_map.get(tool_name.lower())
        if preview_tool:
            style = PreviewStyle(color=color, width=width, alpha=128)
            self.preview_system.start_preview(preview_tool, x, y, style)
            
    def update_tool_preview(self, x: float, y: float) -> None:
        """Update tool preview position."""
        self.preview_system.update_preview(x, y)
        
    def end_tool_preview(self) -> None:
        """End tool preview."""
        self.preview_system.end_preview()
        
    def render_preview(self, target_surface: pygame.Surface) -> None:
        """Render preview to target surface."""
        self.preview_system.render_to_screen(target_surface)