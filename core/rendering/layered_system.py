# core/rendering/layered_system.py (HEAVILY OPTIMIZED)
"""
Layered Rendering System - PERFORMANCE OPTIMIZED

Optimizations: __slots__, fast rendering, cached surfaces, reduced allocations.
Three-layer architecture: Background -> Drawing -> UI
"""

import logging
import time
import pygame
import threading
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import IntEnum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class LayerType(IntEnum):
    """Layer types with z-ordering."""
    BACKGROUND = 0
    DRAWING = 1  
    UI = 2

@dataclass(slots=True)
class LayerConfig:
    """Configuration for a rendering layer - optimized."""
    name: str
    z_index: int
    alpha: int = 255
    blend_mode: int = pygame.BLEND_ALPHA_SDL2
    dirty_tracking: bool = True
    caching_enabled: bool = True

class RenderableObject(ABC):
    """Base class for renderable objects - OPTIMIZED."""
    __slots__ = ('x', 'y', 'width', 'height', 'visible', 'dirty')
    
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.visible = True
        self.dirty = True
        
    @abstractmethod
    def render(self, surface: pygame.Surface) -> None:
        """Render this object to surface."""
        
    def get_bounds(self) -> Tuple[int, int, int, int]:
        """Get bounding rectangle."""
        return (self.x, self.y, self.width, self.height)
        
    def mark_dirty(self) -> None:
        """Mark as needing re-render."""
        self.dirty = True

class GridBackground(RenderableObject):
    """Fixed grid background - HEAVILY OPTIMIZED."""
    __slots__ = ('spacing', 'color', '_line_cache', '_viewport_x', '_viewport_y')
    
    def __init__(self, width: int, height: int, spacing: int = 40, color: Tuple[int, int, int] = (30, 30, 30)):
        super().__init__(0, 0, width, height)
        self.spacing = spacing
        self.color = color
        self._line_cache = {}
        self._viewport_x = 0
        self._viewport_y = 0
        
    def set_viewport(self, viewport_x: int, viewport_y: int) -> None:
        """Set viewport offset for grid rendering."""
        self._viewport_x = viewport_x
        self._viewport_y = viewport_y
        
    def render(self, surface: pygame.Surface) -> None:
        """Render infinite grid - HEAVILY OPTIMIZED."""
        try:
            # Fast grid calculation
            start_x = (self._viewport_x // self.spacing) * self.spacing - self.spacing
            start_y = (self._viewport_y // self.spacing) * self.spacing - self.spacing
            
            end_x = start_x + self.width + self.spacing * 2
            end_y = start_y + self.height + self.spacing * 2
            
            # Pre-calculate screen bounds for culling
            left_bound = -100
            right_bound = self.width + 100
            top_bound = -100
            bottom_bound = self.height + 100
            
            # Render vertical lines - optimized loop
            x = start_x
            while x <= end_x:
                screen_x = x - self._viewport_x
                if left_bound <= screen_x <= right_bound:
                    pygame.draw.line(surface, self.color, (screen_x, 0), (screen_x, self.height), 1)
                x += self.spacing
                    
            # Render horizontal lines - optimized loop  
            y = start_y
            while y <= end_y:
                screen_y = y - self._viewport_y
                if top_bound <= screen_y <= bottom_bound:
                    pygame.draw.line(surface, self.color, (0, screen_y), (self.width, screen_y), 1)
                y += self.spacing
                    
        except Exception as e:
            logger.error("Error rendering grid: %s", e)

class StrokeObject(RenderableObject):
    """Stroke rendering object - HEAVILY OPTIMIZED."""
    __slots__ = ('points', 'color', 'stroke_width', '_screen_points', '_bounds_cache')
    
    def __init__(self, points: List[Tuple[int, int]], color: Tuple[int, int, int], width: int):
        if not points:
            super().__init__(0, 0, 0, 0)
            self.points = []
            self._screen_points = []
            self._bounds_cache = None
            return
            
        # Pre-calculate bounds for culling
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        super().__init__(min_x - width, min_y - width, 
                        max_x - min_x + 2*width, max_y - min_y + 2*width)
        
        self.points = points
        self.color = color
        self.stroke_width = width
        
        # Pre-convert to screen coordinates for faster rendering
        self._screen_points = [(int(x), int(y)) for x, y in points]
        self._bounds_cache = (min_x - width, min_y - width, max_x + width, max_y + width)
        
    def render(self, surface: pygame.Surface) -> None:
        """Render stroke - HEAVILY OPTIMIZED."""
        try:
            points_len = len(self._screen_points)
            
            if points_len == 0:
                return
            elif points_len == 1:
                # Single point - draw circle
                x, y = self._screen_points[0]
                radius = max(1, self.stroke_width >> 1)  # Fast division
                pygame.draw.circle(surface, self.color, (x, y), radius)
            else:
                # Multi-point stroke - optimized rendering
                width = self.stroke_width
                color = self.color
                
                # Draw line segments
                for i in range(points_len - 1):
                    pygame.draw.line(surface, color, self._screen_points[i], 
                                   self._screen_points[i + 1], width)
                
                # Add end caps for smooth appearance
                if width > 2:
                    cap_radius = width >> 1
                    pygame.draw.circle(surface, color, self._screen_points[0], cap_radius)
                    pygame.draw.circle(surface, color, self._screen_points[-1], cap_radius)
                    
        except Exception as e:
            logger.error("Error rendering stroke: %s", e)
            
    def is_visible_in_viewport(self, viewport_x: int, viewport_y: int, 
                              screen_width: int, screen_height: int) -> bool:
        """Fast visibility check."""
        if not self._bounds_cache:
            return True
            
        min_x, min_y, max_x, max_y = self._bounds_cache
        
        # Transform to screen coordinates
        screen_min_x = min_x - viewport_x
        screen_min_y = min_y - viewport_y
        screen_max_x = max_x - viewport_x
        screen_max_y = max_y - viewport_y
        
        # Check overlap with screen
        return not (screen_max_x < 0 or screen_min_x > screen_width or
                   screen_max_y < 0 or screen_min_y > screen_height)

class UIElement(RenderableObject):
    """UI element - OPTIMIZED."""
    __slots__ = ('background_color', 'text_elements', '_cached_surface')
    
    def __init__(self, x: int, y: int, width: int, height: int, 
                 background_color: Tuple[int, int, int] = (60, 60, 60)):
        super().__init__(x, y, width, height)
        self.background_color = background_color
        self.text_elements = []
        self._cached_surface = None
        
    def add_text(self, text: str, x: int, y: int, font_size: int = 12, 
                color: Tuple[int, int, int] = (255, 255, 255)):
        """Add text element."""
        self.text_elements.append({
            'text': text, 'x': x, 'y': y, 
            'font_size': font_size, 'color': color
        })
        self._cached_surface = None  # Invalidate cache
        
    def render(self, surface: pygame.Surface) -> None:
        """Render UI element - optimized with caching."""
        try:
            # Use cached surface if available
            if self._cached_surface is None:
                self._create_cached_surface()
                
            if self._cached_surface:
                surface.blit(self._cached_surface, (self.x, self.y))
                
        except Exception as e:
            logger.error("Error rendering UI element: %s", e)
            
    def _create_cached_surface(self):
        """Create cached surface for UI element."""
        try:
            self._cached_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            
            # Draw background
            bg_rect = pygame.Rect(0, 0, self.width, self.height)
            self._cached_surface.fill(self.background_color)
            pygame.draw.rect(self._cached_surface, (100, 100, 100), bg_rect, 1)
            
            # Draw text elements
            if self.text_elements:
                font = pygame.font.Font(None, 24)
                for text_elem in self.text_elements:
                    try:
                        text_surface = font.render(text_elem['text'], True, text_elem['color'])
                        self._cached_surface.blit(text_surface, (text_elem['x'], text_elem['y']))
                    except Exception:
                        continue
                        
        except Exception as e:
            logger.error("Error creating cached UI surface: %s", e)

class RenderLayer:
    """Individual rendering layer - HEAVILY OPTIMIZED."""
    __slots__ = ('config', 'objects', '_surface', '_cache_valid', '_dirty_objects',
                 '_lock', 'width', 'height', '_object_pool')
    
    def __init__(self, config: LayerConfig, width: int, height: int):
        self.config = config
        self.width = width
        self.height = height
        self.objects: List[RenderableObject] = []
        self._surface = None
        self._cache_valid = False
        self._dirty_objects: List[RenderableObject] = []
        self._lock = threading.Lock()
        self._object_pool = []  # Pool for reusing objects
        
        self._create_surface()
        
    def _create_surface(self):
        """Create layer surface."""
        try:
            if self.config.alpha < 255:
                self._surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                self._surface.set_alpha(self.config.alpha)
            else:
                self._surface = pygame.Surface((self.width, self.height))
        except Exception as e:
            logger.error("Error creating layer surface: %s", e)
            
    def add_object(self, obj: RenderableObject) -> None:
        """Add object to layer - optimized."""
        with self._lock:
            self.objects.append(obj)
            self._mark_dirty()
            
    def remove_object(self, obj: RenderableObject) -> None:
        """Remove object from layer - optimized."""
        with self._lock:
            try:
                self.objects.remove(obj)
                self._mark_dirty()
            except ValueError:
                pass  # Object not in list
                
    def clear_objects(self) -> None:
        """Clear all objects - optimized."""
        with self._lock:
            # Move objects to pool for reuse
            self._object_pool.extend(self.objects[:100])  # Keep reasonable pool size
            self.objects.clear()
            self._mark_dirty()
            
    def _mark_dirty(self) -> None:
        """Mark layer as needing re-render."""
        self._cache_valid = False
        
    def render(self, target_surface: pygame.Surface, viewport_offset: Tuple[int, int]) -> None:
        """Render layer to target surface - HEAVILY OPTIMIZED."""
        if not self._surface:
            return
            
        # Re-render to layer surface if dirty
        if not self._cache_valid:
            self._render_to_layer_surface(viewport_offset)
            self._cache_valid = True
            
        # Blit layer surface to target
        try:
            if self.config.alpha < 255 or self.config.blend_mode != pygame.BLEND_ALPHA_SDL2:
                target_surface.blit(self._surface, (0, 0), special_flags=self.config.blend_mode)
            else:
                target_surface.blit(self._surface, (0, 0))
        except Exception as e:
            logger.error("Error blitting layer %s: %s", self.config.name, e)
            
    def _render_to_layer_surface(self, viewport_offset: Tuple[int, int]) -> None:
        """Render all objects to layer surface - OPTIMIZED."""
        try:
            # Clear surface efficiently
            if self.config.alpha < 255:
                self._surface.fill((0, 0, 0, 0))  # Transparent
            else:
                self._surface.fill((0, 0, 0))  # Black
                
            viewport_x, viewport_y = viewport_offset
            
            # Special handling for grid background
            with self._lock:
                for obj in self.objects:
                    if not obj.visible:
                        continue
                        
                    try:
                        # Set viewport for grid objects
                        if isinstance(obj, GridBackground):
                            obj.set_viewport(viewport_x, viewport_y)
                        # Cull invisible strokes
                        elif isinstance(obj, StrokeObject):
                            if not obj.is_visible_in_viewport(viewport_x, viewport_y, 
                                                            self.width, self.height):
                                continue
                        
                        obj.render(self._surface)
                        obj.dirty = False
                        
                    except Exception as e:
                        logger.error("Error rendering object: %s", e)
                        continue
                        
        except Exception as e:
            logger.error("Error rendering to layer surface: %s", e)
            
    def resize(self, new_width: int, new_height: int):
        """Resize layer."""
        self.width = new_width
        self.height = new_height
        self._create_surface()
        self._mark_dirty()

class LayeredRenderingSystem:
    """Main layered rendering system - HEAVILY OPTIMIZED."""
    __slots__ = ('width', 'height', 'layers', 'viewport_offset', '_lock',
                 '_last_error_time', '_error_throttle_interval', '_render_stats')
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.layers: Dict[LayerType, RenderLayer] = {}
        self.viewport_offset = [0, 0]
        self._lock = threading.Lock()
        
        # Error throttling
        self._last_error_time = {}
        self._error_throttle_interval = 1.0
        
        # Performance stats
        self._render_stats = {
            'frame_count': 0,
            'total_render_time': 0.0,
            'objects_rendered': 0
        }
        
        self._initialize_layers()
        
    def _log_throttled_error(self, error_key: str, message: str) -> None:
        """Log error with throttling."""
        current_time = time.time()
        last_time = self._last_error_time.get(error_key, 0)
        
        if current_time - last_time >= self._error_throttle_interval:
            logger.error(message)
            self._last_error_time[error_key] = current_time
        
    def _initialize_layers(self):
        """Initialize rendering layers - optimized."""
        try:
            # Background layer
            bg_config = LayerConfig("background", LayerType.BACKGROUND, alpha=255, caching_enabled=True)
            self.layers[LayerType.BACKGROUND] = RenderLayer(bg_config, self.width, self.height)
            
            # Drawing layer  
            draw_config = LayerConfig("drawing", LayerType.DRAWING, alpha=255, caching_enabled=True)
            self.layers[LayerType.DRAWING] = RenderLayer(draw_config, self.width, self.height)
            
            # UI layer
            ui_config = LayerConfig("interface", LayerType.UI, alpha=240, blend_mode=pygame.BLEND_ALPHA_SDL2)
            self.layers[LayerType.UI] = RenderLayer(ui_config, self.width, self.height)
            
            # Add grid to background
            grid = GridBackground(self.width, self.height)
            self.layers[LayerType.BACKGROUND].add_object(grid)
            
        except Exception as e:
            self._log_throttled_error("init_layers", f"Failed to initialize layers: {e}")
            
    def add_stroke(self, points: List[Tuple[int, int]], color: Tuple[int, int, int], width: int) -> None:
        """Add stroke to drawing layer - optimized."""
        try:
            if points:  # Only add non-empty strokes
                stroke = StrokeObject(points, color, width)
                self.layers[LayerType.DRAWING].add_object(stroke)
        except Exception as e:
            self._log_throttled_error("add_stroke", f"Error adding stroke: {e}")
            
    def add_ui_element(self, element: UIElement) -> None:
        """Add UI element to UI layer."""
        try:
            self.layers[LayerType.UI].add_object(element)
        except Exception as e:
            self._log_throttled_error("add_ui", f"Error adding UI element: {e}")
            
    def clear_drawing_layer(self) -> None:
        """Clear only drawing layer, preserve grid."""
        try:
            self.layers[LayerType.DRAWING].clear_objects()
        except Exception as e:
            self._log_throttled_error("clear_drawing", f"Error clearing drawing layer: {e}")
            
    def erase_at_position(self, x: int, y: int, radius: int) -> None:
        """Erase only affects drawing layer - OPTIMIZED."""
        try:
            drawing_layer = self.layers[LayerType.DRAWING]
            
            with drawing_layer._lock:
                objects_to_remove = []
                radius_sq = radius * radius
                
                for obj in drawing_layer.objects:
                    if isinstance(obj, StrokeObject):
                        # Fast circle intersection test
                        for px, py in obj.points:
                            dx = px - x
                            dy = py - y
                            if dx * dx + dy * dy <= radius_sq:
                                objects_to_remove.append(obj)
                                break
                                
                # Remove intersecting strokes
                for obj in objects_to_remove:
                    drawing_layer.remove_object(obj)
                    
        except Exception as e:
            self._log_throttled_error("erase", f"Error erasing at position: {e}")
            
    def pan_viewport(self, dx: int, dy: int) -> None:
        """Pan viewport - optimized."""
        try:
            self.viewport_offset[0] += dx
            self.viewport_offset[1] += dy
            
            # Mark layers as dirty
            for layer in self.layers.values():
                layer._mark_dirty()
                
        except Exception as e:
            self._log_throttled_error("pan", f"Error panning viewport: {e}")
            
    def render_all(self, target_surface: pygame.Surface) -> None:
        """Render all layers - HEAVILY OPTIMIZED."""
        render_start = time.time()
        
        try:
            # Clear target efficiently
            target_surface.fill((0, 0, 0))
            
            # Render in z-order
            viewport_tuple = tuple(self.viewport_offset)
            
            for layer_type in [LayerType.BACKGROUND, LayerType.DRAWING, LayerType.UI]:
                layer = self.layers.get(layer_type)
                if layer:
                    layer.render(target_surface, viewport_tuple)
                    
            # Update stats
            self._render_stats['frame_count'] += 1
            self._render_stats['total_render_time'] += time.time() - render_start
                    
        except Exception as e:
            self._log_throttled_error("render_all", f"Critical error in render_all: {e}")
            
    def resize(self, new_width: int, new_height: int) -> None:
        """Resize rendering system."""
        try:
            self.width = new_width
            self.height = new_height
            
            # Resize all layers
            for layer in self.layers.values():
                layer.resize(new_width, new_height)
                
        except Exception as e:
            self._log_throttled_error("resize", f"Error resizing rendering system: {e}")
            
    def get_layer_stats(self) -> Dict[str, Any]:
        """Get layer statistics."""
        try:
            stats = {}
            for layer_type, layer in self.layers.items():
                stats[layer_type.name] = {
                    'object_count': len(layer.objects),
                    'cache_valid': layer._cache_valid,
                    'config': layer.config.__dict__
                }
            stats['render_stats'] = self._render_stats.copy()
            return stats
        except Exception as e:
            self._log_throttled_error("stats", f"Error getting layer stats: {e}")
            return {}
            
    def get_average_fps(self) -> float:
        """Get average FPS."""
        try:
            frame_count = self._render_stats['frame_count']
            total_time = self._render_stats['total_render_time']
            return frame_count / total_time if total_time > 0 else 0.0
        except Exception:
            return 0.0

class LayeredPygameAdapter:
    """Adapter for integrating with existing pygame code - OPTIMIZED."""
    __slots__ = ('engine', 'rendering_system')
    
    def __init__(self, pygame_engine):
        self.engine = pygame_engine
        self.rendering_system = None
        
    def initialize(self, width: int, height: int):
        """Initialize layered rendering."""
        try:
            self.rendering_system = LayeredRenderingSystem(width, height)
        except Exception as e:
            logger.error("Failed to initialize layered adapter: %s", e)
            
    def draw_stroke_layered(self, points: List[Tuple[int, int]], color: Tuple[int, int, int], width: int):
        """Draw stroke using layered system."""
        if self.rendering_system and points:
            self.rendering_system.add_stroke(points, color, width)
            
    def erase_layered(self, x: int, y: int, radius: int):
        """Erase using layered system."""
        if self.rendering_system:
            self.rendering_system.erase_at_position(x, y, radius)
            
    def clear_canvas_layered(self):
        """Clear drawing layer only."""
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