#!/usr/bin/env python3
"""
Main entry point: Application Composition and Startup.
"""
import os
import sys
import argparse
import logging
import logging.config
import atexit
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Callable, ClassVar, List, Tuple
from urllib.parse import urlparse
from importlib import import_module

from dotenv import load_dotenv
from rich import traceback as rich_traceback
from icecream import ic

from core.events import EventBus

__all__ = [
    'ConfigurationError', 'Settings', 'setup_logging',
    'make_exception_hook', 'compose_app', 'main'
]


class ConfigurationError(Exception):
    """Raised for missing or invalid application configuration."""
    pass


def parse_positive_int(
    raw: Any, name: str, default: int, min_value: int = 1, max_value: int = 5000
) -> int:
    """Parse and validate a positive integer within bounds."""
    if raw is None:
        value = default
    else:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            raise ConfigurationError(f"{name} must be an integer, got '{raw}'")
    if not (min_value <= value <= max_value):
        raise ConfigurationError(
            f"{name} must be between {min_value} and {max_value}, got {value}"
        )
    return value


def validate_database_url(url: str) -> None:
    """Ensure the DATABASE_URL is well-formed and supported."""
    parsed = urlparse(url)
    if parsed.scheme == 'sqlite':
        if not parsed.path or parsed.path == ':memory:':
            raise ConfigurationError(f"Invalid sqlite URL '{url}'")
    elif parsed.scheme in ('postgres', 'postgresql', 'mysql', 'mssql'):
        if not parsed.netloc:
            raise ConfigurationError(f"Invalid URL '{url}' — missing network location")
    else:
        raise ConfigurationError(f"Unsupported database scheme '{parsed.scheme}'")


@dataclass(frozen=True)
class Settings:
    """Holds application settings loaded from CLI args or environment."""
    debug: bool
    log_dir: Path
    database_url: str
    data_path: Path
    default_tool: str
    width: int
    height: int

    # Constants
    TITLE: ClassVar[str] = "InfiniteJournal"
    FPS: ClassVar[int] = 60
    VALID_TOOLS: ClassVar[List[str]] = [
        "brush", "eraser", "line", "rect", "circle", "parabola"
    ]
    BRUSH_SIZE_MIN: ClassVar[int] = 1
    BRUSH_SIZE_MAX: ClassVar[int] = 100
    NEON_COLORS: ClassVar[List[Tuple[int, int, int]]] = [
        (57, 255, 20),
        (0, 255, 255),
        (255, 20, 147),
        (255, 255, 0),
        (255, 97, 3),
    ]

    class Config:
        LOG_MAX_BYTES: ClassVar[int] = 1_048_576
        LOG_BACKUP_COUNT: ClassVar[int] = 5
        MIN_SIZE: ClassVar[int] = 100
        MAX_SIZE: ClassVar[int] = 5000

    @classmethod
    def load(cls, args: argparse.Namespace) -> "Settings":
        """Load settings from CLI arguments or environment, validating each."""
        load_dotenv()  # ensure .env is loaded
        missing = []

        debug = bool(args.debug or
                     (os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")))

        log_dir = Path(args.log_dir or os.getenv("LOG_DIR", "./logs")).resolve()
        if not log_dir.parent.exists():
            raise ConfigurationError(f"Cannot create log directory '{log_dir}'")

        url = args.database_url or os.getenv("DATABASE_URL")
        if not url:
            missing.append("DATABASE_URL")
        else:
            validate_database_url(url)

        dp = args.data_path or os.getenv("DATA_PATH")
        data_path = Path(dp).resolve() if dp else None
        if not data_path:
            missing.append("DATA_PATH")
        elif not data_path.exists():
            data_path.mkdir(parents=True, exist_ok=True)

        default_tool = args.default_tool or os.getenv("DEFAULT_TOOL", "brush")
        if default_tool not in cls.VALID_TOOLS:
            raise ConfigurationError(
                f"Invalid DEFAULT_TOOL '{default_tool}'. Valid options: {cls.VALID_TOOLS}"
            )

        width = parse_positive_int(
            args.width,
            "WIDTH",
            default=800,
            min_value=cls.Config.MIN_SIZE,
            max_value=cls.Config.MAX_SIZE
        )
        height = parse_positive_int(
            args.height,
            "HEIGHT",
            default=600,
            min_value=cls.Config.MIN_SIZE,
            max_value=cls.Config.MAX_SIZE
        )
        if missing:
            raise ConfigurationError("Missing configuration: " + ", ".join(missing))

        return cls(debug, log_dir, url, data_path, default_tool, width, height)


def setup_logging(settings: Settings) -> None:
    """
    Configure rotating file and optional console logging.
    """
    settings.log_dir.mkdir(parents=True, exist_ok=True)

    cfg = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
            }
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(settings.log_dir / "app.log"),
                "maxBytes": Settings.Config.LOG_MAX_BYTES,
                "backupCount": Settings.Config.LOG_BACKUP_COUNT,
                "formatter": "standard",
                "encoding": "utf-8",
            }
        },
        "root": {
            "handlers": ["file"],
            "level": "DEBUG" if settings.debug else "WARNING",
        },
    }

    if settings.debug:
        cfg["handlers"]["console"] = {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "standard",
        }
        cfg["root"]["handlers"].append("console")

    logging.config.dictConfig(cfg)
    logging.getLogger(__name__).debug(
        f"Logging initialized at {settings.log_dir} (debug={settings.debug})"
    )


def make_exception_hook(settings: Settings) -> Callable:
    """
    Return a sys.excepthook that logs uncaught exceptions and exits cleanly.
    """
    def _hook(exc_type, exc_value, exc_tb):
        logger = logging.getLogger()
        if issubclass(exc_type, KeyboardInterrupt):
            logger.info("Interrupted by user")
            sys.exit(0)
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
        if not settings.debug:
            print(f"Unexpected error. See logs in '{settings.log_dir / 'app.log'}'")
        sys.exit(1)
    return _hook


def load_adapters() -> Tuple[Any, Any, Any]:
    """
    Dynamically load engine, clock, and input adapters.
    Raises ConfigurationError if any adapter or attribute is missing.
    """
    try:
        mod = import_module("adapters.pygame_adapter")
        Engine = getattr(mod, "PygameEngineAdapter")
        Clock = getattr(mod, "PygameClockAdapter")
        Input = getattr(mod, "PygameInputAdapter")
    except (ImportError, AttributeError) as e:
        raise ConfigurationError(f"Adapter import failed: {e}") from e

    engine = Engine()
    if not hasattr(engine, "open_window"):
        raise ConfigurationError("Engine adapter missing 'open_window' method")
    return engine, Clock(), Input()


def init_database(settings: Settings) -> Any:
    """
    Initializes the database connection and registers its close() at exit (if provided).
    """
    try:
        from services.database import CanvasDatabase
        db = CanvasDatabase(settings.database_url)
    except Exception as e:
        raise ConfigurationError(f"Database init failed: {e}") from e

    atexit.register(getattr(db, "close", lambda: None))
    return db


def init_services(
    settings: Settings, bus: EventBus, database: Any
) -> Tuple[Any, Any, Any, Any, Any]:
    """
    Initialize repository, exporter, tool, journal, and undo services.
    """
    from adapters.fs_adapter import FileSystemJournalRepository, ScreenshotExporter
    from services.tools import ToolService
    from services.journal import JournalService
    from services.undo import UndoRedoService

    repo = FileSystemJournalRepository(settings.data_path)
    exporter = ScreenshotExporter(settings.data_path)
    tool_service = ToolService(settings, bus)
    journal_service = JournalService(bus, tool_service, database)
    undo_service = UndoRedoService(bus)
    return repo, exporter, tool_service, journal_service, undo_service


def init_widgets(
    journal_service: Any,
    engine: Any,
    bus: EventBus,
    clock: Any,
    settings: Settings,
    tool_service: Any
) -> List[Any]:
    """
    Instantiate UI widgets in the order they should appear.
    """
    from ui.canvas_widget import CanvasWidget
    from ui.toolbar import Toolbar
    from ui.status_bar import StatusBar
    from ui.popup_manager import PopupManager

    return [
        CanvasWidget(journal_service, engine, bus),
        Toolbar(tool_service, engine, bus),
        StatusBar(clock, engine, settings),
        PopupManager(bus, engine, clock),
    ]


def compose_app(settings: Settings, bus: EventBus) -> Any:
    """
    Compose and return the main App instance, fully wired.
    """
    settings.data_path.mkdir(parents=True, exist_ok=True)

    engine, clock, input_adapter = load_adapters()
    database = init_database(settings)
    repo, exporter, tool_service, journal_service, undo_service = init_services(
        settings, bus, database
    )
    widgets = init_widgets(
        journal_service, engine, bus, clock, settings, tool_service
    )

    from services.app import App
    app = App(
        settings=settings,
        engine=engine,
        clock=clock,
        input_adapter=input_adapter,
        journal_service=journal_service,
        tool_service=tool_service,
        undo_service=undo_service,
        repository=repo,
        exporter=exporter,
        widgets=widgets,
        bus=bus,
    )
    if settings.debug:
        ic(app)
    return app


def main() -> None:
    """Parse arguments, set up configuration, and launch the application."""
    parser = argparse.ArgumentParser(description="InfiniteJournal Launcher")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--log-dir", type=Path, help="Directory for log files")
    parser.add_argument("--database-url", type=str, help="Database connection URL")
    parser.add_argument("--data-path", type=Path, help="Path for journal data")
    parser.add_argument(
        "--default-tool", type=str, help="Initial tool mode"
    )
    parser.add_argument("--width", type=int, help="Window width in pixels")
    parser.add_argument("--height", type=int, help="Window height in pixels")
    args = parser.parse_args()

    try:
        settings = Settings.load(args)
    except ConfigurationError as e:
        print(f"Configuration error: {e}")
        sys.exit(2)

    setup_logging(settings)
    sys.excepthook = make_exception_hook(settings)

    if settings.debug:
        rich_traceback.install(show_locals=True)
        ic.configureOutput(prefix="[DEBUG] ")

    logging.getLogger(__name__).info("Starting application composition...")
    bus = EventBus()

    try:
        app = compose_app(settings, bus)
        app.run()
        logging.getLogger(__name__).info("Application exited normally.")
        sys.exit(0)

    except ConfigurationError as e:
        logging.getLogger(__name__).error(f"Startup failure: {e}")
        print(f"Configuration error at runtime: {e}")
        sys.exit(2)

    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Shutdown via KeyboardInterrupt.")
        sys.exit(0)

    except Exception as e:
        logging.getLogger(__name__).exception("Unhandled exception in main loop")
        if not settings.debug:
            print(f"Unhandled error. See logs in '{settings.log_dir / 'app.log'}'")
        sys.exit(1)


if __name__ == "__main__":
    main()
