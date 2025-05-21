"""
Main Entry Point: Application Composition and Startup

Sets up configuration, adapters, services, and UI widgets, then launches the app.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from backup import *
from icecream import ic
from rich import traceback
import traceback as tb_module
from services.database import CanvasDatabase
from debug import DEBUG

# Toggle debug mode here
DEBUG = False

if DEBUG:
    traceback.install(show_locals=True)

# Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Rotating log setup
log_file_path = os.path.join(LOG_DIR, "app.log")
rotating_handler = RotatingFileHandler(
    log_file_path, maxBytes=1024 * 100, backupCount=5, encoding='utf-8'
)
stream_handler = logging.StreamHandler(sys.stdout if DEBUG else open(os.devnull, 'w'))

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
rotating_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.WARNING,
    handlers=[rotating_handler, stream_handler]
)

# Imports
from config import Settings
from core.events import EventBus
from services.app import App
from services.journal import JournalService
from services.grid import draw_grid
from services.tools import ToolService
from services.undo import UndoRedoService

from adapters.pygame_adapter import (
    PygameEngineAdapter,
    PygameClockAdapter,
    PygameInputAdapter
)
from adapters.fs_adapter import (
    FileSystemJournalRepository,
    ScreenshotExporter
)
from ui.canvas_widget import CanvasWidget
from ui.toolbar import Toolbar
from ui.status_bar import StatusBar
from ui.popup_manager import PopupManager

# Load settings and create shared event bus
settings = Settings.load()
bus = EventBus()

def compose_app() -> App:
    """
    Composes the main application object with all configuration,
    adapters, domain services, and widgets.
    
    Returns:
        App: Fully initialized application instance.
    """
    try:
        logging.info("Loading settings...")
        settings = Settings.load()
        if DEBUG: ic(settings)

        logging.info("Initializing EventBus...")
        bus = EventBus()

        logging.info("Setting up platform adapters...")
        engine = PygameEngineAdapter()
        clock  = PygameClockAdapter()
        inp    = PygameInputAdapter()

        tool_service = ToolService(settings, bus)

        database = CanvasDatabase()

        logging.info("Initializing services...")
        repo     = FileSystemJournalRepository()
        exporter = ScreenshotExporter()
        journal = JournalService(bus, tool_service, database)
        undo     = UndoRedoService(bus)
        tools    = ToolService(settings, bus)

        logging.info("Constructing UI widgets...")
        canvas  = CanvasWidget(journal, engine, bus)
        toolbar = Toolbar(tools, engine, bus)
        status  = StatusBar(clock, engine, settings)
        popup   = PopupManager(bus, engine, clock)

        logging.info("Composing application...")
        app = App(
            settings=settings,
            engine=engine,
            clock=clock,
            input_adapter=inp,
            journal_service=journal,
            tool_service=tools,
            undo_service=undo,
            repository=repo,
            exporter=exporter,
            widgets=[canvas, toolbar, status, popup],
            bus=bus
        )

        if DEBUG: ic(app)
        logging.info("Application composed successfully.")
        return app

    except Exception as e:
        logging.exception("Error during app composition")
        raise


def main():
    """
    Entry point for launching the application.
    """
    try:
        logging.info("Launching application...")
        app = compose_app()
        app.run()
        logging.info("Application exited normally.")

    except Exception as e:
        logging.exception("Unhandled exception in main()")

        if DEBUG:
            pass  # rich handles it
        else:
            print("An error occurred:")
            print(''.join(tb_module.format_exception(*sys.exc_info())))

        if sys.platform == "win32":
            input("\nPress Enter to exit...")


if __name__ == '__main__':
    main()
