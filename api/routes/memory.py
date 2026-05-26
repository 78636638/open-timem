"""
TiMem API Router - Memory Operations

Provides REST API endpoints for memory operations including generation, retrieval, update, and deletion.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


class AddMemoryRequest(BaseModel):
    """Request model for adding memory"""
    messages: List[Dict[str, str]] = Field(..., description="Dialogue messages")
    user_id: str = Field(..., description="User ID")
    character_id: str = Field(..., description="Character/Expert ID")
    session_id: str = Field(..., description="Session ID")
    timestamp: Optional[datetime] = Field(None, description="Timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AddMemoryResponse(BaseModel):
    """Response model for adding memory"""
    success: bool
    total: int = 0
    memories: List[Dict[str, Any]] = []
    error: Optional[str] = None


class SearchMemoryRequest(BaseModel):
    """Request model for searching memory"""
    query: str = Field(..., description="Search query")
    user_id: str = Field(..., description="User ID")
    limit: int = Field(10, description="Maximum number of results")
    character_id: Optional[str] = Field(None, description="Character/Expert ID filter")
    session_id: Optional[str] = Field(None, description="Session ID filter")
    level: Optional[str] = Field(None, description="Memory level filter (L1-L5)")


class SearchMemoryResponse(BaseModel):
    """Response model for searching memory"""
    total: int = 0
    results: List[Dict[str, Any]] = []
    error: Optional[str] = None


class MemoryResponse(BaseModel):
    """Generic memory response model"""
    success: bool
    memory_id: Optional[str] = None
    error: Optional[str] = None


class MemoryDetailResponse(BaseModel):
    """Detailed memory response model"""
    success: bool
    memory: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class UpdateMemoryRequest(BaseModel):
    """Request model for updating memory"""
    content: Optional[str] = None
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MemoryStatsResponse(BaseModel):
    """Memory statistics response model"""
    total_memories: int = 0
    memories_by_level: Dict[str, int] = {}
    error: Optional[str] = None


@router.post("/add", response_model=AddMemoryResponse)
async def add_memory(request: AddMemoryRequest) -> AddMemoryResponse:
    """
    Add new memory from dialogue messages.
    
    Args:
        request: AddMemoryRequest containing messages, user_id, character_id, session_id
        
    Returns:
        AddMemoryResponse with generated memories
    """
    try:
        from services.memory_generation_service import MemoryGenerationService
        from services.memory_generation_service import MemoryGenerationRequest
        
        service = MemoryGenerationService()
        await service.initialize()
        
        content = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in request.messages
        ])
        
        memory_request = MemoryGenerationRequest(
            user_id=request.user_id,
            expert_id=request.character_id,
            session_id=request.session_id,
            content=content,
            timestamp=request.timestamp or datetime.now(),
            metadata=request.metadata
        )
        
        response = await service.generate_memory(memory_request)
        
        return AddMemoryResponse(
            success=response.success,
            total=len(response.memories),
            memories=response.memories,
            error=response.error
        )
        
    except Exception as e:
        logger.error(f"Failed to add memory: {e}")
        return AddMemoryResponse(
            success=False,
            error=str(e)
        )


@router.post("/search", response_model=SearchMemoryResponse)
async def search_memory(request: SearchMemoryRequest) -> SearchMemoryResponse:
    """
    Search memories based on query.
    
    Args:
        request: SearchMemoryRequest containing query, user_id, and optional filters
        
    Returns:
        SearchMemoryResponse with matching memories
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async
        from timem.workflows.memory_retrieval import MemoryRetrievalWorkflow
        
        storage_manager = await get_memory_storage_manager_async()
        
        if hasattr(storage_manager, 'search_memories'):
            results = await storage_manager.search_memories(
                query={
                    "query_text": request.query,
                    "user_id": request.user_id,
                    "expert_id": request.character_id,
                    "session_id": request.session_id,
                    "level": request.level
                },
                options={"limit": request.limit}
            )
            
            return SearchMemoryResponse(
                total=len(results),
                results=results
            )
        else:
            workflow = await MemoryRetrievalWorkflow.create(
                debug_mode=False,
                use_v2_retrievers=True
            )
            
            retrieval_result = await workflow.run({
                "question": request.query,
                "user_id": request.user_id,
                "expert_id": request.character_id or "default",
                "limit": request.limit
            })
            
            retrieved_memories = retrieval_result.get("retrieved_memories", [])
            
            return SearchMemoryResponse(
                total=len(retrieved_memories),
                results=retrieved_memories
            )
            
    except Exception as e:
        logger.error(f"Failed to search memory: {e}")
        return SearchMemoryResponse(
            total=0,
            results=[],
            error=str(e)
        )


@router.get("/{memory_id}", response_model=MemoryDetailResponse)
async def get_memory(
    memory_id: str,
    level: Optional[str] = Query(None, description="Memory level (L1-L5)")
) -> MemoryDetailResponse:
    """
    Get memory by ID.
    
    Args:
        memory_id: Memory ID
        level: Optional memory level filter
        
    Returns:
        MemoryDetailResponse with memory details
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async
        
        storage_manager = await get_memory_storage_manager_async()
        memory = await storage_manager.get_memory_by_id(memory_id, level=level)
        
        if not memory:
            raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")
        
        return MemoryDetailResponse(
            success=True,
            memory=memory
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get memory {memory_id}: {e}")
        return MemoryDetailResponse(
            success=False,
            error=str(e)
        )


@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: str,
    request: UpdateMemoryRequest
) -> MemoryResponse:
    """
    Update memory content.
    
    Args:
        memory_id: Memory ID
        request: UpdateMemoryRequest with new content/title/metadata
        
    Returns:
        MemoryResponse with update status
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async
        
        storage_manager = await get_memory_storage_manager_async()
        
        updates = {}
        if request.content:
            updates["content"] = request.content
        if request.title:
            updates["title"] = request.title
        if request.metadata:
            updates["metadata"] = request.metadata
        
        result = await storage_manager.update_memory(memory_id, updates)
        
        return MemoryResponse(
            success=result.get("success", False),
            memory_id=memory_id
        )
        
    except Exception as e:
        logger.error(f"Failed to update memory {memory_id}: {e}")
        return MemoryResponse(
            success=False,
            memory_id=memory_id,
            error=str(e)
        )


@router.delete("/{memory_id}", response_model=MemoryResponse)
async def delete_memory(
    memory_id: str,
    level: Optional[str] = Query(None, description="Memory level")
) -> MemoryResponse:
    """
    Delete memory by ID.
    
    Args:
        memory_id: Memory ID
        level: Optional memory level filter
        
    Returns:
        MemoryResponse with deletion status
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async
        
        storage_manager = await get_memory_storage_manager_async()
        result = await storage_manager.delete_memory(memory_id, level=level)
        
        return MemoryResponse(
            success=result.get("success", False),
            memory_id=memory_id
        )
        
    except Exception as e:
        logger.error(f"Failed to delete memory {memory_id}: {e}")
        return MemoryResponse(
            success=False,
            memory_id=memory_id,
            error=str(e)
        )


@router.get("/stats/user/{user_id}", response_model=MemoryStatsResponse)
async def get_user_memory_stats(user_id: str) -> MemoryStatsResponse:
    """
    Get memory statistics for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        MemoryStatsResponse with statistics
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async
        
        storage_manager = await get_memory_storage_manager_async()
        
        stats = {}
        for level in ["L1", "L2", "L3", "L4", "L5"]:
            try:
                count = await storage_manager.get_memory_count(
                    user_id=user_id,
                    expert_id="default",
                    layer=level
                )
                stats[level] = count
            except Exception:
                stats[level] = 0
        
        return MemoryStatsResponse(
            total_memories=sum(stats.values()),
            memories_by_level=stats
        )
        
    except Exception as e:
        logger.error(f"Failed to get memory stats for user {user_id}: {e}")
        return MemoryStatsResponse(
            error=str(e)
        )