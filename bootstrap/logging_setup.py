"""
Logging Setup for InfiniteJournal
Configures comprehensive logging for the application.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


def setup_logging(settings, console_log_level: str = 'INFO') -> None:
    """
    Set up comprehensive logging for the application.
    
    Args:
        settings: Application settings object
        console_log_level: Console logging level
    """
    # Create logs directory
    log_dir = getattr(settings, 'LOG_DIR', Path('./logs'))
    if isinstance(log_dir, str):
        log_dir = Path(log_dir)
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all levels
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)-8s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)-8s [%(name)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_log_level.upper(), logging.INFO))
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handlers
    debug_mode = getattr(settings, 'DEBUG', True)
    
    # Main log file (rotating)
    main_log_file = log_dir / 'infinitejournal.log'
    main_handler = logging.handlers.RotatingFileHandler(
        main_log_file,
        maxBytes=getattr(settings, 'LOG_MAX_BYTES', 10 * 1024 * 1024),  # 10MB
        backupCount=getattr(settings, 'LOG_BACKUP_COUNT', 5)
    )
    main_handler.setLevel(logging.INFO)
    main_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(main_handler)
    
    # Debug log file (if debug mode)
    if debug_mode:
        debug_log_file = log_dir / 'debug.log'
        debug_handler = logging.handlers.RotatingFileHandler(
            debug_log_file,
            maxBytes=50 * 1024 * 1024,  # 50MB for debug
            backupCount=3
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(debug_handler)
    
    # Error log file (errors and critical only)
    error_log_file = log_dir / 'errors.log'
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10  # Keep more error logs
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # Performance log file (for profiling)
    perf_log_file = log_dir / 'performance.log'
    perf_handler = logging.handlers.RotatingFileHandler(
        perf_log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    perf_handler.setLevel(logging.INFO)
    perf_handler.setFormatter(detailed_formatter)
    
    # Create performance logger
    perf_logger = logging.getLogger('performance')
    perf_logger.addHandler(perf_handler)
    perf_logger.setLevel(logging.INFO)
    perf_logger.propagate = False  # Don't propagate to root
    
    # Configure specific loggers
    configure_module_loggers(debug_mode)
    
    # Log startup message
    startup_logger = logging.getLogger('startup')
    startup_logger.info("=" * 50)
    startup_logger.info("InfiniteJournal Starting")
    startup_logger.info(f"Debug Mode: {debug_mode}")
    startup_logger.info(f"Console Log Level: {console_log_level}")
    startup_logger.info(f"Log Directory: {log_dir}")
    startup_logger.info("=" * 50)


def configure_module_loggers(debug_mode: bool = False) -> None:
    """
    Configure logging levels for specific modules.
    
    Args:
        debug_mode: Whether debug mode is enabled
    """
    # Module-specific log levels
    module_levels = {
        'pygame': logging.WARNING,      # Pygame is noisy
        'urllib3': logging.WARNING,     # HTTP library noise
        'requests': logging.WARNING,    # HTTP requests noise
        'PIL': logging.WARNING,         # Pillow image library
        'matplotlib': logging.WARNING,  # Plotting library
    }
    
    # Application module levels
    if debug_mode:
        app_levels = {
            'services': logging.DEBUG,
            'adapters': logging.DEBUG,
            'bootstrap': logging.DEBUG,
            'config': logging.DEBUG,
        }
    else:
        app_levels = {
            'services': logging.INFO,
            'adapters': logging.INFO,
            'bootstrap': logging.INFO,
            'config': logging.INFO,
        }
    
    # Apply module levels
    all_levels = {**module_levels, **app_levels}
    
    for module, level in all_levels.items():
        logger = logging.getLogger(module)
        logger.setLevel(level)


def create_logger(name: str, level: str = 'INFO') -> logging.Logger:
    """
    Create a named logger with specified level.
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger


def log_system_info() -> None:
    """Log system information for debugging."""
    logger = logging.getLogger('system_info')
    
    try:
        import platform
        import sys
        
        logger.info("System Information:")
        logger.info(f"Python Version: {sys.version}")
        logger.info(f"Platform: {platform.platform()}")
        logger.info(f"Architecture: {platform.architecture()}")
        logger.info(f"Processor: {platform.processor()}")
        
        # Memory information if available
        try:
            import psutil
            memory = psutil.virtual_memory()
            logger.info(f"Total Memory: {memory.total // (1024**3)} GB")
            logger.info(f"Available Memory: {memory.available // (1024**3)} GB")
        except ImportError:
            logger.debug("psutil not available for memory info")
        
        # Pygame information if available
        try:
            import pygame
            logger.info(f"Pygame Version: {pygame.version.ver}")
            logger.info(f"SDL Version: {pygame.version.SDL}")
        except ImportError:
            logger.warning("Pygame not available")
            
    except Exception as error:
        logger.error(f"Failed to log system info: {error}")


def log_performance_metric(metric_name: str, value: float, unit: str = '', context: Dict[str, Any] = None) -> None:
    """
    Log a performance metric.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
        context: Additional context information
    """
    perf_logger = logging.getLogger('performance')
    
    context_str = ""
    if context:
        context_parts = [f"{k}={v}" for k, v in context.items()]
        context_str = f" ({', '.join(context_parts)})"
    
    unit_str = f" {unit}" if unit else ""
    perf_logger.info(f"{metric_name}: {value}{unit_str}{context_str}")


def setup_development_logging() -> None:
    """Set up enhanced logging for development."""
    # Add more detailed formatters for development
    dev_formatter = logging.Formatter(
        fmt='%(asctime)s.%(msecs)03d %(levelname)-8s [%(name)s:%(lineno)d] %(funcName)s() - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Get console handler and update formatter
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
            handler.setFormatter(dev_formatter)
            handler.setLevel(logging.DEBUG)


def setup_production_logging(log_dir: Path) -> None:
    """Set up production-optimized logging."""
    # More conservative logging for production
    root_logger = logging.getLogger()
    
    # Remove debug handlers
    for handler in root_logger.handlers[:]:
        if handler.level == logging.DEBUG:
            root_logger.removeHandler(handler)
    
    # Set more restrictive levels
    root_logger.setLevel(logging.INFO)
    
    # Add syslog handler for production if available
    try:
        syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
        syslog_formatter = logging.Formatter(
            'InfiniteJournal[%(process)d]: %(levelname)s %(name)s - %(message)s'
        )
        syslog_handler.setFormatter(syslog_formatter)
        syslog_handler.setLevel(logging.WARNING)
        root_logger.addHandler(syslog_handler)
    except Exception:
        # Syslog not available on this system
        pass


def shutdown_logging() -> None:
    """Shutdown logging gracefully."""
    logger = logging.getLogger('shutdown')
    logger.info("Application shutting down - closing log files")
    
    # Close all handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        try:
            handler.close()
            root_logger.removeHandler(handler)
        except Exception:
            pass  # Ignore errors during shutdown


# Export main functions
__all__ = [
    'setup_logging',
    'configure_module_loggers',
    'create_logger',
    'log_system_info',
    'log_performance_metric',
    'setup_development_logging',
    'setup_production_logging',
    'shutdown_logging'
]