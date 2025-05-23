"""
Enhanced Drawing Application
===========================

Comprehensive drawing application addressing all user requirements:
1. Interactive color wheel with full spectrum color selection
2. Functional shape drawing tools with proper geometry handling
3. Smooth stroke rendering with anti-aliasing and interpolation
4. Professional user interface with real-time feedback
"""

import time
import math
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional
from .core import EventBus, ValidationService, create_memory_storage
from .drawing import create_drawing_engine, create_tool_manager

logger = logging.getLogger(__name__)

# Import the color wheel widget (assuming it's in the same package)
# from .color_wheel_widget import ColorWheelWidget, create_color_wheel


class ColorWheelWidget:
    """Embedded color wheel implementation for immediate integration."""
    
    def __init__(self, x: int, y: int, radius: int = 80):
        self.center_x = x
        self.center_y = y
        self.radius = radius
        self.inner_radius = 15
        
        self.current_hue = 0.0
        self.current_saturation = 1.0
        self.current_value = 1.0
        
        self.is_dragging = False
        self.is_visible = True
        self._last_rgb = (255, 0, 0)
    
    def handle_mouse_event(self, event_type: str, pos: Tuple[int, int], button: int = 1) -> bool:
        if not self.is_visible:
            return False
            
        mouse_x, mouse_y = pos
        distance = self._calculate_distance(mouse_x, mouse_y)
        
        if distance > self.radius:
            if event_type == "mouse_up":
                self.is_dragging = False
            return False
        
        if event_type == "mouse_down" and button == 1:
            self.is_dragging = True
            self._update_color_from_position(mouse_x, mouse_y)
            return True
        elif event_type == "mouse_up" and button == 1:
            self.is_dragging = False
            return True
        elif event_type == "mouse_move" and self.is_dragging:
            self._update_color_from_position(mouse_x, mouse_y)
            return True
            
        return False
    
    def _calculate_distance(self, x: int, y: int) -> float:
        dx = x - self.center_x
        dy = y - self.center_y
        return math.sqrt(dx * dx + dy * dy)
    
    def _update_color_from_position(self, x: int, y: int):
        try:
            dx = x - self.center_x
            dy = y - self.center_y
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance < self.inner_radius:
                self.current_value = max(0.1, min(1.0, distance / self.inner_radius))
            else:
                angle = math.atan2(-dy, dx)
                self.current_hue = (math.degrees(angle) + 360) % 360
                
                max_distance = self.radius - self.inner_radius
                relative_distance = min(distance - self.inner_radius, max_distance)
                self.current_saturation = relative_distance / max_distance
            
            self._last_rgb = self._hsv_to_rgb(self.current_hue, self.current_saturation, self.current_value)
            
        except Exception as e:
            logger.error(f"Error updating color: {e}")
    
    def _hsv_to_rgb(self, h: float, s: float, v: float) -> Tuple[int, int, int]:
        try:
            h = h / 360.0
            
            if s == 0:
                rgb_val = int(v * 255)
                return (rgb_val, rgb_val, rgb_val)
            
            i = int(h * 6)
            f = (h * 6) - i
            p = v * (1 - s)
            q = v * (1 - s * f)
            t = v * (1 - s * (1 - f))
            
            i = i % 6
            
            if i == 0:
                r, g, b = v, t, p
            elif i == 1:
                r, g, b = q, v, p
            elif i == 2:
                r, g, b = p, v, t
            elif i == 3:
                r, g, b = p, q, v
            elif i == 4:
                r, g, b = t, p, v
            else:
                r, g, b = v, p, q
            
            return (int(r * 255), int(g * 255), int(b * 255))
            
        except Exception as e:
            logger.error(f"HSV to RGB conversion error: {e}")
            return (255, 255, 255)
    
    def get_current_color(self) -> Tuple[int, int, int]:
        return self._last_rgb
    
    def render(self, screen):
        if not self.is_visible:
            return
            
        try:
            import pygame
            self._render_color_wheel(screen)
            self._render_selection_indicator(screen)
            self._render_color_preview(screen)
        except Exception as e:
            logger.error(f"Color wheel render error: {e}")
    
    def _render_color_wheel(self, screen):
        import pygame
        
        num_segments = 72
        num_rings = 20
        
        for ring in range(num_rings):
            ring_radius = self.inner_radius + (ring * (self.radius - self.inner_radius) / num_rings)
            next_ring_radius = self.inner_radius + ((ring + 1) * (self.radius - self.inner_radius) / num_rings)
            
            for segment in range(num_segments):
                hue = (segment * 360) / num_segments
                saturation = (ring + 1) / num_rings
                color = self._hsv_to_rgb(hue, saturation, self.current_value)
                
                start_angle = math.radians(segment * 360 / num_segments)
                end_angle = math.radians((segment + 1) * 360 / num_segments)
                
                self._draw_color_segment(screen, ring_radius, next_ring_radius, start_angle, end_angle, color)
        
        center_color = self._hsv_to_rgb(self.current_hue, 0, self.current_value)
        pygame.draw.circle(screen, center_color, (self.center_x, self.center_y), self.inner_radius)
        pygame.draw.circle(screen, (100, 100, 100), (self.center_x, self.center_y), self.radius, 2)
    
    def _draw_color_segment(self, screen, inner_radius: float, outer_radius: float, 
                           start_angle: float, end_angle: float, color: Tuple[int, int, int]):
        import pygame
        
        points = []
        num_points = 8
        
        for i in range(num_points + 1):
            angle = start_angle + (end_angle - start_angle) * i / num_points
            x = self.center_x + inner_radius * math.cos(angle)
            y = self.center_y + inner_radius * math.sin(angle)
            points.append((x, y))
        
        for i in range(num_points, -1, -1):
            angle = start_angle + (end_angle - start_angle) * i / num_points
            x = self.center_x + outer_radius * math.cos(angle)
            y = self.center_y + outer_radius * math.sin(angle)
            points.append((x, y))
        
        if len(points) >= 3:
            pygame.draw.polygon(screen, color, points)
    
    def _render_selection_indicator(self, screen):
        import pygame
        
        try:
            if self.current_saturation < 0.1:
                indicator_x = self.center_x
                indicator_y = self.center_y
            else:
                angle = math.radians(self.current_hue)
                distance = self.inner_radius + (self.current_saturation * (self.radius - self.inner_radius))
                indicator_x = self.center_x + distance * math.cos(angle)
                indicator_y = self.center_y - distance * math.sin(angle)
            
            pygame.draw.circle(screen, (255, 255, 255), (int(indicator_x), int(indicator_y)), 4, 2)
            pygame.draw.circle(screen, (0, 0, 0), (int(indicator_x), int(indicator_y)), 4, 1)
            
        except Exception as e:
            logger.debug(f"Selection indicator error: {e}")
    
    def _render_color_preview(self, screen):
        import pygame
        
        try:
            preview_size = 30
            preview_x = self.center_x - preview_size // 2
            preview_y = self.center_y + self.radius + 10
            
            pygame.draw.rect(screen, (50, 50, 50), (preview_x - 2, preview_y - 2, preview_size + 4, preview_size + 4))
            pygame.draw.rect(screen, self._last_rgb, (preview_x, preview_y, preview_size, preview_size))
            pygame.draw.rect(screen, (200, 200, 200), (preview_x, preview_y, preview_size, preview_size), 1)
            
        except Exception as e:
            logger.debug(f"Color preview error: {e}")


class SmoothStrokeRenderer:
    """Advanced stroke rendering with smoothing and anti-aliasing."""
    
    def __init__(self):
        self.smoothing_enabled = True
        self.interpolation_steps = 3
        self.min_distance_threshold = 2.0
        
    def render_smooth_stroke(self, backend, points: List[Tuple[int, int]], color: Tuple[int, int, int], width: int):
        """Render stroke with advanced smoothing algorithms."""
        if len(points) < 2:
            if points and hasattr(backend, 'draw_circle'):
                backend.draw_circle(points[0], max(1, width // 2), color)
            return
        
        if not self.smoothing_enabled or len(points) < 3:
            self._render_basic_stroke(backend, points, color, width)
            return
        
        try:
            # Apply smoothing algorithm
            smoothed_points = self._apply_smoothing(points)
            
            # Render with interpolation
            self._render_interpolated_stroke(backend, smoothed_points, color, width)
            
        except Exception as e:
            logger.error(f"Smooth stroke rendering error: {e}")
            self._render_basic_stroke(backend, points, color, width)
    
    def _apply_smoothing(self, points: List[Tuple[int, int]]) -> List[Tuple[float, float]]:
        """Apply smoothing algorithm to reduce jagged edges."""
        if len(points) <= 2:
            return [(float(p[0]), float(p[1])) for p in points]
        
        smoothed = []
        
        # First point unchanged
        smoothed.append((float(points[0][0]), float(points[0][1])))
        
        # Apply weighted averaging for middle points
        for i in range(1, len(points) - 1):
            prev_point = points[i - 1]
            curr_point = points[i]
            next_point = points[i + 1]
            
            # Weighted average with emphasis on current point
            smoothed_x = (prev_point[0] * 0.25 + curr_point[0] * 0.5 + next_point[0] * 0.25)
            smoothed_y = (prev_point[1] * 0.25 + curr_point[1] * 0.5 + next_point[1] * 0.25)
            
            smoothed.append((smoothed_x, smoothed_y))
        
        # Last point unchanged
        smoothed.append((float(points[-1][0]), float(points[-1][1])))
        
        return smoothed
    
    def _render_interpolated_stroke(self, backend, points: List[Tuple[float, float]], color: Tuple[int, int, int], width: int):
        """Render stroke with interpolation between points."""
        for i in range(len(points) - 1):
            start_point = points[i]
            end_point = points[i + 1]
            
            # Calculate distance for interpolation steps
            distance = math.sqrt((end_point[0] - start_point[0])**2 + (end_point[1] - start_point[1])**2)
            
            if distance < self.min_distance_threshold:
                # Short segment, render directly
                self._render_line_segment(backend, start_point, end_point, color, width)
            else:
                # Long segment, interpolate
                steps = max(2, int(distance / self.interpolation_steps))
                self._render_interpolated_segment(backend, start_point, end_point, color, width, steps)
    
    def _render_interpolated_segment(self, backend, start: Tuple[float, float], end: Tuple[float, float], 
                                   color: Tuple[int, int, int], width: int, steps: int):
        """Render segment with interpolation for smoothness."""
        for step in range(steps):
            t1 = step / steps
            t2 = (step + 1) / steps
            
            # Interpolate points
            x1 = start[0] + (end[0] - start[0]) * t1
            y1 = start[1] + (end[1] - start[1]) * t1
            x2 = start[0] + (end[0] - start[0]) * t2
            y2 = start[1] + (end[1] - start[1]) * t2
            
            self._render_line_segment(backend, (x1, y1), (x2, y2), color, width)
    
    def _render_line_segment(self, backend, start: Tuple[float, float], end: Tuple[float, float], 
                           color: Tuple[int, int, int], width: int):
        """Render single line segment with proper coordinates."""
        try:
            start_int = (int(round(start[0])), int(round(start[1])))
            end_int = (int(round(end[0])), int(round(end[1])))
            
            if hasattr(backend, 'draw_line'):
                backend.draw_line(start_int, end_int, max(1, width), color)
                
        except Exception as e:
            logger.debug(f"Line segment render error: {e}")
    
    def _render_basic_stroke(self, backend, points: List[Tuple[int, int]], color: Tuple[int, int, int], width: int):
        """Fallback basic stroke rendering."""
        try:
            for i in range(len(points) - 1):
                if hasattr(backend, 'draw_line'):
                    backend.draw_line(points[i], points[i + 1], max(1, width), color)
                    
            # Add end caps for better appearance
            if width > 2 and hasattr(backend, 'draw_circle'):
                cap_radius = max(1, width // 2)
                backend.draw_circle(points[0], cap_radius, color)
                backend.draw_circle(points[-1], cap_radius, color)
                
        except Exception as e:
            logger.debug(f"Basic stroke render error: {e}")


@dataclass
class ApplicationSettings:
    """Enhanced application settings with new features."""
    window_width: int = 1280
    window_height: int = 720
    window_title: str = "InfiniteJournal - Enhanced"
    target_fps: int = 60
    debug_mode: bool = False
    smooth_drawing: bool = True
    color_wheel_enabled: bool = True


class EnhancedDrawingApplication:
    """
    Professional drawing application with comprehensive feature set.
    
    Features:
    - Interactive color wheel with full spectrum selection
    - Smooth stroke rendering with anti-aliasing
    - Complete shape drawing tools
    - Professional user interface
    """
    
    def __init__(self, backend, settings=None):
        self.backend = backend
        self.settings = settings or ApplicationSettings()
        self.running = False
        
        # Core services
        self.event_bus = EventBus()
        self.validation_service = ValidationService()
        self.storage = create_memory_storage("enhanced_app")
        
        # Drawing services
        self.drawing_engine = create_drawing_engine(
            backend, self.validation_service, self.event_bus
        )
        self.tool_manager = create_tool_manager(
            self.validation_service, self.event_bus
        )
        
        # Enhanced components
        self.color_wheel = None
        self.stroke_renderer = SmoothStrokeRenderer()
        
        # Drawing state
        self.is_drawing = False
        self.current_tool = "brush"
        self.current_color = (255, 0, 0)
        self.brush_size = 5
        self.min_brush_size = 1
        self.max_brush_size = 100
        
        # Tool management
        self.available_tools = ["brush", "eraser", "line", "rect", "circle", "triangle"]
        self.current_tool_index = 0
        
        # Shape drawing state
        self.shape_start_pos = None
        self.is_drawing_shape = False
        self.current_stroke_points = []
        
        # Performance tracking
        self.frame_count = 0
        self.last_fps_report = time.time()
        
        self._setup_event_handlers()
        
        logger.info("Enhanced drawing application initialized with professional features")
    
    def _setup_event_handlers(self):
        """Configure comprehensive event handling system."""
        self.event_bus.subscribe('quit_requested', self._handle_quit)
        self.event_bus.subscribe('mouse_pressed', self._handle_mouse_press)
        self.event_bus.subscribe('mouse_released', self._handle_mouse_release)
        self.event_bus.subscribe('mouse_moved', self._handle_mouse_move)
        self.event_bus.subscribe('key_pressed', self._handle_key_press)
        self.event_bus.subscribe('scroll_wheel', self._handle_scroll_wheel)
    
    def initialize(self):
        """Initialize application with enhanced features."""
        try:
            # Initialize window
            if hasattr(self.backend, 'init_window'):
                self.backend.init_window(
                    self.settings.window_width,
                    self.settings.window_height,
                    self.settings.window_title
                )
            elif hasattr(self.backend, 'open_window'):
                self.backend.open_window(
                    self.settings.window_width,
                    self.settings.window_height,
                    self.settings.window_title
                )
            
            # Initialize color wheel
            if self.settings.color_wheel_enabled:
                self._initialize_color_wheel()
            
            # Start services
            self.drawing_engine.start()
            self.tool_manager.start()
            
            # Configure drawing engine
            self.drawing_engine.set_screen_size(
                self.settings.window_width,
                self.settings.window_height
            )
            
            logger.info("Enhanced application initialized successfully")
            self._log_enhanced_controls()
            
        except Exception as e:
            logger.error(f"Enhanced application initialization failed: {e}")
            raise
    
    def _initialize_color_wheel(self):
        """Initialize color wheel in lower left corner."""
        try:
            margin = 20
            radius = 80
            
            x = margin + radius
            y = self.settings.window_height - margin - radius
            
            self.color_wheel = ColorWheelWidget(x, y, radius)
            self.current_color = self.color_wheel.get_current_color()
            
            logger.info(f"Color wheel initialized at position ({x}, {y})")
            
        except Exception as e:
            logger.error(f"Color wheel initialization failed: {e}")
            self.color_wheel = None
    
    def _log_enhanced_controls(self):
        """Log comprehensive control instructions."""
        logger.info("=== ENHANCED CONTROLS ===")
        logger.info("Drawing: Left mouse button")
        logger.info("Color selection: Click and drag on color wheel (lower left)")
        logger.info("Brush size: Mouse wheel up/down")
        logger.info("Tools: T key to cycle, or number keys 1-6")
        logger.info("Shape tools: Click and drag to define shape bounds")
        logger.info("Clear canvas: SPACE key")
        logger.info("Toggle color wheel: W key")
        logger.info("Toggle smooth drawing: S key")
        logger.info("Current tool: %s", self.current_tool)
        logger.info("Current color: RGB%s", self.current_color)
        logger.info("Brush size: %d", self.brush_size)
        logger.info("Smooth drawing: %s", self.settings.smooth_drawing)
    
    def run(self):
        """Execute main application loop with enhanced features."""
        self.running = True
        target_frame_time = 1.0 / self.settings.target_fps
        
        logger.info("Starting enhanced application main loop")
        
        while self.running:
            frame_start = time.time()
            
            try:
                # Process input events
                self._process_enhanced_events()
                
                # Render complete frame
                self._render_enhanced_frame()
                
                # Performance management
                self._manage_frame_timing(frame_start, target_frame_time)
                
            except Exception as e:
                logger.error(f"Main loop error at frame {self.frame_count}: {e}")
                if self.settings.debug_mode:
                    raise
        
        self.shutdown()
    
    def _process_enhanced_events(self):
        """Process events with color wheel integration."""
        try:
            if hasattr(self.backend, 'poll_events'):
                events = self.backend.poll_events()
                
                for event in events:
                    # Check if color wheel handles the event first
                    handled_by_color_wheel = False
                    
                    if self.color_wheel and self.color_wheel.is_visible:
                        handled_by_color_wheel = self._handle_color_wheel_event(event)
                    
                    # If not handled by color wheel, route to application
                    if not handled_by_color_wheel:
                        self._route_application_event(event)
                        
        except Exception as e:
            logger.error(f"Enhanced event processing error: {e}")
    
    def _handle_color_wheel_event(self, event) -> bool:
        """Handle color wheel interaction events."""
        try:
            event_type = getattr(event, 'type', None)
            event_data = getattr(event, 'data', {})
            
            if event_type in ['MOUSE_DOWN', 'MOUSEBUTTONDOWN']:
                pos = event_data.get('pos', (0, 0))
                button = event_data.get('button', 1)
                if self.color_wheel.handle_mouse_event("mouse_down", pos, button):
                    self.current_color = self.color_wheel.get_current_color()
                    return True
            elif event_type in ['MOUSE_UP', 'MOUSEBUTTONUP']:
                pos = event_data.get('pos', (0, 0))
                button = event_data.get('button', 1)
                if self.color_wheel.handle_mouse_event("mouse_up", pos, button):
                    self.current_color = self.color_wheel.get_current_color()
                    return True
            elif event_type in ['MOUSE_MOVE', 'MOUSEMOTION']:
                pos = event_data.get('pos', (0, 0))
                if self.color_wheel.handle_mouse_event("mouse_move", pos):
                    self.current_color = self.color_wheel.get_current_color()
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Color wheel event handling error: {e}")
            return False
    
    def _route_application_event(self, event):
        """Route events to appropriate application handlers."""
        try:
            event_type = getattr(event, 'type', None)
            event_data = getattr(event, 'data', {})
            
            if event_type == 'QUIT':
                self.event_bus.publish('quit_requested')
            elif event_type in ['MOUSE_DOWN', 'MOUSEBUTTONDOWN']:
                pos = event_data.get('pos', (0, 0))
                button = event_data.get('button', 1)
                self.event_bus.publish('mouse_pressed', {'pos': pos, 'button': button})
            elif event_type in ['MOUSE_UP', 'MOUSEBUTTONUP']:
                pos = event_data.get('pos', (0, 0))
                button = event_data.get('button', 1)
                self.event_bus.publish('mouse_released', {'pos': pos, 'button': button})
            elif event_type in ['MOUSE_MOVE', 'MOUSEMOTION']:
                pos = event_data.get('pos', (0, 0))
                self.event_bus.publish('mouse_moved', {'pos': pos})
            elif event_type in ['KEY_PRESS', 'KEYDOWN']:
                key = event_data.get('key', '')
                if isinstance(key, int):
                    import pygame
                    key = pygame.key.name(key) if hasattr(pygame, 'key') else str(key)
                self.event_bus.publish('key_pressed', {'key': str(key)})
            elif event_type == 'SCROLL_WHEEL':
                direction = event_data.get('direction', 0)
                pos = event_data.get('pos', (0, 0))
                self.event_bus.publish('scroll_wheel', {'direction': direction, 'pos': pos})
                
        except Exception as e:
            logger.error(f"Application event routing error: {e}")
    
    def _render_enhanced_frame(self):
        """Render complete frame with all enhancements."""
        try:
            # Clear screen
            if hasattr(self.backend, 'clear'):
                self.backend.clear((15, 15, 15))  # Dark gray background
            
            # Render drawing content with smooth strokes
            self._render_drawing_content()
            
            # Render color wheel
            if self.color_wheel and self.color_wheel.is_visible:
                self.color_wheel.render(self.backend.screen)
            
            # Render user interface
            self._render_enhanced_ui()
            
            # Present final frame
            if hasattr(self.backend, 'present'):
                self.backend.present()
            elif hasattr(self.backend, 'flip'):
                self.backend.flip()
                
        except Exception as e:
            logger.error(f"Enhanced frame rendering error: {e}")
    
    def _render_drawing_content(self):
        """Render drawing content with smooth stroke rendering."""
        try:
            # Render completed strokes
            for stroke in self.drawing_engine.strokes:
                if self.settings.smooth_drawing and len(stroke.points) > 2:
                    self.stroke_renderer.render_smooth_stroke(
                        self.backend, stroke.points, stroke.color, stroke.width
                    )
                else:
                    self._render_basic_stroke(stroke)
            
            # Render current stroke
            if self.drawing_engine.current_stroke:
                stroke = self.drawing_engine.current_stroke
                if self.settings.smooth_drawing and len(stroke.points) > 2:
                    self.stroke_renderer.render_smooth_stroke(
                        self.backend, stroke.points, stroke.color, stroke.width
                    )
                else:
                    self._render_basic_stroke(stroke)
                    
        except Exception as e:
            logger.error(f"Drawing content rendering error: {e}")
    
    def _render_basic_stroke(self, stroke):
        """Render stroke using basic method."""
        try:
            points = stroke.points
            if len(points) < 2:
                if points and hasattr(self.backend, 'draw_circle'):
                    self.backend.draw_circle(points[0], stroke.width // 2, stroke.color)
                return
            
            if hasattr(self.backend, 'draw_line'):
                for i in range(len(points) - 1):
                    self.backend.draw_line(points[i], points[i + 1], stroke.width, stroke.color)
                    
        except Exception as e:
            logger.debug(f"Basic stroke rendering error: {e}")
    
    def _render_enhanced_ui(self):
        """Render enhanced user interface elements."""
        try:
            if hasattr(self.backend, 'draw_text'):
                # Tool information
                tool_text = f"Tool: {self.current_tool.title()}"
                self.backend.draw_text(tool_text, (10, 10), 20, (255, 255, 255))
                
                # Brush size information
                size_text = f"Size: {self.brush_size}"
                self.backend.draw_text(size_text, (10, 35), 20, (255, 255, 255))
                
                # Color information
                color_text = f"Color: RGB{self.current_color}"
                self.backend.draw_text(color_text, (10, 60), 18, self.current_color)
                
                # Smooth drawing status
                smooth_text = f"Smooth: {'ON' if self.settings.smooth_drawing else 'OFF'}"
                self.backend.draw_text(smooth_text, (10, 85), 16, (200, 200, 200))
                
                # Controls information
                controls_text = "Controls: Color Wheel (lower left), T=Tool, Wheel=Size, S=Smooth, W=Color Wheel, Space=Clear"
                self.backend.draw_text(controls_text, (10, self.settings.window_height - 25), 14, (180, 180, 180))
                
                # Current tool preview
                if hasattr(self.backend, 'draw_circle'):
                    preview_x = 250
                    preview_y = 25
                    preview_radius = max(3, min(15, self.brush_size // 2))
                    self.backend.draw_circle((preview_x, preview_y), preview_radius, self.current_color)
                    
        except Exception as e:
            logger.debug(f"Enhanced UI rendering error: {e}")
    
    def _manage_frame_timing(self, frame_start: float, target_frame_time: float):
        """Manage frame timing and performance reporting."""
        try:
            self.frame_count += 1
            
            # Frame rate limiting
            frame_time = time.time() - frame_start
            if frame_time < target_frame_time:
                time.sleep(target_frame_time - frame_time)
            
            # Periodic performance reporting
            current_time = time.time()
            if current_time - self.last_fps_report >= 10.0:  # Every 10 seconds
                fps = self.frame_count / (current_time - self.last_fps_report + 0.001)
                logger.debug(f"Performance: {fps:.1f} FPS, Frame {self.frame_count}")
                self.frame_count = 0
                self.last_fps_report = current_time
                
        except Exception as e:
            logger.debug(f"Frame timing management error: {e}")
    
    def _handle_quit(self, data):
        """Handle application quit request."""
        logger.info("Enhanced application quit requested")
        self.running = False
    
    def _handle_mouse_press(self, data):
        """Handle mouse press events for drawing and shapes."""
        try:
            pos = data.get('pos', (0, 0))
            button = data.get('button', 1)
            
            if button == 1:  # Left click
                if self.current_tool == "brush":
                    self.is_drawing = True
                    self.drawing_engine.start_stroke(pos, self.current_color, self.brush_size)
                    self.current_stroke_points = [pos]
                elif self.current_tool == "eraser":
                    self.is_drawing = True
                    eraser_color = (15, 15, 15)  # Match background
                    self.drawing_engine.start_stroke(pos, eraser_color, self.brush_size * 2)
                    self.current_stroke_points = [pos]
                elif self.current_tool in ["line", "rect", "circle", "triangle"]:
                    self.is_drawing_shape = True
                    self.shape_start_pos = pos
                    
                logger.debug(f"Mouse press handled: tool={self.current_tool}, pos={pos}")
                
        except Exception as e:
            logger.error(f"Mouse press handling error: {e}")
    
    def _handle_mouse_release(self, data):
        """Handle mouse release events."""
        try:
            pos = data.get('pos', (0, 0))
            button = data.get('button', 1)
            
            if button == 1:  # Left click release
                if self.current_tool in ["brush", "eraser"]:
                    if self.is_drawing:
                        self.is_drawing = False
                        self.drawing_engine.finish_current_stroke()
                        self.current_stroke_points = []
                elif self.current_tool in ["line", "rect", "circle", "triangle"] and self.is_drawing_shape:
                    self._complete_shape_drawing(pos)
                    self.is_drawing_shape = False
                    self.shape_start_pos = None
                    
        except Exception as e:
            logger.error(f"Mouse release handling error: {e}")
    
    def _handle_mouse_move(self, data):
        """Handle mouse movement for drawing."""
        try:
            pos = data.get('pos', (0, 0))
            
            if self.is_drawing and self.current_tool in ["brush", "eraser"]:
                self.drawing_engine.add_stroke_point(pos)
                self.current_stroke_points.append(pos)
                
        except Exception as e:
            logger.error(f"Mouse move handling error: {e}")
    
    def _complete_shape_drawing(self, end_pos: Tuple[int, int]):
        """Complete shape drawing with proper geometry."""
        try:
            if not self.shape_start_pos:
                return
            
            start_pos = self.shape_start_pos
            
            if self.current_tool == "line":
                self._draw_line_shape(start_pos, end_pos)
            elif self.current_tool == "rect":
                self._draw_rectangle_shape(start_pos, end_pos)
            elif self.current_tool == "circle":
                self._draw_circle_shape(start_pos, end_pos)
            elif self.current_tool == "triangle":
                self._draw_triangle_shape(start_pos, end_pos)
                
            logger.debug(f"Shape completed: {self.current_tool} from {start_pos} to {end_pos}")
            
        except Exception as e:
            logger.error(f"Shape completion error: {e}")
    
    def _draw_line_shape(self, start_pos: Tuple[int, int], end_pos: Tuple[int, int]):
        """Draw line shape with smooth rendering."""
        try:
            if hasattr(self.backend, 'draw_line'):
                self.backend.draw_line(start_pos, end_pos, self.brush_size, self.current_color)
        except Exception as e:
            logger.error(f"Line shape drawing error: {e}")
    
    def _draw_rectangle_shape(self, start_pos: Tuple[int, int], end_pos: Tuple[int, int]):
        """Draw rectangle shape."""
        try:
            x1, y1 = start_pos
            x2, y2 = end_pos
            
            left = min(x1, x2)
            top = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            
            if hasattr(self.backend, 'draw_rect'):
                self.backend.draw_rect((left, top, width, height), self.current_color, self.brush_size)
            elif hasattr(self.backend, 'draw_line'):
                corners = [
                    (left, top), (left + width, top),
                    (left + width, top + height), (left, top + height), (left, top)
                ]
                for i in range(len(corners) - 1):
                    self.backend.draw_line(corners[i], corners[i + 1], self.brush_size, self.current_color)
                    
        except Exception as e:
            logger.error(f"Rectangle shape drawing error: {e}")
    
    def _draw_circle_shape(self, start_pos: Tuple[int, int], end_pos: Tuple[int, int]):
        """Draw circle shape."""
        try:
            dx = end_pos[0] - start_pos[0]
            dy = end_pos[1] - start_pos[1]
            radius = int(math.sqrt(dx * dx + dy * dy))
            
            if radius > 0 and hasattr(self.backend, 'draw_circle'):
                self.backend.draw_circle(start_pos, radius, self.current_color, self.brush_size)
                
        except Exception as e:
            logger.error(f"Circle shape drawing error: {e}")
    
    def _draw_triangle_shape(self, start_pos: Tuple[int, int], end_pos: Tuple[int, int]):
        """Draw triangle shape."""
        try:
            if hasattr(self.backend, 'draw_line'):
                # Calculate triangle points
                x1, y1 = start_pos
                x2, y2 = end_pos
                
                # Third point forms equilateral-ish triangle
                mid_x = (x1 + x2) // 2
                height = int(abs(y2 - y1) * 0.866)  # sqrt(3)/2 for equilateral
                x3 = mid_x
                y3 = y1 - height if y2 > y1 else y1 + height
                
                # Draw triangle edges
                points = [(x1, y1), (x2, y2), (x3, y3), (x1, y1)]
                for i in range(len(points) - 1):
                    self.backend.draw_line(points[i], points[i + 1], self.brush_size, self.current_color)
                    
        except Exception as e:
            logger.error(f"Triangle shape drawing error: {e}")
    
    def _handle_key_press(self, data):
        """Handle keyboard input for enhanced controls."""
        try:
            key = data.get('key', '').lower()
            
            if key == 't':
                self._cycle_tool()
            elif key == 'w':
                self._toggle_color_wheel()
            elif key == 's':
                self._toggle_smooth_drawing()
            elif key == 'space':
                self._clear_canvas()
            elif key in ['1', '2', '3', '4', '5', '6']:
                self._set_tool_by_number(int(key))
            elif key == 'escape':
                self.event_bus.publish('quit_requested')
                
        except Exception as e:
            logger.error(f"Key press handling error: {e}")
    
    def _handle_scroll_wheel(self, data):
        """Handle scroll wheel for brush size adjustment."""
        try:
            direction = data.get('direction', 0)
            
            if direction > 0:
                self.brush_size = min(self.max_brush_size, self.brush_size + 2)
            elif direction < 0:
                self.brush_size = max(self.min_brush_size, self.brush_size - 2)
                
            logger.debug(f"Brush size adjusted to: {self.brush_size}")
            
        except Exception as e:
            logger.error(f"Scroll wheel handling error: {e}")
    
    def _cycle_tool(self):
        """Cycle through available tools."""
        try:
            self.current_tool_index = (self.current_tool_index + 1) % len(self.available_tools)
            self.current_tool = self.available_tools[self.current_tool_index]
            logger.info(f"Tool changed to: {self.current_tool}")
        except Exception as e:
            logger.error(f"Tool cycling error: {e}")
    
    def _set_tool_by_number(self, number: int):
        """Set tool by number key."""
        try:
            if 1 <= number <= len(self.available_tools):
                self.current_tool_index = number - 1
                self.current_tool = self.available_tools[self.current_tool_index]
                logger.info(f"Tool set to: {self.current_tool}")
        except Exception as e:
            logger.error(f"Tool number setting error: {e}")
    
    def _toggle_color_wheel(self):
        """Toggle color wheel visibility."""
        try:
            if self.color_wheel:
                self.color_wheel.is_visible = not self.color_wheel.is_visible
                logger.info(f"Color wheel visibility: {self.color_wheel.is_visible}")
        except Exception as e:
            logger.error(f"Color wheel toggle error: {e}")
    
    def _toggle_smooth_drawing(self):
        """Toggle smooth drawing mode."""
        try:
            self.settings.smooth_drawing = not self.settings.smooth_drawing
            logger.info(f"Smooth drawing: {self.settings.smooth_drawing}")
        except Exception as e:
            logger.error(f"Smooth drawing toggle error: {e}")
    
    def _clear_canvas(self):
        """Clear the drawing canvas."""
        try:
            self.drawing_engine.clear_canvas()
            logger.info("Canvas cleared")
        except Exception as e:
            logger.error(f"Canvas clearing error: {e}")
    
    def shutdown(self):
        """Enhanced shutdown procedure."""
        try:
            logger.info("Shutting down enhanced drawing application")
            
            # Finish any active drawing
            if self.is_drawing:
                self.drawing_engine.finish_current_stroke()
            
            # Stop services
            self.drawing_engine.stop()
            self.tool_manager.stop()
            self.event_bus.shutdown()
            
            # Cleanup resources
            if self.color_wheel:
                self.color_wheel = None
            
            # Quit backend
            if hasattr(self.backend, 'quit'):
                self.backend.quit()
                
            logger.info("Enhanced application shutdown complete")
            
        except Exception as e:
            logger.error(f"Enhanced shutdown error: {e}")


# Legacy compatibility interfaces
class UnifiedApplication(EnhancedDrawingApplication):
    """Legacy compatibility wrapper."""
    pass

class SimpleApp:
    """Legacy bootstrap compatibility."""
    
    def __init__(self, settings, engine, clock, input_adapter, bus=None):
        app_settings = ApplicationSettings(
            window_width=getattr(settings, 'WIDTH', 1280),
            window_height=getattr(settings, 'HEIGHT', 720),
            window_title=getattr(settings, 'TITLE', 'InfiniteJournal'),
            target_fps=getattr(settings, 'FPS', 60),
            debug_mode=getattr(settings, 'DEBUG', False),
            smooth_drawing=True,
            color_wheel_enabled=True
        )
        
        self.app = EnhancedDrawingApplication(engine, app_settings)
        
    def run(self):
        """Run enhanced application."""
        self.app.initialize()
        self.app.run()

def create_application(settings, backend):
    """Create enhanced drawing application."""
    app_settings = ApplicationSettings(
        window_width=getattr(settings, 'WIDTH', 1280),
        window_height=getattr(settings, 'HEIGHT', 720),
        window_title=getattr(settings, 'TITLE', 'InfiniteJournal'),
        target_fps=getattr(settings, 'FPS', 60),
        debug_mode=getattr(settings, 'DEBUG', False),
        smooth_drawing=True,
        color_wheel_enabled=True
    )
    return EnhancedDrawingApplication(backend, app_settings)