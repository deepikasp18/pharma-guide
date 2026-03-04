"""
Circuit breaker pattern implementation for resilience
"""
import asyncio
import logging
from typing import Callable, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for external service calls
    
    Prevents cascading failures by temporarily blocking calls to failing services
    and allowing them time to recover.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.last_failure_time is None:
            return False
        
        time_since_failure = datetime.utcnow() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker closing - service recovered")
            self.state = CircuitState.CLOSED
        
        self.failure_count = 0
        self.last_failure_time = None
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.warning(
                    f"Circuit breaker opening - {self.failure_count} failures detected"
                )
                self.state = CircuitState.OPEN
    
    def reset(self):
        """Manually reset circuit breaker"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        logger.info("Circuit breaker manually reset")


class RetryPolicy:
    """
    Retry policy with exponential backoff
    
    Automatically retries failed operations with increasing delays.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ):
        """
        Initialize retry policy
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic
        
        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = min(
                        self.initial_delay * (self.exponential_base ** attempt),
                        self.max_delay
                    )
                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay}s: {str(e)}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed")
        
        raise last_exception


class FallbackHandler:
    """
    Fallback handler for degraded service operation
    
    Provides alternative responses when primary services are unavailable.
    """
    
    def __init__(self, cache_ttl: int = 300):
        """
        Initialize fallback handler
        
        Args:
            cache_ttl: Cache time-to-live in seconds
        """
        self.cache_ttl = cache_ttl
        self.cache = {}
    
    async def execute_with_fallback(
        self,
        primary_func: Callable,
        fallback_func: Callable,
        cache_key: Optional[str] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute primary function with fallback
        
        Args:
            primary_func: Primary async function to execute
            fallback_func: Fallback async function if primary fails
            cache_key: Optional cache key for storing results
            *args: Positional arguments for functions
            **kwargs: Keyword arguments for functions
            
        Returns:
            Function result from primary or fallback
        """
        try:
            result = await primary_func(*args, **kwargs)
            
            # Cache successful result
            if cache_key:
                self.cache[cache_key] = {
                    'data': result,
                    'timestamp': datetime.utcnow()
                }
            
            return result
        except Exception as e:
            logger.warning(f"Primary function failed, using fallback: {str(e)}")
            
            # Try cached data first
            if cache_key and cache_key in self.cache:
                cached = self.cache[cache_key]
                age = (datetime.utcnow() - cached['timestamp']).total_seconds()
                
                if age < self.cache_ttl:
                    logger.info(f"Returning cached data (age: {age}s)")
                    return cached['data']
            
            # Use fallback function
            return await fallback_func(*args, **kwargs)
    
    def clear_cache(self, cache_key: Optional[str] = None):
        """Clear cache entries"""
        if cache_key:
            self.cache.pop(cache_key, None)
        else:
            self.cache.clear()
