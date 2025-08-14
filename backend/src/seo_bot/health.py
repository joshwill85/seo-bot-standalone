"""Health check endpoints and monitoring utilities."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
import psutil
import os

from sqlalchemy import text
from .db import db_manager, get_db_session
from .config import settings


class HealthChecker:
    """Comprehensive health checking for all system components."""
    
    def __init__(self):
        self.start_time = time.time()
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        start_time = time.time()
        try:
            with db_manager.session_scope() as session:
                # Test basic connectivity
                result = session.execute(text("SELECT 1")).scalar()
                
                # Test write capability
                session.execute(text("CREATE TEMP TABLE health_check (id INTEGER)"))
                session.execute(text("INSERT INTO health_check VALUES (1)"))
                session.execute(text("SELECT * FROM health_check"))
                session.execute(text("DROP TABLE health_check"))
                
                response_time = (time.time() - start_time) * 1000
                
                return {
                    "status": "healthy" if result == 1 else "unhealthy",
                    "response_time_ms": round(response_time, 2),
                    "database_url": settings.database_url.split('@')[0] + '@***',  # Hide credentials
                    "message": "Database connection successful"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "error": str(e),
                "message": "Database connection failed"
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        start_time = time.time()
        try:
            import redis
            
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            r = redis.from_url(redis_url)
            
            # Test basic connectivity
            ping_result = r.ping()
            
            # Test read/write
            test_key = f"health_check_{int(time.time())}"
            r.set(test_key, "test_value", ex=10)  # Expire in 10 seconds
            value = r.get(test_key)
            r.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy" if ping_result and value == b"test_value" else "unhealthy",
                "response_time_ms": round(response_time, 2),
                "message": "Redis connection successful"
            }
        except ImportError:
            return {
                "status": "skipped",
                "message": "Redis client not installed"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "error": str(e),
                "message": "Redis connection failed"
            }
    
    async def check_external_apis(self) -> Dict[str, Any]:
        """Check external API connectivity."""
        checks = {}
        
        # Google PageSpeed Insights API
        pagespeed_key = os.environ.get('PAGESPEED_API_KEY')
        if pagespeed_key:
            start_time = time.time()
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
                        params={"url": "https://www.google.com", "key": pagespeed_key},
                        timeout=10.0
                    )
                    checks["pagespeed_api"] = {
                        "status": "healthy" if response.status_code == 200 else "unhealthy",
                        "response_time_ms": round((time.time() - start_time) * 1000, 2),
                        "status_code": response.status_code
                    }
            except Exception as e:
                checks["pagespeed_api"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        # OpenAI API
        openai_key = os.environ.get('OPENAI_API_KEY')
        if openai_key:
            start_time = time.time()
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {openai_key}"},
                        timeout=10.0
                    )
                    checks["openai_api"] = {
                        "status": "healthy" if response.status_code == 200 else "unhealthy",
                        "response_time_ms": round((time.time() - start_time) * 1000, 2),
                        "status_code": response.status_code
                    }
            except Exception as e:
                checks["openai_api"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        return checks if checks else {"status": "skipped", "message": "No external APIs configured"}
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Process info
            process = psutil.Process()
            process_memory = process.memory_info()
            
            return {
                "status": "healthy",
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent_used": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent_used": round((disk.used / disk.total) * 100, 2)
                },
                "process_memory_mb": round(process_memory.rss / (1024**2), 2)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_application_info(self) -> Dict[str, Any]:
        """Get application runtime information."""
        uptime_seconds = time.time() - self.start_time
        
        return {
            "status": "healthy",
            "environment": settings.environment,
            "version": "1.0.0",  # Could be read from a version file
            "uptime_seconds": round(uptime_seconds, 2),
            "uptime_human": self._format_uptime(uptime_seconds),
            "start_time": datetime.fromtimestamp(self.start_time, timezone.utc).isoformat(),
            "current_time": datetime.now(timezone.utc).isoformat(),
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
        }
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format."""
        days, remainder = divmod(int(seconds), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        
        return " ".join(parts)
    
    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status."""
        start_time = time.time()
        
        # Run all checks
        database_check = await self.check_database()
        redis_check = await self.check_redis()
        external_apis_check = await self.check_external_apis()
        system_check = self.check_system_resources()
        app_info = self.get_application_info()
        
        # Determine overall status
        checks = [database_check, redis_check, system_check]
        if isinstance(external_apis_check, dict) and external_apis_check.get("status") not in ["skipped"]:
            checks.extend(external_apis_check.values() if isinstance(external_apis_check, dict) else [external_apis_check])
        
        unhealthy_checks = [check for check in checks if check.get("status") == "unhealthy"]
        overall_status = "unhealthy" if unhealthy_checks else "healthy"
        
        total_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response_time_ms": total_time,
            "checks": {
                "database": database_check,
                "redis": redis_check,
                "external_apis": external_apis_check,
                "system_resources": system_check,
                "application": app_info
            },
            "summary": {
                "total_checks": len(checks),
                "healthy_checks": len([c for c in checks if c.get("status") == "healthy"]),
                "unhealthy_checks": len(unhealthy_checks),
                "skipped_checks": len([c for c in checks if c.get("status") == "skipped"])
            }
        }
    
    async def readiness_check(self) -> Dict[str, Any]:
        """Check if the application is ready to receive traffic."""
        start_time = time.time()
        
        # Essential checks for readiness
        database_check = await self.check_database()
        
        # Application is ready if database is healthy
        is_ready = database_check.get("status") == "healthy"
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            "status": "ready" if is_ready else "not_ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response_time_ms": response_time,
            "checks": {
                "database": database_check
            }
        }
    
    async def liveness_check(self) -> Dict[str, Any]:
        """Check if the application is alive (basic health check)."""
        return {
            "status": "alive",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": round(time.time() - self.start_time, 2)
        }


# Global health checker instance
health_checker = HealthChecker()