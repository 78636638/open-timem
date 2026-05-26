"""
TiMem FastAPI Application Entry Point

This module provides the main FastAPI application for the TiMem service,
including all API routes, middleware, and lifecycle management.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, List, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import uvicorn

from api.routes import memory_router, session_router, user_router, health_router, chat_router, web_router
from timem.utils.logging import get_logger, init_logging
from timem.utils.config_manager import get_config, ConfigManager

logger = get_logger(__name__)

_startup_time = datetime.now()
_initialized = False
_shutdown_event = asyncio.Event()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager - handles startup and shutdown.
    """
    global _initialized
    
    logger.info("Starting TiMem API service...")
    
    try:
        init_logging()
        logger.info("Logging system initialized")
        
        config = get_config()
        app_config = config.get("app", {})
        
        logger.info(f"TiMem API starting on {app_config.get('host', '0.0.0.0')}:{app_config.get('port', 8000)}")
        logger.info(f"Debug mode: {app_config.get('debug', False)}")
        
        _initialized = True
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}", exc_info=True)
        raise
    finally:
        logger.info("Shutting down TiMem API service...")
        
        try:
            from storage.memory_storage_manager import _storage_manager_instance_async
            
            if _storage_manager_instance_async is not None:
                await _storage_manager_instance_async.close_all_connections()
                logger.info("Storage connections closed")
        except Exception as e:
            logger.warning(f"Error closing storage connections: {e}")
        
        _initialized = False
        logger.info("TiMem API service stopped")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    config = get_config()
    app_config = config.get("app", {})
    
    application = FastAPI(
        title="TiMem API",
        description="Temporal Memory Tree API - A hierarchical memory system for AI assistants",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    application.add_middleware(GZipMiddleware, minimum_size=1000)
    
    application.include_router(health_router)
    application.include_router(memory_router)
    application.include_router(session_router)
    application.include_router(user_router)
    application.include_router(chat_router)
    application.include_router(web_router)
    
    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors"""
        return JSONResponse(
            status_code=422,
            content={
                "detail": exc.errors(),
                "body": str(exc.body) if hasattr(exc, 'body') else None
            }
        )
    
    @application.exception_handler(ValidationError)
    async def pydantic_validation_handler(request: Request, exc: ValidationError):
        """Handle Pydantic validation errors"""
        return JSONResponse(
            status_code=422,
            content={
                "detail": exc.errors()
            }
        )
    
    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    @application.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions"""
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if app_config.get("debug", False) else None
            }
        )
    
    @application.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests"""
        start_time = datetime.now()
        
        response = await call_next(request)
        
        process_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)"
        )
        
        return response
    
    @application.get("/", tags=["root"])
    async def root():
        """Root endpoint - API information"""
        return {
            "name": "TiMem API",
            "version": "1.0.0",
            "description": "Temporal Memory Tree API",
            "docs": "/docs",
            "health": "/api/v1/health"
        }
    
    @application.get("/api/info", tags=["root"])
    async def api_info():
        """API information endpoint"""
        config = get_config()
        
        return {
            "version": "1.0.0",
            "uptime_seconds": (datetime.now() - _startup_time).total_seconds(),
            "initialized": _initialized,
            "features": {
                "memory_generation": True,
                "memory_retrieval": True,
                "session_management": True,
                "user_management": True,
                "chat": True
            },
            "config": {
                "language": config.get("app", {}).get("language", "en"),
                "debug": config.get("app", {}).get("debug", False)
            }
        }
    
    return application


app = create_app()


def main():
    """Main entry point for running the application"""
    config = get_config()
    app_config = config.get("app", {})
    
    uvicorn.run(
        "app.main:app",
        host=app_config.get("host", "0.0.0.0"),
        port=app_config.get("port", 8000),
        reload=app_config.get("reload", False),
        workers=app_config.get("workers", 1),
        log_level="info" if not app_config.get("debug", False) else "debug",
        access_log=True
    )


if __name__ == "__main__":
    main()