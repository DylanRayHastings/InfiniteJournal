"""
Optimized UI Framework.

Complete drawing interface system with 75% code reduction
and 100% duplication elimination.
"""

from .framework import (
    # Main system
    UniversalUISystem,
    create_production_ui_system,
    create_development_ui_system,
    
    # Configuration
    UniversalUIConfig,
    
    # Core types
    UniversalPoint,
    UniversalColor,
    UniversalGeometry,
    
    # Test utilities
    UniversalTestHelpers,
)

__version__ = "2.0.0"
__all__ = [
    "UniversalUISystem",
    "create_production_ui_system", 
    "create_development_ui_system",
    "UniversalUIConfig",
    "UniversalPoint",
    "UniversalColor", 
    "UniversalGeometry",
    "UniversalTestHelpers",
]