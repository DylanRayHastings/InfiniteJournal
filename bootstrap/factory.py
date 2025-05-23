# bootstrap/factory.py (UPDATED - Enhanced application composition)
"""
Enhanced Application Factory with Architectural Integration

Composes application with new architectural systems:
- Layered rendering system
- Hierarchical coordinate system
- Shape preview system
- Mathematical curve generation
"""

from pathlib import Path
import logging
from core.event_bus import EventBus
from .adapters import load_adapters
from .database import init_database
from .services import init_services
from .widgets import init_widgets
from .errors import StartupError
from icecream import ic

# Import enhanced systems
from core.coordinates.infinite_system import CoordinateManager
from core.preview.shape_preview import ShapePreviewSystem
from core.math.curve_generation import CurveGenerationFramework

logger = logging.getLogger(__name__)


def compose_enhanced_app(settings, bus=None):
    """Compose and return the fully enhanced App instance with architectural systems."""
    bus = bus or EventBus()
    Path(settings.DATA_PATH).mkdir(parents=True, exist_ok=True)

    try:
        # Load enhanced adapters
        engine, clock, input_adapter = load_adapters()
        
        # Initialize enhanced adapters if available
        if hasattr(engine, '_initialize_architectural_systems'):
            logger.info("Enhanced pygame adapter detected")
        
        # Initialize database
        database = init_database(settings.DATABASE_URL)
        
        # Initialize services with architectural integration
        repo, exporter, tool_service, journal_service, undo_service = init_enhanced_services(
            settings.DATA_PATH, settings, bus, database, engine
        )
        
        # Ensure tool service starts with correct default tool
        if tool_service.current_tool_mode not in settings.VALID_TOOLS:
            tool_service.set_mode("brush")
        
        # Initialize enhanced widgets
        widgets = init_enhanced_widgets(journal_service, engine, bus, clock, settings, tool_service)

        # Import and create enhanced app
        from services.app import EnhancedApp
        app = EnhancedApp(
            settings=settings,
            engine=engine,
            clock=clock,
            input_adapter=input_adapter,
            journal_service=journal_service,
            tool_service=tool_service,
            undo_service=undo_service,
            repository=repo,
            exporter=exporter,
            widgets=widgets,
            bus=bus,
        )
        
        if settings.DEBUG:
            ic(app)
            
        logger.info("Enhanced application composed successfully with tool: %s", 
                   tool_service.current_tool_mode)
        return app
        
    except Exception as e:
        logger.error("Failed to compose enhanced app: %s", e)
        raise StartupError(f"Enhanced app composition failed: {e}") from e


def init_enhanced_services(data_path, settings, bus, database, engine):
    """Initialize services with architectural system integration."""
    try:
        from adapters.fs_adapter import FileSystemJournalRepository, ScreenshotExporter
        from services.tools import ToolService
        from services.undo import UndoRedoService
        
        # Import enhanced journal service
        from services.journal import EnhancedJournalService
        
        # Initialize basic services
        repo = FileSystemJournalRepository(data_path)
        exporter = ScreenshotExporter(data_path)
        tool_service = ToolService(settings=settings, bus=bus)
        undo_service = UndoRedoService(bus=bus)
        
        # Initialize architectural systems
        coordinate_manager = None
        preview_system = None
        curve_framework = CurveGenerationFramework()
        
        # Extract systems from enhanced engine if available
        if hasattr(engine, 'coordinate_manager') and engine.coordinate_manager:
            coordinate_manager = engine.coordinate_manager
            logger.info("Using engine's coordinate manager")
            
        if hasattr(engine, 'preview_system') and engine.preview_system:
            preview_system = engine.preview_system
            logger.info("Using engine's preview system")
        else:
            # Create standalone preview system
            try:
                preview_system = ShapePreviewSystem(settings.WIDTH, settings.HEIGHT)
                logger.info("Created standalone preview system")
            except Exception as e:
                logger.warning("Failed to create preview system: %s", e)
        
        # Initialize enhanced journal service
        journal_service = EnhancedJournalService(
            bus=bus, 
            tool_service=tool_service, 
            database=database,
            coordinate_manager=coordinate_manager,
            preview_system=preview_system,
            curve_framework=curve_framework
        )
        
        logger.info("Enhanced services initialized successfully")
        return repo, exporter, tool_service, journal_service, undo_service
        
    except ImportError as e:
        logger.warning("Enhanced services not available, using legacy: %s", e)
        # Fallback to legacy services
        return init_legacy_services(data_path, settings, bus, database)
    except Exception as e:
        logger.error("Error initializing enhanced services: %s", e)
        raise StartupError(f"Enhanced service initialization failed: {e}") from e


def init_legacy_services(data_path, settings, bus, database):
    """Initialize legacy services as fallback."""
    try:
        from adapters.fs_adapter import FileSystemJournalRepository, ScreenshotExporter
        from services.tools import ToolService
        from services.journal import JournalService
        from services.undo import UndoRedoService
        
        repo = FileSystemJournalRepository(data_path)
        exporter = ScreenshotExporter(data_path)
        tool_service = ToolService(settings=settings, bus=bus)
        journal_service = JournalService(bus=bus, tool_service=tool_service, database=database)
        undo_service = UndoRedoService(bus=bus)
        
        logger.info("Legacy services initialized")
        return repo, exporter, tool_service, journal_service, undo_service
        
    except Exception as e:
        raise StartupError(f"Legacy service initialization failed: {e}") from e


def init_enhanced_widgets(journal_service, engine, bus, clock, settings, tool_service):
    """Initialize widgets with enhanced rendering support."""
    widgets = []
    logger.info("Initializing enhanced widgets...")
    
    # Check if engine supports layered rendering
    engine_supports_layers = (hasattr(engine, 'layered_adapter') and 
                             hasattr(engine, 'coordinate_manager'))
    
    if engine_supports_layers:
        logger.info("Engine supports layered rendering - using enhanced widgets")
        
        # Enhanced canvas widget
        try:
            from ui.canvas_widget import EnhancedCanvasWidget
            canvas_widget = EnhancedCanvasWidget(journal_service, engine, bus)
            widgets.append(canvas_widget)
            logger.info("Enhanced canvas widget added")
        except ImportError:
            logger.warning("Enhanced canvas widget not available, using standard")
            from ui.canvas_widget import CanvasWidget
            canvas_widget = CanvasWidget(journal_service, engine, bus)
            widgets.append(canvas_widget)
        except Exception as e:
            logger.error("Failed to create canvas widget: %s", e)
    else:
        logger.info("Engine uses legacy rendering - using standard widgets")
        
        # Standard grid widget (background will be handled by layer system if available)
        try:
            from bootstrap.widgets import SimpleGridWidget
            grid_widget = SimpleGridWidget(engine, settings)
            widgets.append(grid_widget)
            logger.info("Grid widget added")
        except Exception as e:
            logger.warning("Failed to create grid widget: %s", e)
        
        # Standard canvas widget
        try:
            from ui.canvas_widget import CanvasWidget
            canvas_widget = CanvasWidget(journal_service, engine, bus)
            widgets.append(canvas_widget)
            logger.info("Canvas widget added")
        except Exception as e:
            logger.error("Failed to create canvas widget: %s", e)
    
    # Enhanced hotbar widget (works with both rendering systems)
    try:
        from ui.hotbar import EnhancedHotbarWidget
        hotbar_widget = EnhancedHotbarWidget(tool_service, engine, bus)
        widgets.append(hotbar_widget)
        logger.info("Enhanced hotbar widget added")
    except ImportError:
        logger.warning("Enhanced hotbar not available, using standard")
        from ui.hotbar import HotbarWidget
        hotbar_widget = HotbarWidget(tool_service, engine, bus)
        widgets.append(hotbar_widget)
    except Exception as e:
        logger.error("Failed to create hotbar widget: %s", e)
        # Try minimal hotbar fallback
        try:
            from bootstrap.widgets import MinimalHotbarWidget
            hotbar_widget = MinimalHotbarWidget(tool_service, engine, bus)
            widgets.append(hotbar_widget)
            logger.warning("Created minimal hotbar fallback")
        except Exception as fallback_error:
            logger.error("Even fallback hotbar failed: %s", fallback_error)
    
    logger.info("Widgets initialized: %s", [type(w).__name__ for w in widgets])
    return widgets


# Legacy compatibility
def compose_app(settings, bus=None):
    """Legacy compatibility wrapper."""
    try:
        return compose_enhanced_app(settings, bus)
    except Exception as e:
        logger.warning("Enhanced app composition failed: %s", e)
        logger.info("Falling back to legacy app composition")
        
        # Import legacy factory function
        from .legacy_factory import compose_legacy_app
        return compose_legacy_app(settings, bus)


# services/app.py (UPDATED - Enhanced App with architectural integration)
"""
Enhanced Application Service with Architectural Integration

Integrates all new architectural systems:
- Layered rendering for proper separation
- Coordinate system for infinite canvas
- Shape preview for real-time feedback
- Pan functionality with right-click
"""

import logging
import time
from typing import Any, Dict, List, Tuple, Optional

from core.event_bus import EventBus
from core.coordinates.infinite_system import CoordinateManager
from core.preview.shape_preview import ShapePreviewSystem

logger = logging.getLogger(__name__)


class EnhancedApp:
    """
    Enhanced Application with architectural integration.
    
    Features:
    - Layered rendering (background, drawing, UI)
    - Infinite coordinate system with pan support
    - Non-destructive shape preview
    - Mathematical curve generation
    - Dynamic brush width during drawing
    """

    REQUIRED_SETTINGS = (
        'TITLE', 'WIDTH', 'HEIGHT', 'FPS', 'BRUSH_SIZE_MIN', 'BRUSH_SIZE_MAX', 
        'NEON_COLORS', 'VALID_TOOLS',
    )

    def __init__(
        self,
        settings: Any,
        engine: Any,
        clock: Any,
        input_adapter: Any,
        journal_service: Any,
        tool_service: Any,
        undo_service: Any,
        repository: Any,
        exporter: Any,
        widgets: List[Any],
        bus: EventBus,
    ) -> None:
        """Initialize Enhanced App."""
        self.settings = settings
        self.engine = engine
        self.clock = clock
        self.input_adapter = input_adapter
        self.journal = journal_service
        self.tool = tool_service
        self.undo = undo_service
        self.repo = repository
        self.exporter = exporter
        self.widgets = widgets
        self.bus = bus

        self._validate_settings()

        # Enhanced app state
        self._drawing = False
        self._brush_width = 5
        self._brush_color = (255, 255, 255)
        self._neon_map = {str(i + 1): c for i, c in enumerate(self.settings.NEON_COLORS)}
        self._current_page_id = "main_page"
        
        # Performance tracking
        self._last_point = None
        self._frame_count = 0
        self._last_frame_time = time.time()

        # Enhanced system integration
        self.coordinate_manager = getattr(engine, 'coordinate_manager', None)
        self.preview_system = getattr(engine, 'preview_system', None)
        self.layered_rendering = hasattr(engine, 'layered_adapter')
        
        # Find hotbar widget
        self._hotbar_widget = self._find_hotbar_widget()

        # Subscribe to events
        self.bus.subscribe('brush_width_changed', self._on_brush_width_changed)
        self.bus.subscribe('pan_requested', self._on_pan_requested)
        
        # Initialize brush width synchronization
        self._sync_initial_brush_width()

        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.info("Enhanced App initialized with architectural integration")

    def _validate_settings(self) -> None:
        """Validate settings."""
        missing = [attr for attr in self.REQUIRED_SETTINGS if not hasattr(self.settings, attr)]
        if missing:
            raise ValueError(f"Missing required settings attributes: {missing}")

    def _find_hotbar_widget(self) -> Optional[Any]:
        """Find hotbar widget in widget list."""
        for widget in self.widgets:
            widget_name = str(type(widget).__name__).lower()
            if 'hotbar' in widget_name:
                self._logger.info("Found hotbar widget: %s", type(widget).__name__)
                return widget
        
        self._logger.error("CRITICAL: Hotbar widget not found!")
        return None

    def _sync_initial_brush_width(self) -> None:
        """Synchronize initial brush width."""
        if self._hotbar_widget and hasattr(self._hotbar_widget, 'get_current_brush_width'):
            try:
                self._brush_width = self._hotbar_widget.get_current_brush_width()
            except Exception as e:
                self._logger.warning("Failed to get initial brush width: %s", e)
                self._brush_width = 5

    def _on_brush_width_changed(self, width: int) -> None:
        """Handle brush width changes."""
        try:
            if isinstance(width, (int, float)) and 1 <= width <= 200:
                self._brush_width = int(width)
                self._logger.debug("App brush width updated to: %d", self._brush_width)
        except Exception as e:
            self._logger.error("Error handling brush width change: %s", e)

    def _on_pan_requested(self, data: Dict[str, Any]) -> None:
        """Handle pan requests."""
        try:
            dx = data.get('dx', 0)
            dy = data.get('dy', 0)
            
            if self.coordinate_manager:
                self.coordinate_manager.pan_viewport(dx, dy)
                self._logger.debug("Panned viewport by (%d, %d)", dx, dy)
        except Exception as e:
            self._logger.error("Error handling pan request: %s", e)

    def run(self) -> None:
        """Launch the enhanced application."""
        self._open_window()
        try:
            self._main_loop()
        except KeyboardInterrupt:
            self._logger.info("Enhanced app interrupted by user")
        except Exception:
            self._logger.exception("Unhandled exception in Enhanced App.run()")
            raise
        finally:
            self._cleanup()

    def _cleanup(self):
        """Cleanup resources."""
        try:
            # End any active preview
            if hasattr(self.engine, 'end_shape_preview'):
                self.engine.end_shape_preview()
        except Exception as e:
            self._logger.error("Error in cleanup: %s", e)
        
        self._logger.info("Enhanced application cleanup completed")

    def _open_window(self) -> None:
        """Open the application window with enhanced features."""
        title = self.settings.TITLE
        width, height = self.settings.WIDTH, self.settings.HEIGHT
        try:
            self.engine.open_window(width, height, title)
            self._logger.info(f"Enhanced window opened: {width}×{height} '{title}'")
            
            # Log architectural capabilities
            capabilities = []
            if self.coordinate_manager:
                capabilities.append("infinite coordinates")
            if self.preview_system:
                capabilities.append("shape preview")
            if self.layered_rendering:
                capabilities.append("layered rendering")
            
            self._logger.info("Architectural capabilities: %s", ", ".join(capabilities))
            
        except Exception as e:
            self._logger.exception("Failed to open enhanced window")
            raise RuntimeError("Failed to initialize enhanced UI") from e

    def _main_loop(self) -> None:
        """Enhanced main loop with architectural integration."""
        target_fps = self.settings.FPS
        frame_time = 1.0 / target_fps
        
        while True:
            frame_start = time.time()
            
            try:
                # Get events
                events = self._get_events()
                for evt in events:
                    if not self._handle_event(evt):
                        return
                
                # Enhanced render cycle
                self._render_frame_enhanced()
                
                # Timing with adaptive quality
                elapsed = time.time() - frame_start
                if elapsed < frame_time:
                    self.clock.tick(target_fps)
                else:
                    self.clock.tick(target_fps * 2)  # Catch-up mode
                
            except Exception as e:
                self._logger.error("Error in enhanced main loop: %s", e)

    def _get_events(self) -> List[Any]:
        """Poll events from the enhanced engine."""
        try:
            raw = self.engine.poll_events()
            return self.input_adapter.translate(raw)
        except Exception as e:
            self._logger.error("Error getting enhanced events: %s", e)
            return []

    def _handle_event(self, evt: Any) -> bool:
        """Enhanced event handling with pan support."""
        try:
            etype, data = evt.type, evt.data
            if etype == 'QUIT':
                self._logger.info("QUIT received, exiting enhanced app")
                return False

            # Handle events with enhanced features
            handler_name = f"_on_{etype.lower()}"
            handler = getattr(self, handler_name, None)
            if handler:
                handler(data)
        except Exception as e:
            self._logger.error("Error handling enhanced event: %s", e)
        return True

    def _on_key_press(self, data: Any) -> None:
        """Enhanced key press handling."""
        try:
            key = data
            if key in ('=', '+'):
                self._brush_width = min(self._brush_width + 1, self.settings.BRUSH_SIZE_MAX)
                self.bus.publish('brush_width_changed', self._brush_width)
            elif key in ('-', '_'):
                self._brush_width = max(self._brush_width - 1, self.settings.BRUSH_SIZE_MIN)
                self.bus.publish('brush_width_changed', self._brush_width)
            elif key in self._neon_map:
                self._brush_color = self._neon_map[key]
            elif key == 'c':
                self._clear_canvas_enhanced()
            elif key == 'r':  # Reset viewport
                self._reset_viewport()
            
            self.bus.publish('key_press', key)
        except Exception as e:
            self._logger.error("Error in enhanced key press: %s", e)

    def _on_mouse_click(self, data: Dict[str, Any]) -> None:
        """Enhanced mouse click handling."""
        try:
            if data.get('button') != 1:
                return

            pos = data.get('pos')
            if not pos:
                return

            # Check if hotbar handled the click
            if self._hotbar_widget and hasattr(self._hotbar_widget, 'handle_mouse_click'):
                try:
                    if self._hotbar_widget.handle_mouse_click(pos, 1):
                        return
                except Exception as e:
                    self._logger.warning("Hotbar click handling failed: %s", e)

            # Start enhanced drawing
            self._on_mouse_down_enhanced(data)
        except Exception as e:
            self._logger.error("Error in enhanced mouse click: %s", e)

    def _on_mouse_move(self, data: Dict[str, Any]) -> None:
        """Enhanced mouse movement handling."""
        try:
            pos = data.get('pos')
            if not pos:
                return

            # Update hotbar hover
            if self._hotbar_widget and hasattr(self._hotbar_widget, 'handle_mouse_move'):
                try:
                    self._hotbar_widget.handle_mouse_move(pos)
                except Exception:
                    pass

            # Handle enhanced drawing
            if self._drawing:
                self._handle_drawing_mouse_move_enhanced(data)
        except Exception as e:
            self._logger.error("Error in enhanced mouse move: %s", e)

    def _on_scroll_wheel(self, data: Dict[str, Any]) -> None:
        """Enhanced scroll wheel handling with zoom support."""
        try:
            direction = data.get('direction', 0)
            pos = data.get('pos', (0, 0))
            current_tool = self.tool.current_tool_mode
            
            # Check if over hotbar for brush size adjustment
            if (self._hotbar_widget and 
                hasattr(self._hotbar_widget, 'handle_scroll_wheel') and
                current_tool in ['brush', 'eraser']):
                
                try:
                    if self._hotbar_widget.handle_scroll_wheel(direction, pos):
                        return  # Hotbar handled it
                except Exception:
                    pass
            
            # Handle coordinate system zoom if available
            if self.coordinate_manager and direction != 0:
                zoom_factor = 1.1 if direction > 0 else 0.9
                self.coordinate_manager.zoom_viewport(zoom_factor, pos)
                self._logger.debug("Zoomed viewport: factor=%.2f at %s", zoom_factor, pos)
                
        except Exception as e:
            self._logger.error("Error in enhanced scroll wheel: %s", e)

    def _on_mouse_down_enhanced(self, data: Dict[str, Any]) -> None:
        """Enhanced mouse down handling."""
        try:
            if data.get('button') != 1:
                return

            # Don't start drawing if over hotbar
            if self._hotbar_widget and hasattr(self._hotbar_widget, 'is_mouse_over_hotbar'):
                try:
                    if self._hotbar_widget.is_mouse_over_hotbar():
                        return
                except Exception:
                    pass
            
            self._drawing = True
            x, y = data['pos']
            tool = self.tool.current_tool_mode
            
            if tool in self.settings.VALID_TOOLS and self.journal:
                # Start enhanced stroke
                self.journal.start_stroke(x, y, self._brush_width, self._brush_color)
                self._last_point = (x, y)
                
                # Start shape preview if applicable
                if hasattr(self.engine, 'draw_shape_preview') and tool in ['line', 'rect', 'circle', 'triangle', 'parabola']:
                    self.engine.draw_shape_preview(tool, (x, y), (x, y), self._brush_color, self._brush_width)
                
                self._logger.debug("Started enhanced drawing with tool: %s, width: %d", tool, self._brush_width)
                
        except Exception as e:
            self._logger.error("Error starting enhanced stroke: %s", e)
            self._drawing = False

    def _on_mouse_up(self, data: Dict[str, Any]) -> None:
        """Enhanced mouse up handling."""
        try:
            if data.get('button') != 1:
                return
            
            if not self._drawing:
                return
                
            self._drawing = False
            
            # End shape preview
            if hasattr(self.engine, 'end_shape_preview'):
                self.engine.end_shape_preview()
            
            if self.journal:
                self.journal.end_stroke()
                self._logger.debug("Finished enhanced drawing")
            
            self._last_point = None
            
        except Exception as e:
            self._logger.error("Failed to end enhanced stroke: %s", e)

    def _handle_drawing_mouse_move_enhanced(self, data: Dict[str, Any]) -> None:
        """Enhanced drawing mouse movement."""
        try:
            x, y = data['pos']
            current_point = (x, y)
            
            # Optimized point filtering
            if self._last_point:
                dx = x - self._last_point[0]
                dy = y - self._last_point[1]
                distance_sq = dx * dx + dy * dy
                
                threshold = max(1, self._brush_width // 4)
                if distance_sq < threshold:
                    return
            
            # Add point to journal
            if self.journal:
                self.journal.add_point(x, y, self._brush_width)
                self._last_point = current_point
                
                # Update shape preview if in shape mode
                tool = self.tool.current_tool_mode
                if (hasattr(self.engine, 'draw_shape_preview') and 
                    tool in ['line', 'rect', 'circle', 'triangle', 'parabola'] and
                    hasattr(self.journal, '_shape_start_coord')):
                    
                    start_pos = getattr(self.journal, '_shape_start_coord', (x, y))
                    if self.coordinate_manager:
                        # Convert coordinates for preview
                        if hasattr(start_pos, 'to_world_float'):
                            start_screen = self.coordinate_manager.world_coord_to_screen(start_pos)
                        else:
                            start_screen = start_pos
                    else:
                        start_screen = start_pos
                        
                    self.engine.draw_shape_preview(tool, start_screen, (x, y), self._brush_color, self._brush_width)
                
        except Exception as e:
            self._logger.error("Error in enhanced drawing move: %s", e)

    def _clear_canvas_enhanced(self) -> None:
        """Enhanced canvas clearing with layer support."""
        try:
            if self.journal:
                self.journal.reset()
                
            # Clear layered rendering if available
            if hasattr(self.engine, 'clear_canvas_layered'):
                self.engine.clear_canvas_layered()
                
            self.bus.publish('page_cleared')
            self._logger.info("Enhanced canvas cleared")
        except Exception as e:
            self._logger.error("Error clearing enhanced canvas: %s", e)

    def _reset_viewport(self) -> None:
        """Reset viewport to origin."""
        try:
            if self.coordinate_manager:
                self.coordinate_manager.reset()
                self._logger.info("Viewport reset to origin")
        except Exception as e:
            self._logger.error("Error resetting viewport: %s", e)

    def _render_frame_enhanced(self) -> None:
        """Enhanced frame rendering with architectural integration."""
        try:
            # Clear screen
            self.engine.clear()
            
            # Render using layered system if available
            if hasattr(self.engine, 'render_all_layers'):
                self.engine.render_all_layers()
            else:
                # Fallback to widget-based rendering
                for widget in self.widgets:
                    try:
                        if hasattr(widget, 'render'):
                            widget.render()
                    except Exception as e:
                        self._logger.debug("Widget render error (%s): %s", type(widget).__name__, e)
                        continue
            
            # Present final frame
            self.engine.present()
            
        except Exception as e:
            self._logger.error("CRITICAL: Enhanced frame rendering failed: %s", e)
            # Fallback rendering
            try:
                self.engine.clear()
                self.engine.present()
            except Exception:
                pass

    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all integrated systems."""
        try:
            status = {
                'app_type': 'enhanced',
                'drawing': self._drawing,
                'brush_width': self._brush_width,
                'current_tool': self.tool.current_tool_mode,
                'coordinate_system': self.coordinate_manager is not None,
                'preview_system': self.preview_system is not None,
                'layered_rendering': self.layered_rendering,
                'widgets': [type(w).__name__ for w in self.widgets]
            }
            
            # Add coordinate system info
            if self.coordinate_manager:
                try:
                    status['coordinate_info'] = self.coordinate_manager.get_system_info()
                except Exception:
                    pass
            
            # Add journal stats
            if hasattr(self.journal, 'get_system_stats'):
                try:
                    status['journal_stats'] = self.journal.get_system_stats()
                except Exception:
                    pass
            
            return status
            
        except Exception as e:
            self._logger.error("Error getting system status: %s", e)
            return {'app_type': 'enhanced', 'error': str(e)}


# Legacy compatibility wrapper
class App(EnhancedApp):
    """Legacy compatibility wrapper."""
    
    def __init__(self, *args, **kwargs):
        """Initialize with legacy interface."""
        super().__init__(*args, **kwargs)
        self._logger.info("Legacy App wrapper initialized with enhanced features")