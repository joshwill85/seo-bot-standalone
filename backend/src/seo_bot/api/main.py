"""Main FastAPI application with all middleware integrated."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from ..config import settings
from ..health import health_checker
from ..middleware.api_gateway import APIGatewayMiddleware, CORSMiddleware as CustomCORSMiddleware
from ..middleware.rate_limiting import RateLimitMiddleware, rate_limiter
from ..middleware.auth import AuthMiddleware
from .health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("🚀 Starting SEO Bot API...")
    
    # Initialize database
    try:
        from ..db import db_manager
        if db_manager.health_check():
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
    
    # Initialize other services
    print("✅ Application startup complete")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down SEO Bot API...")
    print("✅ Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    # Create FastAPI app
    app = FastAPI(
        title="SEO Bot API",
        description="AI-Powered SEO Automation Platform API",
        version="1.0.0",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan,
        openapi_tags=[
            {
                "name": "Health",
                "description": "Health check and monitoring endpoints"
            },
            {
                "name": "Authentication",
                "description": "User authentication and authorization"
            },
            {
                "name": "Keywords",
                "description": "Keyword research and analysis"
            },
            {
                "name": "Projects",
                "description": "Project management"
            },
            {
                "name": "Analytics",
                "description": "SEO analytics and reporting"
            }
        ]
    )
    
    # Configure middleware
    configure_middleware(app)
    
    # Include routers
    include_routers(app)
    
    # Add exception handlers
    add_exception_handlers(app)
    
    return app


def configure_middleware(app: FastAPI):
    """Configure application middleware."""
    
    # Trusted hosts (security)
    allowed_hosts = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if settings.environment == 'production':
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=allowed_hosts
        )
    
    # API Gateway (custom middleware for logging, versioning, etc.)
    app.add_middleware(
        APIGatewayMiddleware,
        config={
            'enable_request_logging': True,
            'enable_response_logging': True,
        }
    )
    
    # Rate limiting
    app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
    
    # Authentication
    app.add_middleware(AuthMiddleware)
    
    # CORS
    cors_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:8080').split(',')
    app.add_middleware(
        CustomCORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Accept",
            "Accept-Language", 
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "X-Request-ID",
            "API-Version"
        ],
        expose_headers=[
            "X-Request-ID",
            "X-Response-Time", 
            "X-API-Version",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset"
        ]
    )
    
    # Gzip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)


def include_routers(app: FastAPI):
    """Include API routers."""
    
    # Health endpoints
    app.include_router(
        health_router,
        tags=["Health"]
    )
    
    # API v1 routes
    from .v1 import router as v1_router
    app.include_router(
        v1_router,
        prefix="/api/v1"
    )


def add_exception_handlers(app: FastAPI):
    """Add custom exception handlers."""
    
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "type": "not_found",
                    "code": 404,
                    "message": "The requested resource was not found",
                    "path": request.url.path,
                    "method": request.method,
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            }
        )
    
    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc):
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "internal_error",
                    "code": 500,
                    "message": "An internal server error occurred",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            }
        )


# Create the app instance
app = create_app()


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "SEO Bot API",
        "version": "1.0.0",
        "description": "AI-Powered SEO Automation Platform",
        "documentation": "/docs",
        "health": "/health",
        "api": {
            "v1": "/api/v1"
        },
        "links": {
            "website": "https://seobot.ai",
            "documentation": "https://docs.seobot.ai",
            "support": "https://support.seobot.ai"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        access_log=True,
        log_level=settings.log_level.lower()
    )