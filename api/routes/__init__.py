"""
TiMem API Routes Package

This package contains all API route modules for the TiMem service.
"""

from .memory import router as memory_router
from .session import router as session_router
from .user import router as user_router
from .health import router as health_router
from .chat import router as chat_router
from .web import router as web_router

__all__ = [
    "memory_router",
    "session_router",
    "user_router",
    "health_router",
    "chat_router",
    "web_router"
]