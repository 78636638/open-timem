"""
TiMem API Router - User Management

Provides REST API endpoints for user and character management.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class RegisterUserRequest(BaseModel):
    """Request model for registering a user"""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    email: Optional[str] = Field(None, description="Email")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class UserResponse(BaseModel):
    """Generic user response model"""
    success: bool
    user_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class UserListResponse(BaseModel):
    """User list response model"""
    total: int = 0
    users: List[Dict[str, Any]] = []
    error: Optional[str] = None


class CharacterRequest(BaseModel):
    """Request model for creating/updating a character"""
    character_id: str = Field(..., description="Character ID")
    name: str = Field(..., description="Character name")
    role: str = Field(..., description="Character role")
    style: Optional[str] = Field(None, description="Communication style")
    expertise: Optional[List[str]] = Field(None, description="Areas of expertise")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class CharacterResponse(BaseModel):
    """Character response model"""
    success: bool
    character_id: Optional[str] = None
    error: Optional[str] = None


@router.post("/register", response_model=UserResponse)
async def register_user(request: RegisterUserRequest) -> UserResponse:
    """
    Register a new user.
    
    Args:
        request: RegisterUserRequest with username, password, email
        
    Returns:
        UserResponse with user information
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async
        import uuid
        
        storage_manager = await get_memory_storage_manager_async()
        
        user_id = str(uuid.uuid4())
        
        user_data = {
            "user_id": user_id,
            "username": request.username,
            "email": request.email,
            "created_at": datetime.now().isoformat(),
            "metadata": request.metadata or {}
        }
        
        if hasattr(storage_manager.postgres_adapter, 'create_user'):
            result = await storage_manager.postgres_adapter.create_user(user_data)
            if not result.get("success"):
                return UserResponse(
                    success=False,
                    error=result.get("error", "Failed to create user")
                )
        
        return UserResponse(
            success=True,
            user_id=user_id,
            data=user_data
        )
        
    except Exception as e:
        logger.error(f"Failed to register user: {e}")
        return UserResponse(
            success=False,
            error=str(e)
        )


@router.post("/auth/login", response_model=UserResponse)
async def login(
    username: str = Query(..., description="Username"),
    password: str = Query(..., description="Password")
) -> UserResponse:
    """
    User login authentication.
    
    Args:
        username: Username
        password: Password
        
    Returns:
        UserResponse with authentication result
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async
        
        storage_manager = await get_memory_storage_manager_async()
        
        if hasattr(storage_manager.postgres_adapter, 'authenticate_user'):
            result = await storage_manager.postgres_adapter.authenticate_user(username, password)
            if result.get("success"):
                return UserResponse(
                    success=True,
                    user_id=result.get("user_id"),
                    data={
                        "username": username,
                        "token": result.get("token"),
                        "expires_at": result.get("expires_at")
                    }
                )
            else:
                return UserResponse(
                    success=False,
                    error=result.get("error", "Invalid credentials")
                )
        else:
            return UserResponse(
                success=False,
                error="Authentication not available"
            )
        
    except Exception as e:
        logger.error(f"Failed to login: {e}")
        return UserResponse(
            success=False,
            error=str(e)
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str) -> UserResponse:
    """
    Get user information.
    
    Args:
        user_id: User ID
        
    Returns:
        UserResponse with user information
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async
        
        storage_manager = await get_memory_storage_manager_async()
        
        if hasattr(storage_manager.postgres_adapter, 'get_user'):
            user = await storage_manager.postgres_adapter.get_user(user_id)
            if user:
                return UserResponse(
                    success=True,
                    user_id=user_id,
                    data=user
                )
            else:
                return UserResponse(
                    success=False,
                    error="User not found"
                )
        else:
            return UserResponse(
                success=False,
                error="User management not available"
            )
        
    except Exception as e:
        logger.error(f"Failed to get user {user_id}: {e}")
        return UserResponse(
            success=False,
            error=str(e)
        )


@router.post("/characters", response_model=CharacterResponse)
async def create_character(request: CharacterRequest) -> CharacterResponse:
    """
    Create or update a character.
    
    Args:
        request: CharacterRequest with character details
        
    Returns:
        CharacterResponse with status
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async
        
        storage_manager = await get_memory_storage_manager_async()
        
        character_data = {
            "character_id": request.character_id,
            "name": request.name,
            "role": request.role,
            "style": request.style,
            "expertise": request.expertise,
            "metadata": request.metadata or {}
        }
        
        if hasattr(storage_manager.postgres_adapter, 'create_character'):
            result = await storage_manager.postgres_adapter.create_character(character_data)
            return CharacterResponse(
                success=result.get("success", False),
                character_id=request.character_id
            )
        else:
            return CharacterResponse(
                success=True,
                character_id=request.character_id
            )
        
    except Exception as e:
        logger.error(f"Failed to create character: {e}")
        return CharacterResponse(
            success=False,
            error=str(e)
        )


@router.get("/characters/{character_id}", response_model=UserResponse)
async def get_character(character_id: str) -> UserResponse:
    """
    Get character information.
    
    Args:
        character_id: Character ID
        
    Returns:
        UserResponse with character information
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async
        
        storage_manager = await get_memory_storage_manager_async()
        
        if hasattr(storage_manager.postgres_adapter, 'get_character'):
            character = await storage_manager.postgres_adapter.get_character(character_id)
            if character:
                return UserResponse(
                    success=True,
                    data=character
                )
            else:
                return UserResponse(
                    success=False,
                    error="Character not found"
                )
        else:
            return UserResponse(
                success=True,
                data={"character_id": character_id}
            )
        
    except Exception as e:
        logger.error(f"Failed to get character {character_id}: {e}")
        return UserResponse(
            success=False,
            error=str(e)
        )


@router.delete("/characters/{character_id}", response_model=CharacterResponse)
async def delete_character(character_id: str) -> CharacterResponse:
    """
    Delete a character.
    
    Args:
        character_id: Character ID
        
    Returns:
        CharacterResponse with status
    """
    try:
        from storage.memory_storage_manager import get_memory_storage_manager_async
        
        storage_manager = await get_memory_storage_manager_async()
        
        if hasattr(storage_manager.postgres_adapter, 'delete_character'):
            result = await storage_manager.postgres_adapter.delete_character(character_id)
            return CharacterResponse(
                success=result.get("success", False),
                character_id=character_id
            )
        else:
            return CharacterResponse(
                success=True,
                character_id=character_id
            )
        
    except Exception as e:
        logger.error(f"Failed to delete character {character_id}: {e}")
        return CharacterResponse(
            success=False,
            error=str(e)
        )