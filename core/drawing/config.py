"""Configuration validation for drawing module."""

import os
from pathlib import Path


def validate_file_path(file_path: Path) -> None:
    """Validate that the target file’s directory exists and is writable.

    Args:
        file_path: Path to the file to be written.

    Raises:
        ValueError: If the directory does not exist, is not a directory,
            or is not writable.
    """
    directory = file_path.parent
    if not directory.exists():
        raise ValueError(f"Directory does not exist: {directory}")
    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")
    if not os.access(directory, os.W_OK):
        raise ValueError(f"Directory is not writable: {directory}")
