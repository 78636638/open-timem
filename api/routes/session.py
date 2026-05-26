"""
TiMem API Router - Session Operations

Provides REST API endpoints for session management operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    """Request model for creating a session"""
    user_id: str = Field(..., description="User ID")
    expert_id: str = Field(..., description="Expert/Character ID")
    session_id: Optional[str] = Field(None, description="Session ID (auto-generated if empty)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SessionResponse(BaseModel):
    """Generic session response model"""
    success: bool
    session_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SessionListResponse(BaseModel):
    """Session list response model"""
    total: int = 0
    sessions: List[Dict[str, Any]] = []
    error: Optional[str] = None


class SessionDetailResponse(BaseModel):
    """Detailed session response model"""
    success: bool
    session: Optional[Dict[str, Any]] = None
    memories: List[Dict[str, Any]] = []
    error: Optional[str] = None


@router.post("/create", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest) -> SessionResponse:
    """
    Create a new session.
    
    Args:
        request: CreateSessionRequest containing user_id and expert_id
        
    Returns:
        SessionResponse with session information
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async
        
        storage_manager = await get_memory_storage_manager_async()
        
        session_id = await storage_manager.postgres_adapter.create_session(
            user_id=request.user_id,
            expert_id=request.expert_id,
            session_id=request.session_id
        )
        
        return SessionResponse(
            success=True,
            session_id=session_id,
            data={
                "user_id": request.user_id,
                "expert_id": request.expert_id,
                "created_at": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        return SessionResponse(
            success=False,
            error=str(e)
        )


@router.get("/user/{user_id}", response_model=SessionListResponse)
async def get_user_sessions(
    user_id: str,
    expert_id: Optional[str] = Query(None, description="Expert ID filter"),
    limit: int = Query(50, description="Maximum number of results"),
    offset: int = Query(0, description="Offset for pagination")
) -> SessionListResponse:
    """
    Get all sessions for a user.
    
    Args:
        user_id: User ID
        expert_id: Optional expert ID filter
        limit: Maximum number of results
        offset: Offset for pagination
        
    Returns:
        SessionListResponse with sessions
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async
        
        storage_manager = await get_memory_storage_manager_async()
        
        criteria = {"user_id": user_id}
        if expert_id:
            criteria["expert_id"] = expert_id
        
        sessions = await storage_manager.postgres_adapter.find_memories_by_criteria(
            memory_type="session",
            limit=limit,
            offset=offset,
            **criteria
        )
        
        return SessionListResponse(
            total=len(sessions),
            sessions=sessions
        )
        
    except Exception as e:
        logger.error(f"Failed to get sessions for user {user_id}: {e}")
        return SessionListResponse(
            total=0,
            sessions=[],
            error=str(e)
        )


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str) -> SessionDetailResponse:
    """
    Get session details and associated memories.
    
    Args:
        session_id: Session ID
        
    Returns:
        SessionDetailResponse with session details and memories
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async
        
        storage_manager = await get_memory_storage_manager_async()
        
        memories = await storage_manager.postgres_adapter.get_session_memories(session_id)
        
        return SessionDetailResponse(
            success=True,
            session={"session_id": session_id},
            memories=memories
        )
        
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        return SessionDetailResponse(
            success=False,
            error=str(e)
        )


@router.get("/{session_id}/dialogues", response_model=SessionResponse)
async def get_session_dialogues(session_id: str) -> SessionResponse:
    """
    Get dialogue history for a session.
    
    Args:
        session_id: Session ID
        
    Returns:
        SessionResponse with dialogue history
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async
        
        storage_manager = await get_memory_storage_manager_async()
        
        dialogues = await storage_manager.postgres_adapter.get_session_dialogues(session_id)
        
        return SessionResponse(
            success=True,
            session_id=session_id,
            data={"dialogues": dialogues}
        )
        
    except Exception as e:
        logger.error(f"Failed to get dialogues for session {session_id}: {e}")
        return SessionResponse(
            success=False,
            session_id=session_id,
            error=str(e)
        )


@router.delete("/{session_id}", response_model=SessionResponse)
async def delete_session(session_id: str) -> SessionResponse:
    """
    Delete a session and its associated memories.
    
    Args:
        session_id: Session ID
        
    Returns:
        SessionResponse with deletion status
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async
        
        storage_manager = await get_memory_storage_manager_async()
        
        memories = await storage_manager.postgres_adapter.get_session_memories(session_id)
        
        deleted_count = 0
        for memory in memories:
            memory_id = memory.get("id")
            if memory_id:
                result = await storage_manager.delete_memory(memory_id)
                if result.get("success"):
                    deleted_count += 1
        
        return SessionResponse(
            success=True,
            session_id=session_id,
            data={"deleted_memories": deleted_count}
        )
        
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        return SessionResponse(
            success=False,
            session_id=session_id,
            error=str(e)
        )