"""
TiMem API Router - Health Check & System Status

Provides REST API endpoints for system health monitoring and diagnostics.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/health", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = "healthy"
    timestamp: str
    uptime_seconds: float
    version: str = "1.0.0"
    services: Dict[str, str] = {}


class SystemMetricsResponse(BaseModel):
    """System metrics response model"""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_available_mb: float = 0.0
    disk_usage_percent: float = 0.0
    active_connections: int = 0


class ServiceStatusResponse(BaseModel):
    """Service status response model"""
    status: str
    metrics: Dict[str, Any] = {}
    dependencies: Dict[str, str] = {}


_start_time = time.time()


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.
    
    Returns:
        HealthResponse with system status
    """
    uptime = time.time() - _start_time
    
    services = {
        "api": "healthy",
        "database": "unknown",
        "storage": "unknown"
    }
    
    try:
        from storage.memory_storage_manager import _storage_manager_instance_async
        
        if _storage_manager_instance_async is not None:
            services["storage"] = "healthy"
            
            if _storage_manager_instance_async.postgres_adapter:
                try:
                    pool_status = _storage_manager_instance_async.postgres_adapter.get_connection_pool_status()
                    if pool_status.get("status") in ["ok", "healthy"]:
                        services["database"] = "healthy"
                    else:
                        services["database"] = "degraded"
                except Exception:
                    services["database"] = "unknown"
        else:
            services["storage"] = "initializing"
            
    except Exception as e:
        logger.warning(f"Health check warning: {e}")
        services["storage"] = "degraded"
    
    overall_status = "healthy"
    if "unhealthy" in services.values():
        overall_status = "unhealthy"
    elif "degraded" in services.values() or "initializing" in services.values():
        overall_status = "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now().isoformat(),
        uptime_seconds=uptime,
        version="1.0.0",
        services=services
    )


@router.get("/ready", response_model=HealthResponse)
async def readiness_check() -> HealthResponse:
    """
    Kubernetes readiness probe endpoint.
    
    Returns:
        HealthResponse indicating if service is ready to accept traffic
    """
    services = {}
    all_ready = True
    
    try:
        from storage.memory_storage_manager import _storage_manager_instance_async
        
        if _storage_manager_instance_async is not None and _storage_manager_instance_async._initialized:
            services["storage"] = "ready"
        else:
            services["storage"] = "not_ready"
            all_ready = False
            
    except Exception as e:
        logger.warning(f"Readiness check failed: {e}")
        services["storage"] = "not_ready"
        all_ready = False
    
    return HealthResponse(
        status="ready" if all_ready else "not_ready",
        timestamp=datetime.now().isoformat(),
        uptime_seconds=time.time() - _start_time,
        services=services
    )


@router.get("/live", response_model=HealthResponse)
async def liveness_check() -> HealthResponse:
    """
    Kubernetes liveness probe endpoint.
    
    Returns:
        HealthResponse indicating if service is alive
    """
    return HealthResponse(
        status="alive",
        timestamp=datetime.now().isoformat(),
        uptime_seconds=time.time() - _start_time,
        services={"alive": "true"}
    )


@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics() -> SystemMetricsResponse:
    """
    Get system resource metrics.
    
    Returns:
        SystemMetricsResponse with CPU, memory, disk usage
    """
    try:
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return SystemMetricsResponse(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=round(memory.used / (1024 * 1024), 2),
            memory_available_mb=round(memory.available / (1024 * 1024), 2),
            disk_usage_percent=disk.percent
        )
        
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return SystemMetricsResponse()


@router.get("/services", response_model=ServiceStatusResponse)
async def get_services_status() -> ServiceStatusResponse:
    """
    Get detailed status of all services.
    
    Returns:
        ServiceStatusResponse with detailed service information
    """
    dependencies = {}
    metrics = {}
    
    try:
        from storage.memory_storage_manager import _storage_manager_instance_async
        from services.memory_generation_service import MemoryGenerationService
        
        storage = _storage_manager_instance_async
        if storage and storage._initialized:
            dependencies["storage"] = "healthy"
            
            if storage.postgres_adapter:
                pool_status = storage.postgres_adapter.get_connection_pool_status()
                metrics["connection_pool"] = pool_status
        else:
            dependencies["storage"] = "unhealthy"
        
        try:
            memory_service = MemoryGenerationService()
            
            if memory_service.status.value == "ready":
                dependencies["memory_generation"] = "healthy"
                metrics["memory_generation"] = {
                    "total_requests": memory_service.metrics.total_requests,
                    "successful_requests": memory_service.metrics.successful_requests,
                    "failed_requests": memory_service.metrics.failed_requests,
                    "active_workflows": memory_service.metrics.active_workflows,
                    "avg_processing_time": memory_service.metrics.avg_processing_time
                }
            else:
                dependencies["memory_generation"] = memory_service.status.value
        except Exception:
            dependencies["memory_generation"] = "unavailable"
            
    except Exception as e:
        logger.error(f"Failed to get services status: {e}")
        dependencies["service_layer"] = "error"
    
    return ServiceStatusResponse(
        status="healthy" if all(v == "healthy" for v in dependencies.values()) else "degraded",
        metrics=metrics,
        dependencies=dependencies
    )


@router.get("/config", response_model=Dict[str, Any])
async def get_config() -> Dict[str, Any]:
    """
    Get current configuration (non-sensitive).
    
    Returns:
        Configuration dictionary
    """
    try:
        from timem.utils.config_manager import get_config
        
        config = get_config()
        
        safe_config = {
            "app": config.get("app", {}),
            "retrieval": config.get("retrieval", {}),
            "memory_generation": config.get("memory_generation", {})
        }
        
        return safe_config
        
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        return {"error": str(e)}


@router.post("/reload-config", response_model=Dict[str, str])
async def reload_configuration() -> Dict[str, str]:
    """
    Reload configuration from files.
    
    Returns:
        Status message
    """
    try:
        from timem.utils.config_manager import ConfigManager
        
        ConfigManager().reload_config()
        
        return {"status": "success", "message": "Configuration reloaded"}
        
    except Exception as e:
        logger.error(f"Failed to reload config: {e}")
        return {"status": "error", "message": str(e)}