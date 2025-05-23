# core/rendering/layered_system.py (NEW FILE - Core layered rendering architecture)
"""
Layered Rendering System for InfiniteJournal

Implements three-layer rendering architecture:
- Background Layer (z-index: 0): Grid and static elements
- Drawing Layer (z-index: 1): User strokes and shapes  
- UI Layer (z-index: 2): Hotbar and interface overlays

CRITICAL FIX: Prevents eraser from affecting background grid elements.
"""

import logging
import time
import pygame
import threading
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import IntEnum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LayerType(IntEnum):
    """Layer types with z-ordering."""
    BACKGROUND = 0
    DRAWING = 1  
    UI = 2


@dataclass
class LayerConfig:
    """Configuration for a rendering layer."""
    name: str
    z_index: int
    alpha: int = 255
    blend_mode: int = pygame.BLEND_ALPHA_SDL2
    dirty_tracking: bool = True
    caching_enabled: bool = True


class RenderableObject(ABC):
    """Base class for objects that can be rendered to a layer."""
    
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.visible = True
        self.dirty = True
        
    @abstractmethod
    def render(self, surface: pygame.Surface) -> None:
        """Render this object to the given surface."""
        pass
        
    def get_bounds(self) -> Tuple[int, int, int, int]:
        """Get bounding rectangle (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)
        
    def mark_dirty(self) -> None:
        """Mark this object as needing re-render."""
        self.dirty = True


class GridBackground(RenderableObject):
    """CRITICAL: Fixed grid background that cannot be erased."""
    
    def __init__(self, width: int, height: int, spacing: int = 40, color: Tuple[int, int, int] = (30, 30, 30)):
        super().__init__(0, 0, width, height)
        self.spacing = spacing
        self.color = color
        self.infinite_bounds = (-10000, -10000, 20000, 20000)
        
    def render(self, surface: pygame.Surface) -> None:
        """Render infinite grid with FIXED viewport access."""
        try:
            # CRITICAL FIX: Get viewport from layer instead of surface
            viewport_x = 0
            viewport_y = 0
            
            # Try to get viewport from the layer (passed via special attribute)
            if hasattr(surface, '_layer_viewport'):
                viewport_x, viewport_y = surface._layer_viewport
            
            # Calculate grid start positions
            start_x = (viewport_x // self.spacing) * self.spacing - self.spacing
            start_y = (viewport_y // self.spacing) * self.spacing - self.spacing
            
            # Render vertical lines
            for x in range(start_x, start_x + self.width + self.spacing * 2, self.spacing):
                try:
                    screen_x = x - viewport_x
                    if -100 <= screen_x <= self.width + 100:
                        pygame.draw.line(surface, self.color, (screen_x, 0), (screen_x, self.height), 1)
                except Exception:
                    continue
                    
            # Render horizontal lines
            for y in range(start_y, start_y + self.height + self.spacing * 2, self.spacing):
                try:
                    screen_y = y - viewport_y
                    if -100 <= screen_y <= self.height + 100:
                        pygame.draw.line(surface, self.color, (0, screen_y), (self.width, screen_y), 1)
                except Exception:
                    continue
                    
        except Exception as e:
            logger.error("Error rendering grid background: %s", e)


class StrokeObject(RenderableObject):
    """Stroke rendering object for drawing layer."""
    
    def __init__(self, points: List[Tuple[int, int]], color: Tuple[int, int, int], width: int):
        if not points:
            super().__init__(0, 0, 0, 0)
            return
            
        # Calculate bounds
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        super().__init__(min_x - width, min_y - width, max_x - min_x + 2*width, max_y - min_y + 2*width)
        
        self.points = points
        self.color = color
        self.stroke_width = width
        
    def render(self, surface: pygame.Surface) -> None:
        """Render stroke with anti-aliasing."""
        try:
            if len(self.points) < 2:
                if self.points:
                    # Single point
                    x, y = self.points[0]
                    radius = max(1, self.stroke_width // 2)
                    pygame.draw.circle(surface, self.color, (int(x), int(y)), radius)
                return
                
            # Multi-point stroke with smooth rendering
            for i in range(len(self.points) - 1):
                start = (int(self.points[i][0]), int(self.points[i][1]))
                end = (int(self.points[i + 1][0]), int(self.points[i + 1][1]))
                
                try:
                    pygame.draw.line(surface, self.color, start, end, max(1, self.stroke_width))
                except Exception:
                    continue
                    
            # Add end caps for smooth appearance
            if self.stroke_width > 2:
                cap_radius = max(1, self.stroke_width // 2)
                start_pos = (int(self.points[0][0]), int(self.points[0][1]))
                end_pos = (int(self.points[-1][0]), int(self.points[-1][1]))
                
                try:
                    pygame.draw.circle(surface, self.color, start_pos, cap_radius)
                    pygame.draw.circle(surface, self.color, end_pos, cap_radius)
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error("Error rendering stroke: %s", e)


class UIElement(RenderableObject):
    """UI element for interface layer."""
    
    def __init__(self, x: int, y: int, width: int, height: int, background_color: Tuple[int, int, int] = (60, 60, 60)):
        super().__init__(x, y, width, height)
        self.background_color = background_color
        self.text_elements = []
        
    def add_text(self, text: str, x: int, y: int, font_size: int = 12, color: Tuple[int, int, int] = (255, 255, 255)):
        """Add text element to this UI component."""
        self.text_elements.append({
            'text': text,
            'x': x,
            'y': y,
            'font_size': font_size,
            'color': color
        })
        
    def render(self, surface: pygame.Surface) -> None:
        """Render UI element with background and text."""
        try:
            # Draw background
            bg_rect = pygame.Rect(self.x, self.y, self.width, self.height)
            pygame.draw.rect(surface, self.background_color, bg_rect)
            
            # Draw border
            pygame.draw.rect(surface, (100, 100, 100), bg_rect, 1)
            
            # Draw text elements
            font = pygame.font.Font(None, 24)
            for text_elem in self.text_elements:
                try:
                    text_surface = font.render(text_elem['text'], True, text_elem['color'])
                    surface.blit(text_surface, (self.x + text_elem['x'], self.y + text_elem['y']))
                except Exception:
                    continue
                    
        except Exception as e:
            logger.error("Error rendering UI element: %s", e)


class RenderLayer:
    """Individual rendering layer with surface management."""
    
    def _render_to_layer_surface(self, viewport_offset: Tuple[int, int]) -> None:
        """Render all objects to layer surface with FIXED viewport passing."""
        try:
            # Clear surface
            if self.config.alpha < 255:
                self._surface.fill((0, 0, 0, 0))  # Transparent
            else:
                self._surface.fill((0, 0, 0))  # Black
                
            # CRITICAL FIX: Set viewport via special attribute instead of direct assignment
            if self.config.name == "background":
                self._surface._layer_viewport = viewport_offset
                
            # Render all visible objects
            for obj in self.objects:
                if obj.visible:
                    try:
                        obj.render(self._surface)
                        obj.dirty = False
                    except Exception as e:
                        logger.error("Error rendering object: %s", e)
                        continue
                        
        except Exception as e:
            logger.error("Error rendering to layer surface: %s", e)

class LayeredRenderingSystem:
    """Main layered rendering system manager."""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.layers: Dict[LayerType, RenderLayer] = {}
        self.viewport_offset = [0, 0]  # For panning
        self._lock = threading.Lock()
        
        # Create default layers
        self._initialize_layers()
        
    def _initialize_layers(self):
        """Initialize the three main rendering layers."""
        try:
            # Background layer - for grid and static elements
            bg_config = LayerConfig("background", LayerType.BACKGROUND, alpha=255, caching_enabled=True)
            self.layers[LayerType.BACKGROUND] = RenderLayer(bg_config, self.width, self.height)
            
            # Drawing layer - for user strokes and shapes
            draw_config = LayerConfig("drawing", LayerType.DRAWING, alpha=255, caching_enabled=True)  
            self.layers[LayerType.DRAWING] = RenderLayer(draw_config, self.width, self.height)
            
            # UI layer - for interface elements with transparency
            ui_config = LayerConfig("ui", LayerType.UI, alpha=240, blend_mode=pygame.BLEND_ALPHA_SDL2)
            self.layers[LayerType.UI] = RenderLayer(ui_config, self.width, self.height)
            
            # Add fixed grid to background layer
            grid = GridBackground(self.width, self.height)
            self.layers[LayerType.BACKGROUND].add_object(grid)
            
            logger.info("Layered rendering system initialized")
            
        except Exception as e:
            logger.error("Failed to initialize layers: %s", e)
            
    def add_stroke(self, points: List[Tuple[int, int]], color: Tuple[int, int, int], width: int) -> None:
        """Add stroke to drawing layer."""
        try:
            stroke = StrokeObject(points, color, width)
            self.layers[LayerType.DRAWING].add_object(stroke)
        except Exception as e:
            logger.error("Error adding stroke: %s", e)
            
    def add_ui_element(self, element: UIElement) -> None:
        """Add UI element to UI layer."""
        try:
            self.layers[LayerType.UI].add_object(element)
        except Exception as e:
            logger.error("Error adding UI element: %s", e)
            
    def clear_drawing_layer(self) -> None:
        """Clear only the drawing layer, preserving grid."""
        try:
            self.layers[LayerType.DRAWING].clear_objects()
            logger.info("Drawing layer cleared, grid preserved")
        except Exception as e:
            logger.error("Error clearing drawing layer: %s", e)
            
    def erase_at_position(self, x: int, y: int, radius: int) -> None:
        """CRITICAL: Erase only affects drawing layer, not background grid."""
        try:
            drawing_layer = self.layers[LayerType.DRAWING]
            
            with drawing_layer._lock:
                objects_to_remove = []
                
                for obj in drawing_layer.objects:
                    if isinstance(obj, StrokeObject):
                        # Check if stroke intersects with erase area
                        if self._stroke_intersects_circle(obj, x, y, radius):
                            objects_to_remove.append(obj)
                            
                # Remove intersecting strokes
                for obj in objects_to_remove:
                    drawing_layer.remove_object(obj)
                    
                logger.debug("Erased %d objects at (%d, %d)", len(objects_to_remove), x, y)
                
        except Exception as e:
            logger.error("Error erasing at position: %s", e)
            
    def _stroke_intersects_circle(self, stroke: StrokeObject, cx: int, cy: int, radius: int) -> bool:
        """Check if stroke intersects with erase circle."""
        try:
            for point in stroke.points:
                px, py = point
                distance_sq = (px - cx) ** 2 + (py - cy) ** 2
                if distance_sq <= radius ** 2:
                    return True
            return False
        except Exception:
            return False
            
    def pan_viewport(self, dx: int, dy: int) -> None:
        """Pan the viewport without affecting object positions."""
        try:
            self.viewport_offset[0] += dx
            self.viewport_offset[1] += dy
            
            # Mark layers as needing re-render
            for layer in self.layers.values():
                layer._mark_dirty()
                
            logger.debug("Viewport panned by (%d, %d), new offset: (%d, %d)", 
                        dx, dy, self.viewport_offset[0], self.viewport_offset[1])
                        
        except Exception as e:
            logger.error("Error panning viewport: %s", e)
            
    def render_all(self, target_surface: pygame.Surface) -> None:
        """Render all layers in z-order to target surface."""
        try:
            # Clear target surface
            target_surface.fill((0, 0, 0))
            
            # Render layers in z-order
            layer_order = [LayerType.BACKGROUND, LayerType.DRAWING, LayerType.UI]
            
            for layer_type in layer_order:
                if layer_type in self.layers:
                    try:
                        self.layers[layer_type].render(target_surface, tuple(self.viewport_offset))
                    except Exception as e:
                        logger.error("Error rendering layer %s: %s", layer_type.name, e)
                        continue
                        
        except Exception as e:
            logger.error("Critical error in render_all: %s", e)
            
    def resize(self, new_width: int, new_height: int) -> None:
        """Resize the rendering system."""
        try:
            self.width = new_width
            self.height = new_height
            
            # Recreate all layers
            self._initialize_layers()
            
        except Exception as e:
            logger.error("Error resizing rendering system: %s", e)
            
    def get_layer_stats(self) -> Dict[str, Any]:
        """Get statistics about layer usage."""
        try:
            stats = {}
            for layer_type, layer in self.layers.items():
                stats[layer_type.name] = {
                    'object_count': len(layer.objects),
                    'cache_valid': layer._cache_valid,
                    'config': layer.config.__dict__
                }
            return stats
        except Exception as e:
            logger.error("Error getting layer stats: %s", e)
            return {}


# Integration helper for existing codebase
class LayeredPygameAdapter:
    """Adapter to integrate layered rendering with existing pygame adapter."""
    
    def __init__(self, pygame_engine):
        self.engine = pygame_engine
        self.rendering_system = None
        
    def initialize(self, width: int, height: int):
        """Initialize layered rendering system."""
        try:
            self.rendering_system = LayeredRenderingSystem(width, height)
            logger.info("Layered pygame adapter initialized")
        except Exception as e:
            logger.error("Failed to initialize layered adapter: %s", e)
            
    def draw_stroke_layered(self, points: List[Tuple[int, int]], color: Tuple[int, int, int], width: int):
        """Draw stroke using layered system."""
        if self.rendering_system:
            self.rendering_system.add_stroke(points, color, width)
            
    def erase_layered(self, x: int, y: int, radius: int):
        """Erase using layered system (affects only drawing layer)."""
        if self.rendering_system:
            self.rendering_system.erase_at_position(x, y, radius)
            
    def clear_canvas_layered(self):
        """Clear only drawing layer, preserve grid."""
        if self.rendering_system:
            self.rendering_system.clear_drawing_layer()
            
    def pan_layered(self, dx: int, dy: int):
        """Pan viewport."""
        if self.rendering_system:
            self.rendering_system.pan_viewport(dx, dy)
            
    def render_layered(self):
        """Render all layers."""
        if self.rendering_system and hasattr(self.engine, 'screen'):
            self.rendering_system.render_all(self.engine.screen)

class LayeredRenderingSystem:
    """Main layered rendering system manager."""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.layers: Dict[LayerType, RenderLayer] = {}
        self.viewport_offset = [0, 0]
        self._lock = threading.Lock()
        
        # CRITICAL FIX: Add error throttling
        self._last_error_time = {}
        self._error_throttle_interval = 1.0  # Max 1 error per second per type
        
        self._initialize_layers()
        
    def _log_throttled_error(self, error_key: str, message: str) -> None:
        """Log error with throttling to prevent spam."""
        current_time = time.time()
        last_time = self._last_error_time.get(error_key, 0)
        
        if current_time - last_time >= self._error_throttle_interval:
            logger.error(message)
            self._last_error_time[error_key] = current_time
