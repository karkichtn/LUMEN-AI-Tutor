import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.models.chat import ConversationMode

class MessageTurn(BaseModel):
    role: str  # "user" or "model"
    content: str
    timestamp: float = Field(default_factory=time.time)

class KnownContext(BaseModel):
    """Tracks known user situation parameters to prevent redundant questions."""
    topic: Optional[str] = None
    age_group: Optional[str] = None
    duration: Optional[str] = None
    severity: Optional[str] = None
    symptoms: List[str] = Field(default_factory=list)
    triggers: Optional[str] = None
    medications: Optional[str] = None
    user_level: Optional[str] = None  # e.g., "beginner", "advanced", "student"
    questions_asked_count: int = 0
    assessment_done: bool = False

class ConversationSession(BaseModel):
    conversation_id: str
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    current_mode: ConversationMode = "direct_answer"
    detected_language: str = "en"
    history: List[MessageTurn] = Field(default_factory=list)
    known_context: KnownContext = Field(default_factory=KnownContext)
