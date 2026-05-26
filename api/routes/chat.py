"""
TiMem API Router - Chat Operations

Provides REST API endpoints for human-AI conversation with memory integration.
This module enables intelligent chat responses by:
1. Searching relevant memories before responding
2. Building context from retrieved memories
3. Generating responses using LLM or mock responses
4. Saving conversation to memory automatically
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """Single chat message model"""
    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request model for chat with memory integration"""
    message: str = Field(..., description="User message")
    user_id: str = Field(..., description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID (auto-generated if not provided)")
    character_id: Optional[str] = Field("chat_assistant", description="Character/Expert ID")
    search_limit: int = Field(5, description="Number of memories to search")
    temperature: float = Field(0.7, description="LLM temperature", ge=0.0, le=2.0)
    max_tokens: int = Field(500, description="Maximum tokens in response", ge=50, le=2000)
    save_to_memory: bool = Field(True, description="Whether to save conversation to memory")
    llm_provider: Optional[str] = Field(None, description="LLM provider to use (minimax, zhipuai, openai, etc.)")


class ChatResponse(BaseModel):
    """Response model for chat"""
    success: bool
    response: str = Field(..., description="Assistant response")
    session_id: str = Field(..., description="Session ID")
    memories_used: int = Field(0, description="Number of memories used for context")
    context_preview: Optional[str] = Field(None, description="Preview of context used")
    error: Optional[str] = None


class ChatHistoryRequest(BaseModel):
    """Request model for getting chat history"""
    user_id: str = Field(..., description="User ID")
    session_id: str = Field(..., description="Session ID")
    limit: int = Field(20, description="Maximum number of messages")


class ChatHistoryResponse(BaseModel):
    """Response model for chat history"""
    success: bool
    session_id: str
    messages: List[Dict[str, Any]] = []
    total: int = 0
    error: Optional[str] = None


def get_llm_client(provider: Optional[str] = None):
    """
    Get LLM client based on available API keys and configuration.

    This function directly initializes the appropriate LLM adapter based on the provider,
    bypassing the main LLM manager which has import issues with torch.

    Args:
        provider: Optional specific provider to use. If None, uses default from config.

    Returns:
        LLM adapter instance or None if no valid provider is configured
    """
    import sys
    from pathlib import Path

    try:
        from timem.utils.config_manager import get_llm_config

        llm_config = get_llm_config()

        target_provider = provider
        if target_provider is None:
            target_provider = llm_config.get("default_provider", "mock")

        logger.info(f"Attempting to initialize LLM adapter for provider: {target_provider}")

        llm_dir = Path(__file__).parent.parent.parent / "llm"

        # Add llm directory to path and import base_llm first
        if str(llm_dir) not in sys.path:
            sys.path.insert(0, str(llm_dir))
        from base_llm import Message, MessageRole

        if target_provider == "minimax":
            from minimax_adapter import MiniMaxAdapter
            adapter = MiniMaxAdapter()
            logger.info("MiniMax adapter initialized successfully")
            return adapter
        elif target_provider == "zhipuai":
            from zhipuai_adapter import ZhipuAIAdapter
            adapter = ZhipuAIAdapter()
            logger.info("ZhipuAI adapter initialized successfully")
            return adapter
        elif target_provider == "openai":
            from openai_adapter import OpenAIAdapter
            adapter = OpenAIAdapter()
            logger.info("OpenAI adapter initialized successfully")
            return adapter
        elif target_provider == "mock":
            from mock_adapter import MockLLMAdapter
            adapter = MockLLMAdapter()
            logger.info("Mock adapter initialized successfully")
            return adapter
        else:
            logger.warning(f"Unsupported provider '{target_provider}', using mock responses")
            from mock_adapter import MockLLMAdapter
            return MockLLMAdapter()

    except ImportError as e:
        logger.error(f"Failed to import LLM modules: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Failed to initialize LLM client: {e}", exc_info=True)
        return None


def generate_mock_response(message: str, context: str) -> str:
    """Generate mock response when LLM is unavailable"""
    msg_lower = message.lower()

    if any(greet in msg_lower for greet in ["hello", "hi", "你好", "嗨", "hey"]):
        return "Hello! I'm your AI assistant powered by TiMem memory system. How can I help you today?"

    if "name" in msg_lower or "名字" in msg_lower:
        if context == "(No prior context)":
            return "I don't know your name yet. This is our first conversation! Feel free to tell me about yourself."
        return "Based on our previous conversations, I should know you. Could you remind me if I've forgotten?"

    if "remember" in msg_lower or "remembered" in msg_lower or "记住" in msg_lower:
        return "I'll remember that! TiMem's hierarchical memory ensures I can recall important information across sessions."

    if "who are you" in msg_lower or "你是谁" in msg_lower:
        return "I'm an AI assistant powered by TiMem (Temporal Memory Tree), which gives me long-term memory capabilities! I can remember and contextually reference our previous conversations."

    if "time" in msg_lower or "时间" in msg_lower:
        return f"The current time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. Is there anything specific you'd like to know about time?"

    if "help" in msg_lower or "帮助" in msg_lower:
        return "I can help you with:\n- Answering questions\n- Remembering context from our conversations\n- Providing information\n- And more! What would you like to know?"

    return f"You said: {message}\n(This is a mock response. Configure ZHIPUAI_API_KEY for real LLM responses.)"


async def search_relevant_memories(query: str, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search relevant memories for the query"""
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async
        from timem.workflows.memory_retrieval import MemoryRetrievalWorkflow

        storage_manager = await get_memory_storage_manager_async()

        if hasattr(storage_manager, 'search_memories'):
            results = await storage_manager.search_memories(
                query={
                    "query_text": query,
                    "user_id": user_id,
                    "expert_id": "chat_assistant",
                    "session_id": None,
                    "level": None
                },
                options={"limit": limit}
            )
            return results if results else []
        else:
            workflow = await MemoryRetrievalWorkflow.create(
                debug_mode=False,
                use_v2_retrievers=True
            )

            retrieval_result = await workflow.run({
                "question": query,
                "user_id": user_id,
                "expert_id": "chat_assistant",
                "limit": limit
            })

            return retrieval_result.get("retrieved_memories", [])

    except Exception as e:
        logger.error(f"Failed to search memories: {e}")
        return []


async def save_conversation_to_memory(
    messages: List[Dict[str, str]],
    user_id: str,
    character_id: str,
    session_id: str
) -> bool:
    """Save conversation to memory"""
    try:
        from services.memory_generation_service import MemoryGenerationService, MemoryGenerationRequest

        service = MemoryGenerationService()
        await service.initialize()

        content = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in messages
        ])

        memory_request = MemoryGenerationRequest(
            user_id=user_id,
            expert_id=character_id,
            session_id=session_id,
            content=content,
            timestamp=datetime.now(),
            metadata={"type": "chat_conversation"}
        )

        response = await service.generate_memory(memory_request)
        return response.success

    except Exception as e:
        logger.error(f"Failed to save conversation to memory: {e}")
        return False


def build_context_from_memories(memories: List[Dict[str, Any]]) -> str:
    """Build context string from retrieved memories"""
    if not memories:
        return "(No prior context)"

    context_parts = ["Previous relevant conversations:\n"]
    for i, mem in enumerate(memories, 1):
        content = mem.get("memory", "")
        if content:
            context_parts.append(f"{i}. {content}")

    return "\n".join(context_parts)


@router.post("/send", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a chat message and receive a response with memory integration.

    This endpoint:
    1. Searches relevant memories based on the user message
    2. Builds context from retrieved memories
    3. Generates response using LLM or mock
    4. Saves the conversation to memory (if enabled)

    Args:
        request: ChatRequest containing message, user_id, and optional parameters

    Returns:
        ChatResponse with assistant response and metadata
    """
    try:
        session_id = request.session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Chat request from user={request.user_id}, session={session_id}")

        memories = await search_relevant_memories(
            query=request.message,
            user_id=request.user_id,
            limit=request.search_limit
        )

        context = build_context_from_memories(memories)
        logger.debug(f"Context built from {len(memories)} memories")

        llm_adapter = get_llm_client(provider=request.llm_provider)
        response_text = ""

        if llm_adapter:
            try:
                # Import Message and MessageRole from the same path as get_llm_client
                import sys
                from pathlib import Path
                llm_dir = Path(__file__).parent.parent.parent / "llm"
                if str(llm_dir) not in sys.path:
                    sys.path.insert(0, str(llm_dir))
                from base_llm import Message, MessageRole

                system_prompt = f"You are a helpful assistant with access to previous conversation context. {context}"

                messages = [
                    Message(role=MessageRole.SYSTEM, content=system_prompt),
                    Message(role=MessageRole.USER, content=request.message)
                ]

                chat_response = await llm_adapter.chat(
                    messages=messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                )
                response_text = chat_response.content
                logger.info(f"LLM response generated successfully using {request.llm_provider or 'default'} provider")
            except Exception as e:
                logger.error(f"LLM call failed: {e}", exc_info=True)
                response_text = generate_mock_response(request.message, context)
        else:
            response_text = generate_mock_response(request.message, context)
            logger.info("Using mock response")

        if request.save_to_memory:
            messages = [
                {"role": "user", "content": request.message},
                {"role": "assistant", "content": response_text}
            ]
            save_success = await save_conversation_to_memory(
                messages=messages,
                user_id=request.user_id,
                character_id=request.character_id,
                session_id=session_id
            )
            logger.debug(f"Conversation saved to memory: {save_success}")

        context_preview = context[:200] + "..." if len(context) > 200 else context

        return ChatResponse(
            success=True,
            response=response_text,
            session_id=session_id,
            memories_used=len(memories),
            context_preview=context_preview if memories else None
        )

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return ChatResponse(
            success=False,
            response="抱歉，我遇到了一个问题。请稍后再试。",
            session_id=request.session_id or "unknown",
            memories_used=0,
            error=str(e)
        )


@router.post("/history", response_model=ChatHistoryResponse)
async def get_chat_history(request: ChatHistoryRequest) -> ChatHistoryResponse:
    """
    Get chat history for a session.

    Args:
        request: ChatHistoryRequest containing user_id and session_id

    Returns:
        ChatHistoryResponse with messages and metadata
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async

        storage_manager = await get_memory_storage_manager_async()

        if hasattr(storage_manager, 'get_session_messages'):
            messages = await storage_manager.get_session_messages(
                user_id=request.user_id,
                session_id=request.session_id,
                limit=request.limit
            )
            return ChatHistoryResponse(
                success=True,
                session_id=request.session_id,
                messages=messages,
                total=len(messages)
            )
        else:
            return ChatHistoryResponse(
                success=False,
                session_id=request.session_id,
                messages=[],
                total=0,
                error="Storage manager does not support get_session_messages"
            )

    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        return ChatHistoryResponse(
            success=False,
            session_id=request.session_id,
            messages=[],
            total=0,
            error=str(e)
        )


@router.get("/sessions/{user_id}", response_model=Dict[str, Any])
async def get_user_sessions(
    user_id: str,
    limit: int = Query(20, description="Maximum number of sessions", ge=1, le=100)
) -> Dict[str, Any]:
    """
    Get all sessions for a user.

    Args:
        user_id: User ID
        limit: Maximum number of sessions to return

    Returns:
        Dictionary containing sessions list
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async

        storage_manager = await get_memory_storage_manager_async()

        if hasattr(storage_manager, 'get_user_sessions'):
            sessions = await storage_manager.get_user_sessions(
                user_id=user_id,
                limit=limit
            )
            return {
                "success": True,
                "user_id": user_id,
                "sessions": sessions,
                "total": len(sessions)
            }
        else:
            return {
                "success": False,
                "user_id": user_id,
                "sessions": [],
                "total": 0,
                "error": "Storage manager does not support get_user_sessions"
            }

    except Exception as e:
        logger.error(f"Failed to get user sessions: {e}")
        return {
            "success": False,
            "user_id": user_id,
            "sessions": [],
            "total": 0,
            "error": str(e)
        }