"""
Unified Error Boundary Architecture for InfiniteJournal

Provides comprehensive error handling, recovery mechanisms, and user feedback.
"""

import logging
import traceback
import functools
import threading
from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass
from enum import Enum
from core.event_bus import EventBus

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for categorization and handling."""
    LOW = "low"          # Minor issues, continue operation
    MEDIUM = "medium"    # Significant issues, degrade gracefully  
    HIGH = "high"        # Critical issues, attempt recovery
    CRITICAL = "critical"  # System-breaking issues, require restart


class ErrorCategory(Enum):
    """Error categories for better classification and handling."""
    RENDERING = "rendering"
    INPUT = "input"
    PERSISTENCE = "persistence"
    DRAWING = "drawing"
    TOOL = "tool"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    SYSTEM = "system"


@dataclass
class ErrorContext:
    """Rich error context for better debugging and recovery."""
    operation: str
    component: str
    user_action: Optional[str] = None
    system_state: Optional[Dict[str, Any]] = None
    recovery_hints: Optional[List[str]] = None


class ApplicationError(Exception):
    """Base application error with rich context and recovery information."""
    
    def __init__(
        self, 
        message: str, 
        error_code: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        context: Optional[ErrorContext] = None,
        recoverable: bool = True,
        user_message: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.category = category
        self.context = context or ErrorContext("unknown", "unknown")
        self.recoverable = recoverable
        self.user_message = user_message or self._generate_user_message()
        
    def _generate_user_message(self) -> str:
        """Generate user-friendly error message."""
        category_messages = {
            ErrorCategory.RENDERING: "Display issue encountered",
            ErrorCategory.INPUT: "Input handling problem", 
            ErrorCategory.DRAWING: "Drawing operation failed",
            ErrorCategory.TOOL: "Tool malfunction",
            ErrorCategory.PERSISTENCE: "Save/load issue",
            ErrorCategory.CONFIGURATION: "Configuration problem",
            ErrorCategory.NETWORK: "Network connectivity issue",
            ErrorCategory.SYSTEM: "System error"
        }
        
        base_message = category_messages.get(self.category, "Unknown error")
        
        if self.severity == ErrorSeverity.LOW:
            return f"{base_message} (minor)"
        elif self.severity == ErrorSeverity.CRITICAL:
            return f"Critical {base_message.lower()}"
        else:
            return base_message


class ErrorRecoveryStrategy:
    """Strategies for recovering from different types of errors."""
    
    @staticmethod
    def retry_operation(func: Callable, max_attempts: int = 3, delay: float = 0.1) -> Any:
        """Retry an operation with exponential backoff."""
        import time
        
        for attempt in range(max_attempts):
            try:
                return func()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                time.sleep(delay * (2 ** attempt))
                logger.warning("Retry attempt %d failed: %s", attempt + 1, e)
    
    @staticmethod
    def graceful_degradation(primary_func: Callable, fallback_func: Callable) -> Any:
        """Try primary function, fall back to simpler alternative."""
        try:
            return primary_func()
        except Exception as e:
            logger.warning("Primary function failed, using fallback: %s", e)
            return fallback_func()
    
    @staticmethod
    def safe_default(func: Callable, default_value: Any) -> Any:
        """Execute function with safe default fallback."""
        try:
            return func()
        except Exception as e:
            logger.warning("Function failed, returning default: %s", e)
            return default_value


class ErrorBoundary:
    """Central error boundary for handling and recovering from errors."""
    
    def __init__(self, bus: Optional[EventBus] = None):
        self.bus = bus
        self.error_counts: Dict[str, int] = {}
        self.recovery_attempts: Dict[str, int] = {}
        self.max_recovery_attempts = 3
        self._lock = threading.Lock()
        
    def handle_error(
        self, 
        error: Exception, 
        context: ErrorContext,
        attempt_recovery: bool = True
    ) -> bool:
        """
        Handle an error with context-aware recovery.
        
        Returns:
            bool: True if error was handled and operation can continue
        """
        # Determine if this is an ApplicationError or wrap it
        if isinstance(error, ApplicationError):
            app_error = error
        else:
            app_error = self._wrap_exception(error, context)
        
        # Log the error appropriately
        self._log_error(app_error, context)
        
        # Track error frequency
        with self._lock:
            error_key = f"{app_error.category.value}:{app_error.error_code}"
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Publish error event for UI feedback
        if self.bus:
            try:
                self.bus.publish('error_occurred', {
                    'message': app_error.user_message,
                    'severity': app_error.severity.value,
                    'category': app_error.category.value,
                    'recoverable': app_error.recoverable,
                    'error_code': app_error.error_code
                })
            except Exception as bus_error:
                logger.error("Failed to publish error event: %s", bus_error)
        
        # Attempt recovery if appropriate
        if attempt_recovery and app_error.recoverable:
            return self._attempt_recovery(app_error, context)
        
        return False
    
    def _wrap_exception(self, error: Exception, context: ErrorContext) -> ApplicationError:
        """Wrap a standard exception in ApplicationError."""
        error_type = type(error).__name__
        
        # Categorize based on exception type and context
        severity = self._determine_severity(error, context)
        category = self._determine_category(error, context)
        
        return ApplicationError(
            message=str(error),
            error_code=f"{category.value}_{error_type}",
            severity=severity,
            category=category,
            context=context,
            recoverable=self._is_recoverable(error, context)
        )
    
    def _determine_severity(self, error: Exception, context: ErrorContext) -> ErrorSeverity:
        """Determine error severity based on exception type and context."""
        if isinstance(error, (MemoryError, SystemError)):
            return ErrorSeverity.CRITICAL
        elif isinstance(error, (ValueError, TypeError, AttributeError)):
            if context.component in ['rendering', 'drawing']:
                return ErrorSeverity.MEDIUM
            return ErrorSeverity.LOW
        elif isinstance(error, (IOError, OSError)):
            return ErrorSeverity.HIGH
        else:
            return ErrorSeverity.MEDIUM
    
    def _determine_category(self, error: Exception, context: ErrorContext) -> ErrorCategory:
        """Determine error category based on context and exception type."""
        component_mapping = {
            'pygame_adapter': ErrorCategory.RENDERING,
            'journal_service': ErrorCategory.DRAWING,
            'tool_service': ErrorCategory.TOOL,
            'database': ErrorCategory.PERSISTENCE,
            'input_adapter': ErrorCategory.INPUT
        }
        
        # Check component first
        for component_key, category in component_mapping.items():
            if component_key in context.component.lower():
                return category
        
        # Fallback to exception type
        if isinstance(error, (IOError, OSError)):
            return ErrorCategory.PERSISTENCE
        elif isinstance(error, (ValueError, TypeError)):
            return ErrorCategory.CONFIGURATION
        else:
            return ErrorCategory.SYSTEM
    
    def _is_recoverable(self, error: Exception, context: ErrorContext) -> bool:
        """Determine if an error is recoverable."""
        # Critical system errors are not recoverable
        if isinstance(error, (MemoryError, SystemError)):
            return False
        
        # Most other errors are recoverable with appropriate strategies
        return True
    
    def _log_error(self, error: ApplicationError, context: ErrorContext) -> None:
        """Log error with appropriate level and context."""
        log_message = (
            f"[{error.category.value.upper()}] {error.message} "
            f"(Code: {error.error_code}, Operation: {context.operation})"
        )
        
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, exc_info=True)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_message, exc_info=True)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def _attempt_recovery(self, error: ApplicationError, context: ErrorContext) -> bool:
        """Attempt to recover from an error based on its category and context."""
        with self._lock:
            recovery_key = f"{error.category.value}:{context.operation}"
            attempts = self.recovery_attempts.get(recovery_key, 0)
            
            if attempts >= self.max_recovery_attempts:
                logger.error("Max recovery attempts exceeded for %s", recovery_key)
                return False
            
            self.recovery_attempts[recovery_key] = attempts + 1
        
        try:
            if error.category == ErrorCategory.RENDERING:
                return self._recover_rendering_error(error, context)
            elif error.category == ErrorCategory.DRAWING:
                return self._recover_drawing_error(error, context)
            elif error.category == ErrorCategory.TOOL:
                return self._recover_tool_error(error, context)
            elif error.category == ErrorCategory.PERSISTENCE:
                return self._recover_persistence_error(error, context)
            else:
                return self._generic_recovery(error, context)
        except Exception as recovery_error:
            logger.error("Recovery attempt failed: %s", recovery_error)
            return False
    
    def _recover_rendering_error(self, error: ApplicationError, context: ErrorContext) -> bool:
        """Recover from rendering errors."""
        logger.info("Attempting rendering error recovery")
        
        # For rendering errors, try to continue without the failed operation
        if self.bus:
            self.bus.publish('rendering_recovery', {
                'operation': context.operation,
                'fallback_mode': True
            })
        return True
    
    def _recover_drawing_error(self, error: ApplicationError, context: ErrorContext) -> bool:
        """Recover from drawing errors."""
        logger.info("Attempting drawing error recovery")
        
        # Reset drawing state and continue
        if self.bus:
            self.bus.publish('drawing_recovery', {
                'reset_stroke': True,
                'operation': context.operation
            })
        return True
    
    def _recover_tool_error(self, error: ApplicationError, context: ErrorContext) -> bool:
        """Recover from tool errors."""
        logger.info("Attempting tool error recovery")
        
        # Switch to safe default tool (brush)
        if self.bus:
            self.bus.publish('tool_recovery', {
                'fallback_tool': 'brush',
                'operation': context.operation
            })
        return True
    
    def _recover_persistence_error(self, error: ApplicationError, context: ErrorContext) -> bool:
        """Recover from persistence errors."""
        logger.info("Attempting persistence error recovery")
        
        # Continue without saving for now
        if self.bus:
            self.bus.publish('persistence_recovery', {
                'disable_autosave': True,
                'operation': context.operation
            })
        return True
    
    def _generic_recovery(self, error: ApplicationError, context: ErrorContext) -> bool:
        """Generic recovery strategy."""
        logger.info("Attempting generic error recovery")
        
        # Log and continue - most errors are non-fatal
        return True
    
    def reset_recovery_attempts(self, category: Optional[ErrorCategory] = None) -> None:
        """Reset recovery attempt counters."""
        with self._lock:
            if category:
                keys_to_remove = [k for k in self.recovery_attempts.keys() 
                                if k.startswith(category.value)]
                for key in keys_to_remove:
                    del self.recovery_attempts[key]
            else:
                self.recovery_attempts.clear()
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics for monitoring."""
        with self._lock:
            return self.error_counts.copy()


def error_boundary(
    category: ErrorCategory,
    operation: str,
    component: str,
    boundary: Optional[ErrorBoundary] = None,
    fallback_value: Any = None,
    retry_attempts: int = 0
):
    """
    Decorator for wrapping functions with error boundary protection.
    
    Args:
        category: Error category for classification
        operation: Operation being performed
        component: Component performing the operation
        boundary: Error boundary instance (uses global if None)
        fallback_value: Value to return on unrecoverable error
        retry_attempts: Number of retry attempts
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            context = ErrorContext(
                operation=operation,
                component=component,
                system_state={'args': len(args), 'kwargs': list(kwargs.keys())}
            )
            
            # Use global error boundary if none provided
            error_handler = boundary or _global_error_boundary
            
            def execute():
                return func(*args, **kwargs)
            
            try:
                if retry_attempts > 0:
                    return ErrorRecoveryStrategy.retry_operation(execute, retry_attempts)
                else:
                    return execute()
                    
            except Exception as e:
                handled = error_handler.handle_error(e, context)
                
                if not handled:
                    if fallback_value is not None:
                        logger.warning("Using fallback value for %s.%s", component, operation)
                        return fallback_value
                    raise
                
                # If handled, return fallback or None
                return fallback_value
        
        return wrapper
    return decorator


# Global error boundary instance
_global_error_boundary = ErrorBoundary()


def get_global_error_boundary() -> ErrorBoundary:
    """Get the global error boundary instance."""
    return _global_error_boundary


def set_global_error_boundary(boundary: ErrorBoundary) -> None:
    """Set the global error boundary instance."""
    global _global_error_boundary
    _global_error_boundary = boundary


# Convenience decorators for common error boundaries
def rendering_boundary(operation: str, component: str = "renderer", fallback_value: Any = None):
    """Decorator for rendering operations."""
    return error_boundary(ErrorCategory.RENDERING, operation, component, fallback_value=fallback_value)


def drawing_boundary(operation: str, component: str = "drawing", fallback_value: Any = None):
    """Decorator for drawing operations.""" 
    return error_boundary(ErrorCategory.DRAWING, operation, component, fallback_value=fallback_value)


def tool_boundary(operation: str, component: str = "tool", fallback_value: Any = None):
    """Decorator for tool operations."""
    return error_boundary(ErrorCategory.TOOL, operation, component, fallback_value=fallback_value)


def persistence_boundary(operation: str, component: str = "persistence", fallback_value: Any = None):
    """Decorator for persistence operations."""
    return error_boundary(ErrorCategory.PERSISTENCE, operation, component, fallback_value=fallback_value)


# Example usage patterns:
"""
# Method decorator
class SomeService:
    @drawing_boundary("start_stroke", "journal_service")
    def start_stroke(self, x, y, width, color):
        # Drawing logic here
        pass
    
    @rendering_boundary("render_strokes", "journal_service", fallback_value=[])
    def render_strokes(self, renderer):
        # Rendering logic here
        pass

# Context manager usage
def some_critical_operation():
    context = ErrorContext("critical_op", "main_service")
    boundary = get_global_error_boundary()
    
    try:
        # Critical operation
        result = perform_operation()
    except Exception as e:
        if not boundary.handle_error(e, context):
            raise
        result = safe_fallback_value
    
    return result
"""