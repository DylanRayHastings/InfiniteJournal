"""
ARCHITECTURE:
    services/
    ├── core/                    # Universal framework (685 lines)
    │   ├── __init__.py         # Framework exports
    │   ├── framework.py        # Universal service architecture  
    │   ├── validation.py       # Universal validation system
    │   ├── events.py           # Universal event system
    │   └── storage.py          # Universal storage system
    │
    ├── drawing/                 # Drawing module (520 lines)
    │   ├── __init__.py         # Drawing exports
    │   ├── engine.py           # Unified drawing engine
    │   └── tools.py            # Unified tool management
    │
    ├── application.py          # Unified application (890 lines)
    ├── utilities.py            # Consolidated utilities (385 lines)
    └── __init__.py             # This file (exports)

"""

# Core Framework - Universal patterns eliminating all duplication
from .core import (
    # Universal Service Framework
    UniversalService,
    ServiceConfiguration,
    ServiceFactory,
    ServiceRegistry,
    ServiceLifecycleManager,
    create_production_service,
    
    # Universal Validation - eliminates 8+ validation classes
    ValidationService,
    ValidationRule,
    ValidationError,
    validate_coordinate,
    validate_color,
    validate_brush_width,
    validate_file_path,
    validate_tool_key,
    create_validator_chain,
    
    # Universal Event System - eliminates 6+ event interfaces
    EventBus,
    EventSubscription,
    EventPublisher,
    EventHandler,
    create_event_bus,
    create_event_handler,
    
    # Universal Storage - eliminates 4+ storage providers  
    StorageProvider,
    ConfigurationProvider,
    StateProvider,
    create_file_storage,
    create_memory_storage,
    create_json_storage
)

# Drawing System - Consolidated drawing functionality
from .drawing import (
    # Unified Drawing Engine - replaces 3+ drawing services
    DrawingEngine,
    RenderingBackend,
    CoordinateSystem,
    ViewportState,
    WorldCoordinate,
    ScreenCoordinate,
    DrawingConfiguration,
    create_drawing_engine,
    create_pygame_backend,
    
    # Unified Tool Management - replaces tools.py + undo.py + journal.py patterns
    ToolManager,
    DrawingTool,
    ToolState,
    ShapeGenerator,
    BrushController,
    create_tool_manager,
    create_shape_generator
)

# Unified Application - Replaces app.py + database integration
from .application import (
    UnifiedApplication,
    ApplicationSettings,
    ApplicationState,
    InputProcessor,
    RenderingOrchestrator,
    create_application,
    create_production_application,
    
    # Legacy compatibility for existing code
    SimpleApp,
    SimpleApplicationFactory
)

# Consolidated Utilities - Replaces grid.py + calculator.py + scattered utilities
from .utilities import (
    # Grid System - replaces entire grid.py
    GridRenderer,
    GridConfiguration,
    GridStyle,
    create_grid_renderer,
    
    # Math Engine - replaces calculator.py mathematical operations
    MathEngine,
    MathResult,
    MathOperationType,
    GeometryCalculator,
    create_math_engine,
    
    # Utility Service - unified access to all utilities
    UtilityService,
    ConfigurationManager,
    create_utility_service,
    
    # Convenience functions
    calculate_distance,
    interpolate_line,
    solve_equation,
    plot_function
)

# Export all public interfaces -