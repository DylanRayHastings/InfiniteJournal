from typing import Optional, List
import argparse

from .parsers import parse_positive_int


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments for the application."""
    parser = argparse.ArgumentParser(description="InfiniteJournal Launcher")
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default=None,
        help='Console logging level'
    )
    parser.add_argument(
        '--width',
        type=lambda x: parse_positive_int(x, 'width', default=800),
        help='Window width in pixels'
    )
    parser.add_argument(
        '--height',
        type=lambda x: parse_positive_int(x, 'height', default=600),
        help='Window height in pixels'
    )
    return parser.parse_args(argv)
