"""
Adapters Package for InfiniteJournal
Provides integration adapters for different rendering backends and input systems.
"""

from .pygame_adapter import (
    PygameEngineAdapter,
    PygameInputAdapter,
    PygameClock,
    PygameEvent,
    create_pygame_adapter,
    create_pygame_input_adapter,
    create_pygame_clock,
    create_pygame_bus
)

__version__ = "1.0.0"
__author__ = "InfiniteJournal Adapters"

__all__ = [
    'PygameEngineAdapter',
    'PygameInputAdapter',
    'PygameClock', 
    'PygameEvent',
    'create_pygame_adapter',
    'create_pygame_input_adapter',
    'create_pygame_clock',
    'create_pygame_bus'
]