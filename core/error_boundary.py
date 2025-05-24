"""
Unified Error Boundary Architecture - OPTIMIZED

Optimizations: __slots__, reduced validation, faster lookups, cached messages.
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
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories."""
    RENDERING = "rendering"
    INPUT = "input"
    PERSISTENCE = "persistence"
    DRAWING = "drawing"
    TOOL = "tool"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    SYSTEM = "system"

@dataclass(slots=True)
class ErrorContext:
    """Error context - optimized with slots."""
    operation: str
    component: str
    user_action: Optional[str] = None
    system_state: Optional[Dict[str, Any]] = None
    recovery_hints: Optional[List[str]] = None

# Pre-computed category messages for performance
CATEGORY_MESSAGES = {
    ErrorCategory.RENDERING: "Display issue encountered",
    ErrorCategory.INPUT: "Input handling problem", 
    ErrorCategory.DRAWING: "Drawing operation failed",
    ErrorCategory.TOOL: "Tool malfunction",
    ErrorCategory.PERSISTENCE: "Save/load issue",
    ErrorCategory.CONFIGURATION: "Configuration problem",
    ErrorCategory.NETWORK: "Network connectivity issue",
    ErrorCategory.SYSTEM: "System error"
}

class ApplicationError(Exception):
    """Base application error - optimized."""
    __slots__ = ('message', 'error_code', 'severity', 'category', 'context', 
                 'recoverable', 'user_message')
    
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
        """Generate user-friendly error message - optimized."""
        base_message = CATEGORY_MESSAGES.get(self.category, "Unknown error")
        
        if self.severity == ErrorSeverity.LOW:
            return f"{base_message} (minor)"
        elif self.severity == ErrorSeverity.CRITICAL:
            return f"Critical {base_message.lower()}"
        else:
            return base_message

class ErrorRecoveryStrategy:
    """Recovery strategies - optimized static methods."""
    
    @staticmethod
    def retry_operation(func: Callable, max_attempts: int = 3, delay: float = 0.1) -> Any:
        """Retry operation - optimized."""
        import time
        
        for attempt in range(max_attempts):
            try:
                return func()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                time.sleep(delay * (2 ** attempt))
    
    @staticmethod
    def graceful_degradation(primary_func: Callable, fallback_func: Callable) -> Any:
        """Try primary function, fall back to alternative."""
        try:
            return primary_func()
        except Exception:
            return fallback_func()
    
    @staticmethod
    def safe_default(func: Callable, default_value: Any) -> Any:
        """Execute function with safe default fallback."""
        try:
            return func()
        except Exception:
            return default_value

class ErrorBoundary:
    """Central error boundary - OPTIMIZED."""
    __slots__ = ('bus', 'error_counts', 'recovery_attempts', 'max_recovery_attempts', '_lock')
    
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
        """Handle error - optimized."""
        # Wrap exception if needed
        if isinstance(error, ApplicationError):
            app_error = error
        else:
            app_error = self._wrap_exception(error, context)
        
        # Log appropriately
        self._log_error_fast(app_error)
        
        # Track error frequency
        with self._lock:
            error_key = f"{app_error.category.value}:{app_error.error_code}"
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Publish error event
        if self.bus:
            try:
                self.bus.publish('error_occurred', {
                    'message': app_error.user_message,
                    'severity': app_error.severity.value,
                    'category': app_error.category.value,
                    'recoverable': app_error.recoverable,
                    'error_code': app_error.error_code
                })
            except Exception:
                pass  # Don't fail on event publishing
        
        # Attempt recovery
        if attempt_recovery and app_error.recoverable:
            return self._attempt_recovery_fast(app_error, context)
        
        return False
    
    def _wrap_exception(self, error: Exception, context: ErrorContext) -> ApplicationError:
        """Wrap exception - optimized."""
        error_type = type(error).__name__
        
        # Fast categorization
        severity = self._determine_severity_fast(error)
        category = self._determine_category_fast(error, context)
        
        return ApplicationError(
            message=str(error),
            error_code=f"{category.value}_{error_type}",
            severity=severity,
            category=category,
            context=context,
            recoverable=not isinstance(error, (MemoryError, SystemError))
        )
    
    def _determine_severity_fast(self, error: Exception) -> ErrorSeverity:
        """Fast severity determination."""
        if isinstance(error, (MemoryError, SystemError)):
            return ErrorSeverity.CRITICAL
        elif isinstance(error, (IOError, OSError)):
            return ErrorSeverity.HIGH
        elif isinstance(error, (ValueError, TypeError, AttributeError)):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _determine_category_fast(self, error: Exception, context: ErrorContext) -> ErrorCategory:
        """Fast category determination."""
        component = context.component.lower()
        
        # Fast component mapping
        if 'pygame' in component or 'render' in component:
            return ErrorCategory.RENDERING
        elif 'journal' in component or 'draw' in component:
            return ErrorCategory.DRAWING
        elif 'tool' in component:
            return ErrorCategory.TOOL
        elif 'database' in component or 'persist' in component:
            return ErrorCategory.PERSISTENCE
        elif 'input' in component:
            return ErrorCategory.INPUT
        elif isinstance(error, (IOError, OSError)):
            return ErrorCategory.PERSISTENCE
        else:
            return ErrorCategory.SYSTEM
    
    def _log_error_fast(self, error: ApplicationError) -> None:
        """Fast error logging."""
        log_message = f"[{error.category.value.upper()}] {error.message} (Code: {error.error_code})"
        
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def _attempt_recovery_fast(self, error: ApplicationError, context: ErrorContext) -> bool:
        """Fast recovery attempt."""
        with self._lock:
            recovery_key = f"{error.category.value}:{context.operation}"
            attempts = self.recovery_attempts.get(recovery_key, 0)
            
            if attempts >= self.max_recovery_attempts:
                return False
            
            self.recovery_attempts[recovery_key] = attempts + 1
        
        # Simple recovery based on category
        if self.bus:
            try:
                event_name = f"{error.category.value}_recovery"
                self.bus.publish(event_name, {'operation': context.operation})
                return True
            except Exception:
                return False
        
        return True  # Assume recovery succeeded
    
    def reset_recovery_attempts(self, category: Optional[ErrorCategory] = None) -> None:
        """Reset recovery attempts."""
        with self._lock:
            if category:
                prefix = category.value
                keys_to_remove = [k for k in self.recovery_attempts.keys() if k.startswith(prefix)]
                for key in keys_to_remove:
                    del self.recovery_attempts[key]
            else:
                self.recovery_attempts.clear()
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics."""
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
    """Optimized decorator for error boundary protection."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            context = ErrorContext(operation=operation, component=component)
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
                
                if not handled and fallback_value is not None:
                    return fallback_value
                elif not handled:
                    raise
                
                return fallback_value
        
        return wrapper
    return decorator

# Global error boundary
_global_error_boundary = ErrorBoundary()

def get_global_error_boundary() -> ErrorBoundary:
    """Get the global error boundary."""
    return _global_error_boundary

def set_global_error_boundary(boundary: ErrorBoundary) -> None:
    """Set the global error boundary."""
    global _global_error_boundary
    _global_error_boundary = boundary

# Optimized convenience decorators
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