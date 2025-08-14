"""Monitoring and error handling utilities for technical systems."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union
from functools import wraps
from dataclasses import dataclass
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring."""
    
    operation_name: str
    start_time: float
    end_time: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    @property
    def duration_ms(self) -> float:
        """Calculate duration in milliseconds."""
        return (self.end_time - self.start_time) * 1000
    
    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds."""
        return self.end_time - self.start_time


class PerformanceMonitor:
    """Monitor performance and errors across technical systems."""
    
    def __init__(self):
        """Initialize performance monitor."""
        self.metrics: List[PerformanceMetrics] = []
        self.error_counts: Dict[str, int] = {}
        self.success_counts: Dict[str, int] = {}
    
    def record_metric(self, metric: PerformanceMetrics) -> None:
        """Record a performance metric."""
        self.metrics.append(metric)
        
        # Update counters
        if metric.success:
            self.success_counts[metric.operation_name] = self.success_counts.get(metric.operation_name, 0) + 1
        else:
            self.error_counts[metric.operation_name] = self.error_counts.get(metric.operation_name, 0) + 1
    
    def get_stats(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics."""
        if operation_name:
            relevant_metrics = [m for m in self.metrics if m.operation_name == operation_name]
        else:
            relevant_metrics = self.metrics
        
        if not relevant_metrics:
            return {"error": "No metrics found"}
        
        durations = [m.duration_ms for m in relevant_metrics]
        success_count = len([m for m in relevant_metrics if m.success])
        error_count = len([m for m in relevant_metrics if not m.success])
        
        return {
            "operation_name": operation_name or "all_operations",
            "total_calls": len(relevant_metrics),
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": success_count / len(relevant_metrics) if relevant_metrics else 0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "min_duration_ms": min(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "p95_duration_ms": self._percentile(durations, 95) if durations else 0,
            "p99_duration_ms": self._percentile(durations, 99) if durations else 0
        }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def export_metrics(self, output_path: Path) -> None:
        """Export metrics to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        export_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": self.get_stats(),
            "metrics": [
                {
                    "operation_name": m.operation_name,
                    "start_time": m.start_time,
                    "end_time": m.end_time,
                    "duration_ms": m.duration_ms,
                    "success": m.success,
                    "error_message": m.error_message,
                    "metadata": m.metadata
                }
                for m in self.metrics
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Metrics exported to {output_path}")


# Global performance monitor instance
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return _performance_monitor


def monitor_performance(operation_name: str):
    """Decorator to monitor function performance."""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                error_message = None
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error_message = str(e)
                    logger.error(f"Error in {operation_name}: {e}")
                    raise
                finally:
                    end_time = time.time()
                    metric = PerformanceMetrics(
                        operation_name=operation_name,
                        start_time=start_time,
                        end_time=end_time,
                        success=success,
                        error_message=error_message
                    )
                    _performance_monitor.record_metric(metric)
            
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                error_message = None
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error_message = str(e)
                    logger.error(f"Error in {operation_name}: {e}")
                    raise
                finally:
                    end_time = time.time()
                    metric = PerformanceMetrics(
                        operation_name=operation_name,
                        start_time=start_time,
                        end_time=end_time,
                        success=success,
                        error_message=error_message
                    )
                    _performance_monitor.record_metric(metric)
            
            return sync_wrapper
    
    return decorator


@asynccontextmanager
async def monitor_operation(operation_name: str, metadata: Optional[Dict[str, Any]] = None):
    """Context manager to monitor operation performance."""
    start_time = time.time()
    success = True
    error_message = None
    
    try:
        yield
    except Exception as e:
        success = False
        error_message = str(e)
        logger.error(f"Error in {operation_name}: {e}")
        raise
    finally:
        end_time = time.time()
        metric = PerformanceMetrics(
            operation_name=operation_name,
            start_time=start_time,
            end_time=end_time,
            success=success,
            error_message=error_message,
            metadata=metadata
        )
        _performance_monitor.record_metric(metric)


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_backoff: bool = True,
        jitter: bool = True
    ):
        """Initialize retry configuration."""
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_backoff = exponential_backoff
        self.jitter = jitter


async def retry_with_backoff(
    func: Callable,
    config: RetryConfig,
    operation_name: str,
    *args,
    **kwargs
) -> Any:
    """Retry function with exponential backoff."""
    import random
    
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            async with monitor_operation(f"{operation_name}_attempt_{attempt + 1}"):
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
        
        except Exception as e:
            last_exception = e
            
            if attempt == config.max_attempts - 1:
                logger.error(f"All {config.max_attempts} attempts failed for {operation_name}: {e}")
                break
            
            # Calculate delay
            if config.exponential_backoff:
                delay = config.base_delay * (2 ** attempt)
            else:
                delay = config.base_delay
            
            delay = min(delay, config.max_delay)
            
            # Add jitter
            if config.jitter:
                delay *= (0.5 + random.random() * 0.5)
            
            logger.warning(f"Attempt {attempt + 1} failed for {operation_name}: {e}. Retrying in {delay:.2f}s")
            await asyncio.sleep(delay)
    
    # If we get here, all attempts failed
    raise last_exception


class HealthChecker:
    """Health checker for technical systems."""
    
    def __init__(self):
        """Initialize health checker."""
        self.health_checks: Dict[str, Callable] = {}
    
    def register_check(self, name: str, check_func: Callable) -> None:
        """Register a health check function."""
        self.health_checks[name] = check_func
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_healthy": True,
            "checks": {}
        }
        
        for name, check_func in self.health_checks.items():
            try:
                async with monitor_operation(f"health_check_{name}"):
                    if asyncio.iscoroutinefunction(check_func):
                        check_result = await check_func()
                    else:
                        check_result = check_func()
                    
                    if isinstance(check_result, bool):
                        check_result = {"healthy": check_result}
                    
                    results["checks"][name] = {
                        "healthy": check_result.get("healthy", True),
                        "message": check_result.get("message", "OK"),
                        "details": check_result.get("details", {})
                    }
                    
                    if not check_result.get("healthy", True):
                        results["overall_healthy"] = False
            
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                results["checks"][name] = {
                    "healthy": False,
                    "message": f"Check failed: {str(e)}",
                    "details": {"error": str(e)}
                }
                results["overall_healthy"] = False
        
        return results


# Global health checker instance
_health_checker = HealthChecker()


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance."""
    return _health_checker


# Default health checks
async def check_memory_usage() -> Dict[str, Any]:
    """Check memory usage."""
    import psutil
    
    try:
        memory = psutil.virtual_memory()
        healthy = memory.percent < 85  # Alert if memory usage > 85%
        
        return {
            "healthy": healthy,
            "message": f"Memory usage: {memory.percent:.1f}%",
            "details": {
                "percent_used": memory.percent,
                "available_gb": memory.available / (1024**3),
                "total_gb": memory.total / (1024**3)
            }
        }
    except ImportError:
        return {
            "healthy": True,
            "message": "psutil not available - memory check skipped"
        }


async def check_disk_space() -> Dict[str, Any]:
    """Check disk space."""
    import shutil
    
    try:
        total, used, free = shutil.disk_usage("/")
        percent_used = (used / total) * 100
        healthy = percent_used < 90  # Alert if disk usage > 90%
        
        return {
            "healthy": healthy,
            "message": f"Disk usage: {percent_used:.1f}%",
            "details": {
                "percent_used": percent_used,
                "free_gb": free / (1024**3),
                "total_gb": total / (1024**3)
            }
        }
    except Exception as e:
        return {
            "healthy": False,
            "message": f"Disk check failed: {str(e)}"
        }


# Register default health checks
_health_checker.register_check("memory", check_memory_usage)
_health_checker.register_check("disk", check_disk_space)


class CircuitBreaker:
    """Circuit breaker pattern for handling failures."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply circuit breaker."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == "open":
                if self._should_attempt_reset():
                    self.state = "half-open"
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                self._on_success()
                return result
            
            except self.expected_exception as e:
                self._on_failure()
                raise
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        if self.last_failure_time is None:
            return True
        
        return time.time() - self.last_failure_time >= self.reset_timeout
    
    def _on_success(self) -> None:
        """Handle successful operation."""
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self) -> None:
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


def setup_error_handling() -> None:
    """Set up comprehensive error handling."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('seo_bot_technical.log')
        ]
    )
    
    # Set specific log levels for noisy libraries
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    logger.info("Error handling and monitoring setup completed")