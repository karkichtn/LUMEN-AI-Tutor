from typing import List, Optional, Literal, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator

ConversationMode = Literal[
    "direct_answer",
    "educational_explanation",
    "clarification",
    "guided_assessment",
    "health_assessment",
    "emergency_triage",
    "casual_chat"
]

SafetyLevel = Literal["normal", "caution", "emergency"]

class MessageContent(BaseModel):
    text: str = Field(..., description="Main conversational or educational response")

class SurveyProgress(BaseModel):
    current: int = 1
    estimated_total: int = 4

class SurveyData(BaseModel):
    active: bool = False
    question: Optional[str] = None
    question_type: Optional[Literal["text", "choice"]] = "choice"
    options: List[str] = Field(default_factory=list, description="Clickable suggested answer choices")
    progress: Optional[SurveyProgress] = None

class AssessmentData(BaseModel):
    required: bool = False
    completed: bool = False
    summary: Optional[str] = None
    possibilities: List[str] = Field(default_factory=list, description="Non-diagnostic possibilities or factors")
    action_steps: List[str] = Field(default_factory=list, description="Practical comfort/care or educational steps")
    when_to_seek_doctor: List[str] = Field(default_factory=list, description="Red flag signs or guidance when to see a professional")
    disclaimer: Optional[str] = None

class SafetyData(BaseModel):
    level: SafetyLevel = "normal"
    urgent: bool = False
    message: Optional[str] = None

class FollowUpData(BaseModel):
    required: bool = False
    question: Optional[str] = None

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    language: Optional[str] = "auto"

class ChatResponse(BaseModel):
    language: str = "en"
    mode: ConversationMode = "direct_answer"
    message: MessageContent
    survey: SurveyData = Field(default_factory=SurveyData)
    assessment: AssessmentData = Field(default_factory=AssessmentData)
    safety: SafetyData = Field(default_factory=SafetyData)
    suggestions: List[str] = Field(default_factory=list, description="Suggested follow-up queries or quick replies")
    follow_up: FollowUpData = Field(default_factory=FollowUpData)

    @field_validator("message", mode="before")
    @classmethod
    def validate_message(cls, v):
        if isinstance(v, str):
            return MessageContent(text=v)
        elif isinstance(v, dict):
            if "text" in v:
                return MessageContent(text=str(v["text"]))
            return MessageContent(text=str(v))
        return v

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, v):
        valid = [
            "direct_answer",
            "educational_explanation",
            "clarification",
            "guided_assessment",
            "health_assessment",
            "emergency_triage",
            "casual_chat"
        ]
        if v not in valid:
            v_str = str(v).lower()
            if "emergency" in v_str:
                return "emergency_triage"
            if "health" in v_str or "assessment" in v_str:
                return "health_assessment"
            if "education" in v_str or "tutor" in v_str:
                return "educational_explanation"
            return "direct_answer"
        return v
