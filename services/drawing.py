"""
Drawing Service Migration - Backward Compatibility Layer.

This module provides a backward-compatible LayeredDrawingService class that wraps
the new refactored drawing system, allowing existing applications to continue working
without modification while gaining the benefits of the improved architecture.
"""

import logging
import math
import time
from typing import Any, Dict, List, Tuple, Optional
from collections import defaultdict

from core.event_bus import EventBus

logger = logging.getLogger(__name__)


class SimpleEventBusAdapter:
    """Adapter for event bus if core.event_bus is not available."""
    
    def __init__(self):
        self.subscribers = defaultdict(list)
    
    def publish(self, event_name: str, event_data: Any) -> None:
        """Publish event to all subscribers."""
        for callback in self.subscribers[event_name]:
            try:
                callback(event_data)
            except Exception as error:
                logger.error(f"Event callback error: {error}")
    
    def subscribe(self, event_name: str, callback_function) -> None:
        """Subscribe callback function to event."""
        self.subscribers[event_name].append(callback_function)


class PygameRendererAdapter:
    """Pygame renderer adapter for the compatibility layer."""
    
    def __init__(self, surface):
        self.surface = surface
        
    def render_background_grid(self, viewport, config) -> None:
        """Render infinite background grid."""
        try:
            import pygame
            
            self.surface.fill((0, 0, 0))
            
            grid_spacing = 40
            grid_color = (30, 30, 30)
            
            world_left = viewport.x
            world_top = viewport.y
            world_right = viewport.x + viewport.width
            world_bottom = viewport.y + viewport.height
            
            first_vertical = (world_left // grid_spacing) * grid_spacing
            for world_x in range(int(first_vertical), int(world_right) + grid_spacing, grid_spacing):
                screen_x = world_x - viewport.x
                if 0 <= screen_x <= viewport.width:
                    pygame.draw.line(self.surface, grid_color, 
                                   (screen_x, 0), (screen_x, viewport.height), 1)
            
            first_horizontal = (world_top // grid_spacing) * grid_spacing
            for world_y in range(int(first_horizontal), int(world_bottom) + grid_spacing, grid_spacing):
                screen_y = world_y - viewport.y
                if 0 <= screen_y <= viewport.height:
                    pygame.draw.line(self.surface, grid_color,
                                   (0, screen_y), (viewport.width, screen_y), 1)
        except Exception as e:
            logger.error(f"Error rendering grid: {e}")
    
    def render_stroke(self, stroke, viewport) -> None:
        """Render drawing stroke."""
        try:
            import pygame
            
            if not stroke.points:
                return
            
            screen_points = []
            for point in stroke.points:
                screen_x = int(point.world_coordinate.x - viewport.x)
                screen_y = int(point.world_coordinate.y - viewport.y)
                
                if (-100 <= screen_x <= viewport.width + 100 and 
                    -100 <= screen_y <= viewport.height + 100):
                    screen_points.append((screen_x, screen_y))
            
            if len(screen_points) < 2:
                if len(screen_points) == 1:
                    pygame.draw.circle(self.surface, stroke.color, screen_points[0], 
                                     max(1, int(stroke.points[0].width // 2)))
                return
            
            for i in range(len(screen_points) - 1):
                start = screen_points[i]
                end = screen_points[i + 1]
                width = max(1, int(stroke.points[i].width if i < len(stroke.points) else 3))
                pygame.draw.line(self.surface, stroke.color, start, end, width)
                
        except Exception as e:
            logger.error(f"Error rendering stroke: {e}")
    
    def render_stroke_preview(self, points, viewport, config) -> None:
        """Render stroke preview."""
        try:
            import pygame
            
            if not points:
                return
            
            preview_color = (128, 128, 255)
            screen_points = []
            
            for point in points:
                screen_x = int(point.world_coordinate.x - viewport.x)
                screen_y = int(point.world_coordinate.y - viewport.y)
                screen_points.append((screen_x, screen_y))
            
            if len(screen_points) >= 2:
                width = max(1, int(config.brush_width))
                for i in range(len(screen_points) - 1):
                    start = screen_points[i]
                    end = screen_points[i + 1]
                    pygame.draw.line(self.surface, preview_color, start, end, width)
                    
        except Exception as e:
            logger.error(f"Error rendering preview: {e}")
    
    def clear_display(self) -> None:
        """Clear display surface."""
        try:
            self.surface.fill((0, 0, 0))
        except Exception as e:
            logger.error(f"Error clearing display: {e}")


class LayeredDrawingService:
    """
    Backward-compatible LayeredDrawingService implementation.
    
    This class provides the same interface as the original LayeredDrawingService
    but uses the new refactored drawing system internally. This allows existing
    applications to continue working without modification.
    """
    
    def __init__(self, bus: EventBus, settings: Any):
        """Initialize backward-compatible drawing service."""
        try:
            self.bus = bus
        except:
            self.bus = SimpleEventBusAdapter()
            
        self.settings = settings
        
        # Import the new refactored system
        from .drawing_refactored import (
            DrawingTool, WorldCoordinate, ScreenCoordinate, DrawingPoint, 
            DrawingStroke, ViewportState, DrawingConfiguration,
            InfiniteCanvasService, ViewportManagementService, 
            DrawingConfigurationService, DrawingOrchestrationService,
            InMemoryCanvasDataStore, StandardInputHandler, ShapeType
        )
        
        # Store classes for use
        self.DrawingTool = DrawingTool
        self.WorldCoordinate = WorldCoordinate
        self.ScreenCoordinate = ScreenCoordinate
        self.DrawingPoint = DrawingPoint
        self.DrawingStroke = DrawingStroke
        self.ViewportState = ViewportState
        self.DrawingConfiguration = DrawingConfiguration
        self.ShapeType = ShapeType
        
        # Initialize services
        self.data_store = InMemoryCanvasDataStore()
        self.input_handler = StandardInputHandler()
        
        # Surfaces for compatibility
        self.background_surface = None
        self.drawing_surface = None
        self.ui_surface = None
        
        # Current state tracking for compatibility
        self._current_tool = "brush"
        self._current_base_width = 5
        self._current_brush_color = (255, 255, 255)
        
        # Services will be initialized in initialize_layers
        self.canvas_service = None
        self.viewport_service = None  
        self.config_service = None
        self.orchestration_service = None
        self.renderer = None
        
        logger.info("Backward-compatible LayeredDrawingService initialized")
    
    def initialize_layers(self, width: int, height: int) -> None:
        """Initialize drawing layers and internal services."""
        try:
            import pygame
            
            self.screen_width = width
            self.screen_height = height
            
            # Create surfaces for compatibility
            self.background_surface = pygame.Surface((width, height))
            self.drawing_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            self.ui_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            self.ui_surface.fill((0, 0, 0, 0))
            
            # Initialize the new system
            initial_viewport = self.ViewportState(x=0, y=0, width=width, height=height)
            initial_config = self.DrawingConfiguration(
                current_tool=self.DrawingTool.BRUSH,
                brush_width=float(self._current_base_width),
                brush_color=self._current_brush_color
            )
            
            self.canvas_service = InfiniteCanvasService(self.data_store)
            self.viewport_service = ViewportManagementService(initial_viewport)
            self.config_service = DrawingConfigurationService(initial_config)
            self.renderer = PygameRendererAdapter(self.drawing_surface)
            
            # Import orchestration service classes
            from .drawing_refactored import DrawingOrchestrationService
            
            self.orchestration_service = DrawingOrchestrationService(
                canvas_service=self.canvas_service,
                viewport_service=self.viewport_service,
                config_service=self.config_service,
                input_handler=self.input_handler,
                renderer=self.renderer,
                event_bus=self.bus
            )
            
            logger.info(f"Layers initialized: {width}x{height}")
            
        except Exception as e:
            logger.error(f"Failed to initialize layers: {e}")
            # Fallback initialization
            self._initialize_fallback_system(width, height)
    
    def _initialize_fallback_system(self, width: int, height: int) -> None:
        """Fallback initialization if new system fails."""
        try:
            import pygame
            
            self.screen_width = width
            self.screen_height = height
            self.background_surface = pygame.Surface((width, height))
            self.drawing_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            self.ui_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            
            # Simple fallback state
            self._viewport_x = 0
            self._viewport_y = 0
            self._is_drawing = False
            self._is_panning = False
            self._world_strokes = []
            self._dynamic_stroke_points = []
            
            logger.warning("Using fallback drawing system")
            
        except Exception as e:
            logger.error(f"Fallback initialization failed: {e}")
    
    def handle_mouse_down(self, x: int, y: int, button: int) -> bool:
        """Handle mouse down events."""
        try:
            if self.orchestration_service:
                return self.orchestration_service.handle_mouse_down(x, y, button)
            else:
                return self._fallback_mouse_down(x, y, button)
        except Exception as e:
            logger.error(f"Error in handle_mouse_down: {e}")
            return False
    
    def handle_mouse_move(self, x: int, y: int) -> bool:
        """Handle mouse move events."""
        try:
            if self.orchestration_service:
                return self.orchestration_service.handle_mouse_move(x, y)
            else:
                return self._fallback_mouse_move(x, y)
        except Exception as e:
            logger.error(f"Error in handle_mouse_move: {e}")
            return False
    
    def handle_mouse_up(self, x: int, y: int, button: int) -> bool:
        """Handle mouse up events."""
        try:
            if self.orchestration_service:
                return self.orchestration_service.handle_mouse_up(x, y, button)
            else:
                return self._fallback_mouse_up(x, y, button)
        except Exception as e:
            logger.error(f"Error in handle_mouse_up: {e}")
            return False
    
    def handle_scroll(self, direction: int) -> bool:
        """Handle scroll wheel events."""
        try:
            if self.orchestration_service:
                return self.orchestration_service.handle_scroll(direction)
            else:
                return self._fallback_scroll(direction)
        except Exception as e:
            logger.error(f"Error in handle_scroll: {e}")
            return False
    
    def handle_key_press(self, key: str) -> bool:
        """Handle key press events."""
        try:
            if self.orchestration_service:
                return self.orchestration_service.handle_key_press(key)
            else:
                return self._fallback_key_press(key)
        except Exception as e:
            logger.error(f"Error in handle_key_press: {e}")
            return False
    
    def render(self, screen_surface) -> None:
        """Render the complete drawing canvas."""
        try:
            if self.orchestration_service:
                # Use new system rendering
                original_surface = self.renderer.surface
                self.renderer.surface = screen_surface
                self.orchestration_service.render_complete_canvas()
                self.renderer.surface = original_surface
            else:
                # Fallback rendering
                self._fallback_render(screen_surface)
        except Exception as e:
            logger.error(f"Error in render: {e}")
    
    def clear_canvas(self) -> None:
        """Clear all drawing from canvas."""
        try:
            if self.orchestration_service:
                self.orchestration_service.clear_canvas()
            else:
                self._fallback_clear_canvas()
        except Exception as e:
            logger.error(f"Error in clear_canvas: {e}")
    
    def get_current_tool(self) -> str:
        """Get current drawing tool."""
        try:
            if self.orchestration_service:
                tool = self.orchestration_service.get_current_tool()
                return tool.value if hasattr(tool, 'value') else str(tool)
            else:
                return self._current_tool
        except Exception as e:
            logger.error(f"Error getting current tool: {e}")
            return self._current_tool
    
    def get_current_brush_width(self) -> int:
        """Get current brush width."""
        try:
            if self.orchestration_service:
                return int(self.orchestration_service.get_current_brush_width())
            else:
                return self._current_base_width
        except Exception as e:
            logger.error(f"Error getting brush width: {e}")
            return self._current_base_width
    
    def is_drawing(self) -> bool:
        """Check if currently drawing."""
        try:
            if self.orchestration_service:
                return self.orchestration_service.is_drawing_active()
            else:
                return getattr(self, '_is_drawing', False)
        except Exception as e:
            logger.error(f"Error checking drawing state: {e}")
            return False
    
    def is_panning(self) -> bool:
        """Check if currently panning."""
        try:
            if self.orchestration_service:
                return self.orchestration_service.is_panning_active()
            else:
                return getattr(self, '_is_panning', False)
        except Exception as e:
            logger.error(f"Error checking panning state: {e}")
            return False
    
    def get_viewport_position(self) -> Tuple[int, int]:
        """Get current viewport position."""
        try:
            if self.orchestration_service:
                pos = self.orchestration_service.get_viewport_position()
                return (int(pos[0]), int(pos[1]))
            else:
                return (getattr(self, '_viewport_x', 0), getattr(self, '_viewport_y', 0))
        except Exception as e:
            logger.error(f"Error getting viewport position: {e}")
            return (0, 0)
    
    def get_stroke_count(self) -> int:
        """Get total stroke count."""
        try:
            if self.orchestration_service:
                return self.orchestration_service.get_stroke_count()
            else:
                return len(getattr(self, '_world_strokes', []))
        except Exception as e:
            logger.error(f"Error getting stroke count: {e}")
            return 0
    
    # Fallback methods for when new system is not available
    def _fallback_mouse_down(self, x: int, y: int, button: int) -> bool:
        """Fallback mouse down handling."""
        if button == 3:  # Right click - panning
            self._is_panning = True
            return True
        elif button == 1:  # Left click - drawing
            self._is_drawing = True
            self._dynamic_stroke_points = [{'x': x, 'y': y, 'width': self._current_base_width}]
            return True
        return False
    
    def _fallback_mouse_move(self, x: int, y: int) -> bool:
        """Fallback mouse move handling."""
        if self._is_drawing:
            self._dynamic_stroke_points.append({'x': x, 'y': y, 'width': self._current_base_width})
            return True
        return False
    
    def _fallback_mouse_up(self, x: int, y: int, button: int) -> bool:
        """Fallback mouse up handling."""
        if button == 3:
            self._is_panning = False
            return True
        elif button == 1 and self._is_drawing:
            self._is_drawing = False
            if hasattr(self, '_world_strokes') and self._dynamic_stroke_points:
                stroke = {
                    'points': self._dynamic_stroke_points.copy(),
                    'color': self._current_brush_color,
                    'tool': self._current_tool
                }
                self._world_strokes.append(stroke)
            self._dynamic_stroke_points = []
            return True
        return False
    
    def _fallback_scroll(self, direction: int) -> bool:
        """Fallback scroll handling."""
        if direction > 0:
            self._current_base_width = min(self._current_base_width + 2, 50)
        else:
            self._current_base_width = max(self._current_base_width - 2, 1)
        return True
    
    def _fallback_key_press(self, key: str) -> bool:
        """Fallback key press handling."""
        if key == 'space':
            tools = ['brush', 'eraser', 'line', 'rect', 'circle', 'triangle', 'parabola']
            try:
                current_index = tools.index(self._current_tool)
                self._current_tool = tools[(current_index + 1) % len(tools)]
            except ValueError:
                self._current_tool = 'brush'
            return True
        elif key == 'c':
            if hasattr(self, '_world_strokes'):
                self._world_strokes.clear()
            return True
        return False
    
    def _fallback_render(self, screen_surface) -> None:
        """Fallback rendering method."""
        try:
            screen_surface.fill((0, 0, 0))
            
            # Draw simple grid
            import pygame
            grid_color = (30, 30, 30)
            for x in range(0, self.screen_width, 40):
                pygame.draw.line(screen_surface, grid_color, (x, 0), (x, self.screen_height), 1)
            for y in range(0, self.screen_height, 40):
                pygame.draw.line(screen_surface, grid_color, (0, y), (self.screen_width, y), 1)
            
            # Draw strokes if available
            if hasattr(self, '_world_strokes'):
                for stroke in self._world_strokes:
                    points = stroke.get('points', [])
                    color = stroke.get('color', (255, 255, 255))
                    for i in range(len(points) - 1):
                        start = (int(points[i]['x']), int(points[i]['y']))
                        end = (int(points[i + 1]['x']), int(points[i + 1]['y']))
                        pygame.draw.line(screen_surface, color, start, end, 3)
            
        except Exception as e:
            logger.error(f"Error in fallback render: {e}")
    
    def _fallback_clear_canvas(self) -> None:
        """Fallback canvas clearing."""
        if hasattr(self, '_world_strokes'):
            self._world_strokes.clear()
        self._dynamic_stroke_points = []


# Import the new system for direct access if needed
try:
    from .drawing_refactored import *
    logger.info("New drawing system available for direct use")
except ImportError as e:
    logger.warning(f"New drawing system not available: {e}")


# For applications that need the old DrawingCanvas and DrawingInputHandler classes
class DrawingCanvas:
    """Compatibility wrapper for DrawingCanvas."""
    
    def __init__(self):
        self._current_brush_color = (255, 255, 255)
    
    def set_brush_color(self, color):
        """Set brush color."""
        self._current_brush_color = color


class DrawingInputHandler:
    """Compatibility wrapper for DrawingInputHandler."""
    
    def __init__(self, canvas, settings):
        self.canvas = canvas
        self.settings = settings
        self.on_tool_changed = None
        self.on_brush_width_changed = None