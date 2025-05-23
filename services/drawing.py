# services/drawing.py (FIXED - Proper infinite canvas with stationary objects)
"""
Fixed Drawing System with True Infinite Canvas Panning

CRITICAL FIXES:
1. Objects (drawings, shapes, grid) remain stationary in world space
2. Pan only changes viewport position, revealing more infinite space
3. Proper coordinate system: world coordinates vs screen coordinates
4. Grid extends infinitely without moving during pan
"""

import logging
import math
import time
from typing import Any, Dict, List, Tuple, Optional

from core.event_bus import EventBus
from core.drawing.canvas import DrawingCanvas
from core.drawing.input_handler import DrawingInputHandler

logger = logging.getLogger(__name__)


class LayeredDrawingService:
    """Drawing service with true infinite canvas panning where only viewport moves."""
    
    def __init__(self, bus: EventBus, settings: Any):
        self.bus = bus
        self.settings = settings
        self.canvas = DrawingCanvas()
        self.input_handler = DrawingInputHandler(self.canvas, settings)
        
        # Layer surfaces
        self.background_surface = None
        self.drawing_surface = None
        self.ui_surface = None
        
        # Universal brush state
        self._dynamic_stroke_points = []
        self._is_drawing = False
        self._current_base_width = 5
        self._current_tool = "brush"
        
        # Shape state
        self._shape_start_pos = None
        self._shape_current_pos = None
        self._preview_points = []
        
        # CRITICAL FIX: Viewport for infinite canvas (only POV moves)
        self._is_panning = False
        self._pan_start_pos = None
        self._last_pan_pos = None
        self._viewport_x = 0  # Camera position in world space
        self._viewport_y = 0  # Camera position in world space
        self._pan_sensitivity = 1.0
        
        # World space storage for all permanent objects
        self._world_strokes = []  # All strokes in world coordinates
        
        # Connect input handler callbacks
        self.input_handler.on_tool_changed = self._on_tool_changed
        self.input_handler.on_brush_width_changed = self._on_brush_width_changed
        
        # Subscribe to events
        self.bus.subscribe('tool_changed', self._handle_tool_changed)
        
        logger.info("LayeredDrawingService initialized with true infinite canvas")
    
    def initialize_layers(self, width: int, height: int) -> None:
        """Initialize separate drawing layers."""
        try:
            import pygame
            
            self.screen_width = width
            self.screen_height = height
            
            # Background layer - will be regenerated each frame based on viewport
            self.background_surface = pygame.Surface((width, height))
            
            # Drawing layer - will render world objects based on viewport
            self.drawing_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            
            # UI layer
            self.ui_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            self.ui_surface.fill((0, 0, 0, 0))
            
            logger.info("Layers initialized: %dx%d with infinite canvas", width, height)
            
        except Exception as e:
            logger.error("Failed to initialize layers: %s", e)
    
    def _generate_infinite_grid(self) -> None:
        """CRITICAL FIX: Generate infinite grid based on viewport position."""
        if not self.background_surface:
            return
            
        try:
            import pygame
            
            # Clear background
            self.background_surface.fill((0, 0, 0))
            
            grid_spacing = 40
            grid_color = (30, 30, 30)
            
            # CRITICAL FIX: Calculate grid lines based on viewport position
            # The grid exists in world space, we render the visible portion
            
            # Calculate the world coordinates of the screen edges
            world_left = self._viewport_x
            world_top = self._viewport_y
            world_right = self._viewport_x + self.screen_width
            world_bottom = self._viewport_y + self.screen_height
            
            # Find the grid lines that would be visible
            # Vertical lines
            first_vertical = (world_left // grid_spacing) * grid_spacing
            for world_x in range(int(first_vertical), int(world_right) + grid_spacing, grid_spacing):
                # Convert world coordinate to screen coordinate
                screen_x = world_x - self._viewport_x
                if 0 <= screen_x <= self.screen_width:
                    pygame.draw.line(self.background_surface, grid_color, 
                                   (screen_x, 0), (screen_x, self.screen_height), 1)
            
            # Horizontal lines
            first_horizontal = (world_top // grid_spacing) * grid_spacing
            for world_y in range(int(first_horizontal), int(world_bottom) + grid_spacing, grid_spacing):
                # Convert world coordinate to screen coordinate
                screen_y = world_y - self._viewport_y
                if 0 <= screen_y <= self.screen_height:
                    pygame.draw.line(self.background_surface, grid_color,
                                   (0, screen_y), (self.screen_width, screen_y), 1)
            
            logger.debug("Generated infinite grid for viewport (%d, %d)", self._viewport_x, self._viewport_y)
            
        except Exception as e:
            logger.error("Error generating infinite grid: %s", e)
    
    def _on_tool_changed(self, tool: str) -> None:
        """Handle tool changes."""
        self._current_tool = tool
        self.bus.publish('tool_changed', tool)
        logger.debug("Tool changed: %s", tool)
    
    def _handle_tool_changed(self, tool: str) -> None:
        """Handle tool_changed events."""
        self._current_tool = tool
    
    def _on_brush_width_changed(self, width: int) -> None:
        """Handle brush width changes."""
        self._current_base_width = width
        self.bus.publish('brush_width_changed', width)
        logger.debug("Universal brush width changed: %d", width)
    
    def handle_mouse_down(self, x: int, y: int, button: int) -> bool:
        """Handle mouse down with proper coordinate conversion."""
        if button == 3:  # Right click - start panning
            return self._start_pan(x, y)
        elif button == 1:  # Left click - start drawing
            if self._is_panning:
                return False
                
            self._is_drawing = True
            
            # CRITICAL FIX: Convert screen coordinates to world coordinates
            world_x = x + self._viewport_x
            world_y = y + self._viewport_y
            
            # Store in world coordinates
            self._dynamic_stroke_points = [{
                'x': world_x, 
                'y': world_y, 
                'width': self._current_base_width,
                'pressure': 1.0
            }]
            
            # Handle shape tools
            if self._current_tool in ['line', 'rect', 'circle', 'triangle', 'parabola']:
                self._shape_start_pos = (world_x, world_y)
                self._shape_current_pos = (world_x, world_y)
                self._preview_points = []
                logger.debug("Started shape: %s at world pos (%d, %d)", self._current_tool, world_x, world_y)
            else:
                logger.debug("Started stroke at world pos (%d, %d)", world_x, world_y)
            
            return True
        
        return False
    
    def _start_pan(self, x: int, y: int) -> bool:
        """Start panning operation."""
        try:
            self._is_panning = True
            self._pan_start_pos = (x, y)
            self._last_pan_pos = (x, y)
            
            logger.debug("Started panning at screen pos (%d, %d)", x, y)
            return True
            
        except Exception as e:
            logger.error("Error starting pan: %s", e)
            return False
    
    def handle_mouse_move(self, x: int, y: int) -> bool:
        """Handle mouse move with proper coordinate handling."""
        if self._is_panning:
            return self._update_pan(x, y)
        elif self._is_drawing:
            # CRITICAL FIX: Convert screen to world coordinates
            world_x = x + self._viewport_x
            world_y = y + self._viewport_y
            
            if self._current_tool in ['line', 'rect', 'circle', 'triangle', 'parabola']:
                # Update shape preview in world coordinates
                self._shape_current_pos = (world_x, world_y)
                self._update_shape_preview()
                return True
            else:
                # Add point in world coordinates
                self._dynamic_stroke_points.append({
                    'x': world_x,
                    'y': world_y, 
                    'width': self._current_base_width,
                    'pressure': 1.0
                })
                
                if len(self._dynamic_stroke_points) > 1000:
                    self._dynamic_stroke_points = self._dynamic_stroke_points[-500:]
                
                return True
        
        return False
    
    def _update_pan(self, x: int, y: int) -> bool:
        """CRITICAL FIX: Update viewport position, not object positions."""
        try:
            if not self._is_panning or not self._last_pan_pos:
                return False
            
            # Calculate how much the mouse moved
            dx = (x - self._last_pan_pos[0]) * self._pan_sensitivity
            dy = (y - self._last_pan_pos[1]) * self._pan_sensitivity
            
            # CRITICAL FIX: Move viewport in opposite direction
            # When mouse moves right, we want to see what's to the left
            self._viewport_x -= int(dx)
            self._viewport_y -= int(dy)
            
            self._last_pan_pos = (x, y)
            
            logger.debug("Pan: viewport moved to (%d, %d)", self._viewport_x, self._viewport_y)
            
            return True
            
        except Exception as e:
            logger.error("Error updating pan: %s", e)
            return False
    
    def handle_mouse_up(self, x: int, y: int, button: int) -> bool:
        """Handle mouse up with proper completion."""
        if button == 3:  # Right click - end panning
            return self._end_pan()
        elif button == 1 and self._is_drawing:
            if self._current_tool in ['line', 'rect', 'circle', 'triangle', 'parabola']:
                self._complete_shape()
            else:
                self._complete_dynamic_stroke()
            
            self._reset_drawing_state()
            return True
        
        return False
    
    def _end_pan(self) -> bool:
        """End panning operation."""
        try:
            self._is_panning = False
            self._pan_start_pos = None
            self._last_pan_pos = None
            
            logger.debug("Ended panning at viewport (%d, %d)", self._viewport_x, self._viewport_y)
            return True
            
        except Exception as e:
            logger.error("Error ending pan: %s", e)
            return False
    
    def handle_scroll(self, direction: int) -> bool:
        """Universal scroll for ALL tools."""
        old_width = self._current_base_width
        
        if direction > 0:
            self._current_base_width = min(self._current_base_width + 2, 50)
        else:
            self._current_base_width = max(self._current_base_width - 2, 1)
        
        if self._current_base_width != old_width:
            self.bus.publish('brush_width_changed', self._current_base_width)
            logger.debug("Universal width change: %d -> %d", old_width, self._current_base_width)
            
            if self._is_drawing and self._current_tool in ['line', 'rect', 'circle', 'triangle', 'parabola']:
                self._update_shape_preview()
        
        return True
    
    def _complete_dynamic_stroke(self) -> None:
        """Complete stroke and store in world coordinates."""
        if not self._dynamic_stroke_points:
            return
        
        try:
            # Store stroke in world coordinates
            world_stroke = {
                'points': self._dynamic_stroke_points.copy(),
                'color': self.canvas._current_brush_color,
                'width': self._current_base_width,
                'tool': self._current_tool,
                'timestamp': time.time()
            }
            
            self._world_strokes.append(world_stroke)
            
            logger.debug("Stored stroke in world coordinates with %d points", len(self._dynamic_stroke_points))
            
        except Exception as e:
            logger.error("Error completing dynamic stroke: %s", e)
    
    def _update_shape_preview(self) -> None:
        """Update shape preview in world coordinates."""
        if not self._shape_start_pos or not self._shape_current_pos:
            return
        
        start_x, start_y = self._shape_start_pos
        end_x, end_y = self._shape_current_pos
        
        try:
            if self._current_tool == 'line':
                self._preview_points = [(start_x, start_y), (end_x, end_y)]
            elif self._current_tool == 'rect':
                self._preview_points = self._generate_rect_preview(start_x, start_y, end_x, end_y)
            elif self._current_tool == 'circle':
                self._preview_points = self._generate_circle_preview(start_x, start_y, end_x, end_y)
            elif self._current_tool == 'triangle':
                self._preview_points = self._generate_triangle_preview(start_x, start_y, end_x, end_y)
            elif self._current_tool == 'parabola':
                self._preview_points = self._generate_parabola_preview_dense(start_x, start_y, end_x, end_y)
        except Exception as e:
            logger.error("Error updating shape preview: %s", e)
            self._preview_points = [(start_x, start_y), (end_x, end_y)]
    
    def _generate_parabola_preview_dense(self, x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
        """Generate dense parabola in world coordinates."""
        if abs(x2 - x1) < 2 and abs(y2 - y1) < 2:
            return [(x1, y1), (x2, y2)]
        
        points = []
        steps = 100
        
        dx = x2 - x1
        dy = y2 - y1
        
        mid_x = (x1 + x2) / 2.0
        distance = math.sqrt(dx*dx + dy*dy)
        vertex_offset = distance * 0.25
        
        if dy >= 0:
            k = min(y1, y2) - vertex_offset
        else:
            k = max(y1, y2) + vertex_offset
        
        h = mid_x
        
        try:
            if abs(x1 - h) > 0.01:
                a = (y1 - k) / ((x1 - h) ** 2)
            else:
                a = 1.0 if dy >= 0 else -1.0
        except:
            a = 1.0 if dy >= 0 else -1.0
        
        for i in range(steps + 1):
            t = i / steps
            x = x1 + t * (x2 - x1)
            y = a * (x - h) ** 2 + k
            points.append((int(round(x)), int(round(y))))
        
        # Add intermediate points for smoothness
        dense_points = []
        for i in range(len(points) - 1):
            dense_points.append(points[i])
            x1_p, y1_p = points[i]
            x2_p, y2_p = points[i + 1]
            if abs(x2_p - x1_p) > 1 or abs(y2_p - y1_p) > 1:
                mid_x_p = (x1_p + x2_p) // 2
                mid_y_p = (y1_p + y2_p) // 2
                dense_points.append((mid_x_p, mid_y_p))
        
        dense_points.append(points[-1])
        return dense_points
    
    def _generate_rect_preview(self, x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
        """Generate rectangle preview."""
        return [
            (x1, y1), (x2, y1),  # Top
            (x2, y1), (x2, y2),  # Right
            (x2, y2), (x1, y2),  # Bottom  
            (x1, y2), (x1, y1)   # Left
        ]
    
    def _generate_circle_preview(self, x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
        """Generate circle preview."""
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        radius = max(1, int(math.sqrt((x2 - x1)**2 + (y2 - y1)**2) // 2))
        
        points = []
        num_points = max(64, radius * 2)
        
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            
            next_angle = 2 * math.pi * (i + 1) / num_points
            next_x = center_x + radius * math.cos(next_angle)
            next_y = center_y + radius * math.sin(next_angle)
            
            points.append((int(x), int(y)))
            points.append((int(next_x), int(next_y)))
        
        return points
    
    def _generate_triangle_preview(self, x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
        """Generate triangle preview."""
        return [
            (x1, y1), (x2, y2),  # Diagonal
            (x2, y2), (x2, y1),  # Vertical
            (x2, y1), (x1, y1)   # Horizontal
        ]
    
    def _complete_shape(self) -> None:
        """Complete shape and store in world coordinates."""
        if not self._preview_points:
            return
        
        try:
            # Store shape as world stroke
            shape_stroke = {
                'points': [{'x': x, 'y': y, 'width': self._current_base_width, 'pressure': 1.0} 
                          for x, y in self._preview_points],
                'color': (255, 255, 255),
                'width': self._current_base_width,
                'tool': self._current_tool,
                'timestamp': time.time()
            }
            
            self._world_strokes.append(shape_stroke)
            
            logger.info("Completed shape: %s with %d points in world coordinates", 
                       self._current_tool, len(self._preview_points))
            
        except Exception as e:
            logger.error("Error completing shape: %s", e)
    
    def _reset_drawing_state(self) -> None:
        """Reset all drawing state."""
        self._is_drawing = False
        self._dynamic_stroke_points = []
        self._shape_start_pos = None
        self._shape_current_pos = None
        self._preview_points = []
    
    def render(self, screen_surface) -> None:
        """CRITICAL FIX: Render everything based on current viewport position."""
        try:
            if not screen_surface:
                return
            
            # Clear screen
            screen_surface.fill((0, 0, 0))
            
            # Layer 1: Generate infinite grid based on viewport
            self._generate_infinite_grid()
            if self.background_surface:
                screen_surface.blit(self.background_surface, (0, 0))
            
            # Layer 2: Render all world strokes based on viewport
            self._render_world_strokes(screen_surface)
            
            # Layer 3: Render live preview
            self._render_live_preview(screen_surface)
            
            # Layer 4: UI overlay
            if self.ui_surface:
                screen_surface.blit(self.ui_surface, (0, 0))
            
        except Exception as e:
            logger.error("Error in render: %s", e)
    
    def _render_world_strokes(self, screen_surface) -> None:
        """CRITICAL FIX: Render all world strokes based on viewport position."""
        try:
            import pygame
            
            for stroke in self._world_strokes:
                try:
                    points = stroke['points']
                    color = stroke['color']
                    width = stroke.get('width', 3)
                    tool = stroke.get('tool', 'brush')
                    
                    if not points:
                        continue
                    
                    # Convert world coordinates to screen coordinates
                    screen_points = []
                    for point in points:
                        world_x = point['x']
                        world_y = point['y']
                        screen_x = world_x - self._viewport_x
                        screen_y = world_y - self._viewport_y
                        
                        # Only include points that might be visible (with margin)
                        if (-100 <= screen_x <= self.screen_width + 100 and 
                            -100 <= screen_y <= self.screen_height + 100):
                            screen_points.append((screen_x, screen_y))
                    
                    if len(screen_points) < 2:
                        if len(screen_points) == 1:
                            # Single point
                            pygame.draw.circle(screen_surface, color, screen_points[0], max(1, width // 2))
                        continue
                    
                    # Render stroke
                    if tool == 'eraser':
                        # Skip rendering eraser strokes as they've already been applied
                        continue
                    elif tool == 'parabola':
                        # Continuous line for parabola
                        for i in range(len(screen_points) - 1):
                            start = screen_points[i]
                            end = screen_points[i + 1]
                            pygame.draw.line(screen_surface, color, start, end, max(1, width))
                            if width > 1:
                                pygame.draw.circle(screen_surface, color, start, width // 2)
                                pygame.draw.circle(screen_surface, color, end, width // 2)
                    else:
                        # Regular stroke or shape
                        if tool in ['line', 'rect', 'circle', 'triangle']:
                            # Paired segments for shapes
                            for i in range(0, len(screen_points), 2):
                                if i + 1 < len(screen_points):
                                    start = screen_points[i]
                                    end = screen_points[i + 1]
                                    pygame.draw.line(screen_surface, color, start, end, max(1, width))
                                    if width > 1:
                                        pygame.draw.circle(screen_surface, color, start, width // 2)
                                        pygame.draw.circle(screen_surface, color, end, width // 2)
                        else:
                            # Brush stroke
                            for i in range(len(screen_points) - 1):
                                start = screen_points[i]
                                end = screen_points[i + 1]
                                pygame.draw.line(screen_surface, color, start, end, max(1, width))
                                if width > 1:
                                    pygame.draw.circle(screen_surface, color, start, width // 2)
                                    pygame.draw.circle(screen_surface, color, end, width // 2)
                    
                except Exception as e:
                    logger.debug("Error rendering stroke: %s", e)
                    continue
                    
        except Exception as e:
            logger.error("Error rendering world strokes: %s", e)
    
    def _render_live_preview(self, screen_surface) -> None:
        """Render live preview with viewport transformation."""
        try:
            import pygame
            
            if self._is_drawing and not self._is_panning:
                if self._current_tool in ['line', 'rect', 'circle', 'triangle', 'parabola']:
                    # Shape preview
                    if self._preview_points:
                        preview_color = (128, 128, 255)
                        preview_width = max(1, self._current_base_width)
                        
                        # Convert world coordinates to screen coordinates
                        screen_points = []
                        for world_x, world_y in self._preview_points:
                            screen_x = world_x - self._viewport_x
                            screen_y = world_y - self._viewport_y
                            screen_points.append((screen_x, screen_y))
                        
                        if self._current_tool == 'parabola':
                            # Continuous preview
                            for i in range(len(screen_points) - 1):
                                start = screen_points[i]
                                end = screen_points[i + 1]
                                pygame.draw.line(screen_surface, preview_color, start, end, preview_width)
                                if preview_width > 1:
                                    pygame.draw.circle(screen_surface, preview_color, start, preview_width // 2)
                                    pygame.draw.circle(screen_surface, preview_color, end, preview_width // 2)
                        else:
                            # Paired segments
                            for i in range(0, len(screen_points), 2):
                                if i + 1 < len(screen_points):
                                    start = screen_points[i]
                                    end = screen_points[i + 1]
                                    pygame.draw.line(screen_surface, preview_color, start, end, preview_width)
                                    if preview_width > 1:
                                        pygame.draw.circle(screen_surface, preview_color, start, preview_width // 2)
                                        pygame.draw.circle(screen_surface, preview_color, end, preview_width // 2)
                
                elif self._dynamic_stroke_points and len(self._dynamic_stroke_points) > 1:
                    # Live stroke preview
                    color = self.canvas._current_brush_color
                    
                    if self._current_tool == 'eraser':
                        # Translucent red eraser preview
                        preview_surface = pygame.Surface(screen_surface.get_size(), pygame.SRCALPHA)
                        translucent_red = (255, 100, 100, 128)
                        
                        for i in range(len(self._dynamic_stroke_points) - 1):
                            point1 = self._dynamic_stroke_points[i]
                            point2 = self._dynamic_stroke_points[i + 1]
                            
                            width = max(1, int((point1['width'] + point2['width']) / 2))
                            
                            # Convert world to screen coordinates
                            start_pos = (
                                int(point1['x'] - self._viewport_x),
                                int(point1['y'] - self._viewport_y)
                            )
                            end_pos = (
                                int(point2['x'] - self._viewport_x),
                                int(point2['y'] - self._viewport_y)
                            )
                            
                            pygame.draw.line(preview_surface, translucent_red, start_pos, end_pos, width)
                            if width > 1:
                                pygame.draw.circle(preview_surface, translucent_red, start_pos, width // 2)
                                pygame.draw.circle(preview_surface, translucent_red, end_pos, width // 2)
                        
                        screen_surface.blit(preview_surface, (0, 0))
                    else:
                        # Regular brush preview
                        for i in range(len(self._dynamic_stroke_points) - 1):
                            point1 = self._dynamic_stroke_points[i]
                            point2 = self._dynamic_stroke_points[i + 1]
                            
                            width = max(1, int((point1['width'] + point2['width']) / 2))
                            
                            # Convert world to screen coordinates
                            start_pos = (
                                int(point1['x'] - self._viewport_x),
                                int(point1['y'] - self._viewport_y)
                            )
                            end_pos = (
                                int(point2['x'] - self._viewport_x),
                                int(point2['y'] - self._viewport_y)
                            )
                            
                            pygame.draw.line(screen_surface, color, start_pos, end_pos, width)
                            if width > 1:
                                pygame.draw.circle(screen_surface, color, start_pos, width // 2)
                                pygame.draw.circle(screen_surface, color, end_pos, width // 2)
            
        except Exception as e:
            logger.error("Error rendering live preview: %s", e)
    
    def clear_canvas(self) -> None:
        """Clear all world strokes."""
        try:
            self._world_strokes.clear()
            self._reset_drawing_state()
            logger.info("Cleared all world strokes")
            
        except Exception as e:
            logger.error("Error clearing canvas: %s", e)
    
    def handle_key_press(self, key: str) -> bool:
        """Handle key press events."""
        if key == 'space':
            tools = ['brush', 'eraser', 'line', 'rect', 'circle', 'triangle', 'parabola']
            try:
                current_index = tools.index(self._current_tool)
                next_tool = tools[(current_index + 1) % len(tools)]
                self._current_tool = next_tool
                self.bus.publish('tool_changed', next_tool)
                return True
            except ValueError:
                self._current_tool = 'brush'
                return True
        elif key == 'c':
            self.clear_canvas()
            return True
        elif key in '12345':
            colors = {
                '1': (57, 255, 20),   # Neon Green
                '2': (0, 255, 255),   # Neon Blue
                '3': (255, 20, 147),  # Neon Pink
                '4': (255, 255, 0),   # Neon Yellow
                '5': (255, 97, 3),    # Neon Orange
            }
            if key in colors:
                self.canvas.set_brush_color(colors[key])
                return True
        elif key in ['+', '=']:
            self._current_base_width = min(self._current_base_width + 1, 50)
            self.bus.publish('brush_width_changed', self._current_base_width)
            return True
        elif key in ['-', '_']:
            self._current_base_width = max(self._current_base_width - 1, 1)
            self.bus.publish('brush_width_changed', self._current_base_width)
            return True
        
        return False
    
    def get_current_tool(self) -> str:
        """Get current tool."""
        return self._current_tool
    
    def get_current_brush_width(self) -> int:
        """Get current universal brush width."""
        return self._current_base_width
    
    def is_drawing(self) -> bool:
        """Check if currently drawing."""
        return self._is_drawing
    
    def is_panning(self) -> bool:
        """Check if currently panning."""
        return self._is_panning
    
    def get_viewport_position(self) -> Tuple[int, int]:
        """Get current viewport position in world space."""
        return (self._viewport_x, self._viewport_y)
    
    def get_stroke_count(self) -> int:
        """Get total stroke count."""
        return len(self._world_strokes)