"""Command line interface parsing with improved validation."""

from typing import Optional, List
import argparse
import sys

from .parsers import parse_positive_int


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments for the application.
    
    Args:
        argv: List of command line arguments (defaults to sys.argv)
        
    Returns:
        Parsed arguments namespace
        
    Raises:
        SystemExit: If argument parsing fails or help is requested
    """
    parser = argparse.ArgumentParser(
        description="InfiniteJournal - An infinite digital journal with drawing capabilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run with default settings
  %(prog)s --width 1920 --height 1080  # Set window size
  %(prog)s --log-level DEBUG        # Enable debug logging
        """
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='InfiniteJournal 0.1.0'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default=None,
        help='Console logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--width',
        type=lambda x: parse_positive_int(x, 'width', default=None, min_value=100, max_value=5000),
        help='Window width in pixels (100-5000, default: from config/env)'
    )
    
    parser.add_argument(
        '--height',
        type=lambda x: parse_positive_int(x, 'height', default=None, min_value=100, max_value=5000),
        help='Window height in pixels (100-5000, default: from config/env)'
    )
    
    parser.add_argument(
        '--fps',
        type=lambda x: parse_positive_int(x, 'fps', default=None, min_value=1, max_value=240),
        help='Target frames per second (1-240, default: from config/env)'
    )
    
    parser.add_argument(
        '--data-path',
        type=str,
        help='Path to data directory (default: from config/env)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )

    try:
        return parser.parse_args(argv)
    except SystemExit:
        # Re-raise SystemExit to allow proper handling
        raise
    except Exception as e:
        parser.error(f"Argument parsing failed: {e}")