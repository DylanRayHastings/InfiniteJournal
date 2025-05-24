"""Infinite Journal - A 3D infinite drawing application."""

__version__ = "0.1.0"
__author__ = "Your Name"

# ===================================

# src/infinitejournal/backends/__init__.py
"""Rendering backends for Infinite Journal."""

from infinitejournal.backends.base import Backend
from infinitejournal.backends.opengl import OpenGLBackend

__all__ = ["Backend", "OpenGLBackend"]

# ===================================

# src/infinitejournal/interface/__init__.py
"""User interface components."""

from infinitejournal.interface.framework import Application

__all__ = ["Application"]

# ===================================

# src/infinitejournal/utilities/__init__.py
"""Utility modules."""

from infinitejournal.utilities.logging import setup_logging

__all__ = ["setup_logging"]
