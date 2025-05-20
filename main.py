"""
Main Entry Point: Application Composition and Startup

Sets up configuration, adapters, services, and UI widgets, then launches the app.
"""

from logging.handlers import RotatingFileHandler
from backup import *

from icecream import ic
from rich import traceback
import logging
import sys
import traceback as tb_module
from debug import DEBUG

# Toggle debug mode here
DEBUG = False

if DEBUG:
    traceback.install(show_locals=True)

# Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Set up rotating log handler
log_file_path = os.path.join(LOG_DIR, "app.log")
rotating_handler = RotatingFileHandler(
    log_file_path, maxBytes=1024 * 100, backupCount=5, encoding='utf-8'
)

# Stream handler to stdout only if debug
stream_handler = logging.StreamHandler(sys.stdout if DEBUG else open(os.devnull, 'w'))

# Formatter for all logs
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
rotating_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.WARNING,
    handlers=[rotating_handler, stream_handler]
)

from config import Settings
from core.events import EventBus
from core.services import (
    JournalService,
    ToolService,
    UndoRedoService,
    App
)
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

        logging.info("Initializing services...")
        repo     = FileSystemJournalRepository()
        exporter = ScreenshotExporter()
        journal  = JournalService(bus)
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

        # Show full formatted traceback using rich or fallback if disabled
        if DEBUG:
            # Already handled by rich
            pass
        else:
            print("An error occurred:")
            print(''.join(tb_module.format_exception(*sys.exc_info())))

        # Optional: pause so user can read before terminal closes (Windows-specific behavior)
        if sys.platform == "win32":
            input("\nPress Enter to exit...")


if __name__ == '__main__':
    main()
