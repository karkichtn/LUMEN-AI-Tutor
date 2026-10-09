import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.models.chat import ChatRequest, ChatResponse
from backend.services.conversation_service import conversation_manager
from backend.services.gemini_service import gemini_service
from backend.services.db_service import db_service
from backend.routes.auth import get_current_user, get_optional_user

logger = logging.getLogger("lumen.chat")

router = APIRouter(prefix="", tags=["Chat"])

class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New chat"

class RenameConversationRequest(BaseModel):
    title: str

@router.get("/conversations")
async def list_conversations(current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    """List all saved conversations for the authenticated user, or empty for guest."""
    if not current_user:
        return {"conversations": []}
    conversations = await db_service.get_user_conversations(current_user["id"])
    return {"conversations": conversations}

@router.post("/conversations")
async def create_conversation_endpoint(
    payload: CreateConversationRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """Create a new conversation session."""
    user_id = current_user["id"] if current_user else "guest-session"
    conv = await db_service.create_conversation(user_id=user_id, title=payload.title or "New chat")
    return {"conversation": conv}

@router.get("/conversations/{conversation_id}")
async def get_conversation_endpoint(
    conversation_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """Get conversation details and full message history."""
    user_id = current_user["id"] if current_user else "guest-session"
    conv = await db_service.get_conversation(conversation_id, user_id=user_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied.")
    
    messages = await db_service.get_conversation_messages(conversation_id, user_id=user_id)
    return {
        "conversation": conv,
        "messages": messages
    }

@router.patch("/conversations/{conversation_id}")
async def rename_conversation_endpoint(
    conversation_id: str,
    payload: RenameConversationRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """Rename a conversation."""
    user_id = current_user["id"] if current_user else "guest-session"
    if not payload.title or not payload.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty.")
    
    updated = await db_service.rename_conversation(conversation_id, user_id, payload.title.strip())
    if not updated:
        raise HTTPException(status_code=404, detail="Conversation not found or unauthorized.")
    return {"success": True, "title": payload.title.strip()}

@router.delete("/conversations/{conversation_id}")
async def delete_conversation_endpoint(
    conversation_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """Delete a conversation and all its messages."""
    user_id = current_user["id"] if current_user else "guest-session"
    deleted = await db_service.delete_conversation(conversation_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found or unauthorized.")
    
    # Also clean up in-memory session if active
    conversation_manager.clear_session(conversation_id)
    return {"success": True, "message": "Conversation deleted successfully."}

@router.post("/conversations/clear")
async def clear_conversation(
    payload: dict,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    conversation_id = payload.get("conversation_id")
    if not conversation_id:
        raise HTTPException(status_code=400, detail="conversation_id is required")
    
    user_id = current_user["id"] if current_user else "guest-session"
    cleared = await db_service.delete_conversation(conversation_id, user_id)
    conversation_manager.clear_session(conversation_id)
    return {"success": True, "conversation_id": conversation_id, "cleared": cleared}

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    user_id = current_user["id"] if current_user else "guest-session"
    user_plan = current_user["plan"] if current_user else "free"

    # Enforce server-side rate limits for registered or guest users
    allowed, current_count, limit, reset_sec = await db_service.check_and_log_usage(user_id, user_plan)
    if not allowed:
        reset_min = max(1, reset_sec // 60)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit reached ({current_count}/{limit} messages). Resets in {reset_min}m. Upgrade to LUMEN Plus for unlimited messaging."
        )

    # 1. Resolve or create conversation in SQLite database
    conv_id = req.conversation_id
    conv = None

    if conv_id:
        conv = await db_service.get_conversation(conv_id, user_id=user_id)
    
    if not conv:
        # Create a new conversation with automatic title derived from prompt
        auto_title = req.message.strip().split("\n")[0][:45]
        if len(req.message.strip()) > 45:
            auto_title += "..."
        conv = await db_service.create_conversation(user_id=user_id, title=auto_title, id=conv_id)
        conv_id = conv["id"]
    else:
        # Update last activity timestamp
        await db_service.touch_conversation(conv_id, user_id)

    # 2. Get or initialize in-memory conversation session
    session = conversation_manager.get_or_create(conv_id)

    # Synchronize in-memory session history from database if memory was empty
    if not session.history:
        past_msgs = await db_service.get_conversation_messages(conv_id, user_id=user_id)
        for msg in past_msgs:
            if msg["role"] == "user":
                conversation_manager.add_user_message(conv_id, msg["content"])
            else:
                m_mode = "direct_answer"
                if msg.get("structured_data") and isinstance(msg["structured_data"], dict):
                    m_mode = msg["structured_data"].get("mode", "direct_answer")
                conversation_manager.add_model_message(conv_id, msg["content"], mode=m_mode)

    # 3. Append user message to in-memory session and persistent DB
    conversation_manager.add_user_message(conv_id, req.message)
    await db_service.add_message(
        conversation_id=conv_id,
        user_id=user_id,
        role="user",
        content=req.message
    )

    # 4. Call Gemini service
    try:
        response: ChatResponse = await gemini_service.generate_response(
            session=session,
            user_message=req.message,
            language_preference=req.language,
            user_plan=user_plan
        )
    except Exception as e:
        logger.error(f"Error generating chat response: {e}")
        raise e

    # 5. Save model response text into in-memory session and persistent DB
    conversation_manager.add_model_message(
        session_id=conv_id,
        content=response.message.text,
        mode=response.mode
    )
    await db_service.add_message(
        conversation_id=conv_id,
        user_id=user_id,
        role="assistant",
        content=response.message.text,
        structured_data=response.model_dump()
    )

    return response
