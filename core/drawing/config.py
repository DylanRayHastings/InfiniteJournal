# core/drawing/config.py (OPTIMIZED)
"""Configuration validation for drawing module - OPTIMIZED."""

import os
from pathlib import Path

def validate_file_path(file_path: Path) -> None:
    """Validate file path - optimized with early returns."""
    directory = file_path.parent
    
    if not directory.exists():
        raise ValueError(f"Directory does not exist: {directory}")
    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")
    if not os.access(directory, os.W_OK):
        raise ValueError(f"Directory is not writable: {directory}")