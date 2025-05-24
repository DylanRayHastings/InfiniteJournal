"""Main entry point for the Infinite Journal application."""

import sys
import logging
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from infinitejournal.config import Config
from infinitejournal.backends.opengl.backend import OpenGLBackend
from infinitejournal.interface.framework import Application
from infinitejournal.utilities.logging import setup_logging


def main():
    """Main entry point for the application."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Infinite Journal...")
    
    try:
        # Load configuration
        config = Config()
        
        # Initialize backend
        backend = OpenGLBackend(config)
        
        # Create and run application
        app = Application(backend, config)
        app.run()
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Shutting down Infinite Journal...")


if __name__ == "__main__":
    main()
