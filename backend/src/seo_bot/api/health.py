"""Health check API endpoints."""

from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse
from typing import Dict, Any

from ..health import health_checker

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint.
    
    Returns detailed health information about all system components:
    - Database connectivity
    - Redis connectivity  
    - External API status
    - System resources
    - Application info
    """
    health_data = await health_checker.comprehensive_health_check()
    
    # Set appropriate HTTP status code
    if health_data["status"] == "healthy":
        status_code = status.HTTP_200_OK
    else:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        content=health_data,
        status_code=status_code
    )


@router.get("/health/readiness", tags=["Health"])
async def readiness_check() -> Dict[str, Any]:
    """
    Kubernetes readiness probe endpoint.
    
    Checks if the application is ready to receive traffic.
    Returns 200 if ready, 503 if not ready.
    """
    readiness_data = await health_checker.readiness_check()
    
    if readiness_data["status"] == "ready":
        status_code = status.HTTP_200_OK
    else:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        content=readiness_data,
        status_code=status_code
    )


@router.get("/health/liveness", tags=["Health"])
async def liveness_check() -> Dict[str, Any]:
    """
    Kubernetes liveness probe endpoint.
    
    Basic check to determine if the application is alive.
    Always returns 200 unless the application is completely down.
    """
    liveness_data = await health_checker.liveness_check()
    
    return JSONResponse(
        content=liveness_data,
        status_code=status.HTTP_200_OK
    )


@router.get("/health/database", tags=["Health"])
async def database_health() -> Dict[str, Any]:
    """
    Database-specific health check.
    
    Returns detailed information about database connectivity and performance.
    """
    db_health = await health_checker.check_database()
    
    if db_health["status"] == "healthy":
        status_code = status.HTTP_200_OK
    else:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        content=db_health,
        status_code=status_code
    )


@router.get("/health/redis", tags=["Health"])
async def redis_health() -> Dict[str, Any]:
    """
    Redis-specific health check.
    
    Returns information about Redis connectivity and performance.
    """
    redis_health = await health_checker.check_redis()
    
    if redis_health["status"] == "healthy":
        status_code = status.HTTP_200_OK
    elif redis_health["status"] == "skipped":
        status_code = status.HTTP_200_OK
    else:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        content=redis_health,
        status_code=status_code
    )


@router.get("/metrics", tags=["Monitoring"])
async def prometheus_metrics() -> Response:
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus format for monitoring and alerting.
    """
    try:
        health_data = await health_checker.comprehensive_health_check()
        
        # Convert health data to Prometheus format
        metrics = _convert_to_prometheus_metrics(health_data)
        
        return Response(
            content=metrics,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        return Response(
            content=f"# Error generating metrics: {str(e)}\n",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            media_type="text/plain"
        )


def _convert_to_prometheus_metrics(health_data: Dict[str, Any]) -> str:
    """Convert health check data to Prometheus metrics format."""
    lines = []
    
    # Add metadata
    lines.append("# HELP seo_bot_health_status Overall health status of the application")
    lines.append("# TYPE seo_bot_health_status gauge")
    lines.append(f"seo_bot_health_status{{status=\"{health_data['status']}\"}} {1 if health_data['status'] == 'healthy' else 0}")
    
    lines.append("# HELP seo_bot_response_time_ms Health check response time in milliseconds")
    lines.append("# TYPE seo_bot_response_time_ms gauge")
    lines.append(f"seo_bot_response_time_ms {health_data['response_time_ms']}")
    
    # Database metrics
    db_check = health_data["checks"]["database"]
    lines.append("# HELP seo_bot_database_status Database connectivity status")
    lines.append("# TYPE seo_bot_database_status gauge")
    lines.append(f"seo_bot_database_status{{status=\"{db_check['status']}\"}} {1 if db_check['status'] == 'healthy' else 0}")
    
    if "response_time_ms" in db_check:
        lines.append("# HELP seo_bot_database_response_time_ms Database response time in milliseconds")
        lines.append("# TYPE seo_bot_database_response_time_ms gauge")
        lines.append(f"seo_bot_database_response_time_ms {db_check['response_time_ms']}")
    
    # Redis metrics
    redis_check = health_data["checks"]["redis"]
    if redis_check["status"] != "skipped":
        lines.append("# HELP seo_bot_redis_status Redis connectivity status")
        lines.append("# TYPE seo_bot_redis_status gauge")
        lines.append(f"seo_bot_redis_status{{status=\"{redis_check['status']}\"}} {1 if redis_check['status'] == 'healthy' else 0}")
        
        if "response_time_ms" in redis_check:
            lines.append("# HELP seo_bot_redis_response_time_ms Redis response time in milliseconds")
            lines.append("# TYPE seo_bot_redis_response_time_ms gauge")
            lines.append(f"seo_bot_redis_response_time_ms {redis_check['response_time_ms']}")
    
    # System resource metrics
    system_check = health_data["checks"]["system_resources"]
    if system_check["status"] == "healthy":
        lines.append("# HELP seo_bot_cpu_percent CPU usage percentage")
        lines.append("# TYPE seo_bot_cpu_percent gauge")
        lines.append(f"seo_bot_cpu_percent {system_check['cpu_percent']}")
        
        lines.append("# HELP seo_bot_memory_percent Memory usage percentage")
        lines.append("# TYPE seo_bot_memory_percent gauge")
        lines.append(f"seo_bot_memory_percent {system_check['memory']['percent_used']}")
        
        lines.append("# HELP seo_bot_disk_percent Disk usage percentage")
        lines.append("# TYPE seo_bot_disk_percent gauge")
        lines.append(f"seo_bot_disk_percent {system_check['disk']['percent_used']}")
        
        lines.append("# HELP seo_bot_process_memory_mb Process memory usage in MB")
        lines.append("# TYPE seo_bot_process_memory_mb gauge")
        lines.append(f"seo_bot_process_memory_mb {system_check['process_memory_mb']}")
    
    # Application metrics
    app_info = health_data["checks"]["application"]
    lines.append("# HELP seo_bot_uptime_seconds Application uptime in seconds")
    lines.append("# TYPE seo_bot_uptime_seconds counter")
    lines.append(f"seo_bot_uptime_seconds {app_info['uptime_seconds']}")
    
    # Summary metrics
    summary = health_data["summary"]
    lines.append("# HELP seo_bot_total_checks Total number of health checks")
    lines.append("# TYPE seo_bot_total_checks gauge")
    lines.append(f"seo_bot_total_checks {summary['total_checks']}")
    
    lines.append("# HELP seo_bot_healthy_checks Number of healthy checks")
    lines.append("# TYPE seo_bot_healthy_checks gauge")
    lines.append(f"seo_bot_healthy_checks {summary['healthy_checks']}")
    
    lines.append("# HELP seo_bot_unhealthy_checks Number of unhealthy checks")
    lines.append("# TYPE seo_bot_unhealthy_checks gauge")
    lines.append(f"seo_bot_unhealthy_checks {summary['unhealthy_checks']}")
    
    return "\n".join(lines) + "\n"