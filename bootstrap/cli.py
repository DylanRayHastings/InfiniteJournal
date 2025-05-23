"""
Command Line Interface for InfiniteJournal
Handles command line argument parsing.
"""

import argparse
import sys
from typing import List, Optional


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command line arguments for InfiniteJournal.
    
    Args:
        argv: Optional command line arguments. If None, uses sys.argv
        
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="InfiniteJournal - Digital drawing and note-taking application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Start with default settings
  python main.py --debug            # Start in debug mode
  python main.py --log-level INFO   # Set logging level
  python main.py --width 1920 --height 1080  # Set window size
        """
    )
    
    # Window settings
    parser.add_argument(
        '--width',
        type=int,
        default=None,
        help='Window width in pixels (default: from config)'
    )
    
    parser.add_argument(
        '--height', 
        type=int,
        default=None,
        help='Window height in pixels (default: from config)'
    )
    
    parser.add_argument(
        '--title',
        type=str,
        default=None,
        help='Window title (default: from config)'
    )
    
    parser.add_argument(
        '--fps',
        type=int,
        default=None,
        help='Target FPS (default: from config)'
    )
    
    # Debug and logging
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default=None,
        help='Set logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        default=None,
        help='Log to file instead of console'
    )
    
    # Application settings
    parser.add_argument(
        '--data-dir',
        type=str,
        default=None,
        help='Data directory path (default: ./data)'
    )
    
    parser.add_argument(
        '--config-file',
        type=str,
        default=None,
        help='Configuration file path'
    )
    
    parser.add_argument(
        '--no-autosave',
        action='store_true',
        help='Disable automatic saving'
    )
    
    # Tool settings
    parser.add_argument(
        '--default-tool',
        choices=['brush', 'eraser', 'line', 'rect', 'circle', 'triangle', 'parabola'],
        default=None,
        help='Default drawing tool'
    )
    
    parser.add_argument(
        '--brush-size',
        type=int,
        default=None,
        help='Default brush size'
    )
    
    # Performance settings
    parser.add_argument(
        '--no-vsync',
        action='store_true',
        help='Disable vertical sync'
    )
    
    parser.add_argument(
        '--no-smoothing',
        action='store_true',
        help='Disable stroke smoothing'
    )
    
    # Development options
    parser.add_argument(
        '--profile',
        action='store_true',
        help='Enable performance profiling'
    )
    
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Run in test mode (for automated testing)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='InfiniteJournal 1.0.0'
    )
    
    # Parse arguments
    if argv is None:
        argv = sys.argv[1:]
    
    args = parser.parse_args(argv)
    
    # Post-processing
    if args.debug and args.log_level is None:
        args.log_level = 'DEBUG'
    elif args.log_level is None:
        args.log_level = 'INFO'
    
    return args


def validate_args(args: argparse.Namespace) -> bool:
    """
    Validate parsed command line arguments.
    
    Args:
        args: Parsed arguments namespace
        
    Returns:
        True if arguments are valid, False otherwise
    """
    errors = []
    
    # Validate window dimensions
    if args.width is not None:
        if args.width < 100 or args.width > 5000:
            errors.append(f"Window width {args.width} out of range 100-5000")
    
    if args.height is not None:
        if args.height < 100 or args.height > 5000:
            errors.append(f"Window height {args.height} out of range 100-5000")
    
    # Validate FPS
    if args.fps is not None:
        if args.fps < 1 or args.fps > 240:
            errors.append(f"FPS {args.fps} out of range 1-240")
    
    # Validate brush size
    if args.brush_size is not None:
        if args.brush_size < 1 or args.brush_size > 200:
            errors.append(f"Brush size {args.brush_size} out of range 1-200")
    
    # Print errors if any
    if errors:
        print("Command line argument errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return False
    
    return True


def print_help():
    """Print detailed help information."""
    parser = argparse.ArgumentParser()
    parse_args(['--help'])  # This will print help and exit


# Export main functions
__all__ = ['parse_args', 'validate_args', 'print_help']