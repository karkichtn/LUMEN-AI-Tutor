import logging
from typing import List, Dict, Any, Optional
import httpx
from fastapi import HTTPException
from backend.config import settings
from backend.models.chat import (
    ChatResponse, MessageContent, SurveyData, AssessmentData, SafetyData, FollowUpData
)
from backend.models.conversation import ConversationSession
from backend.prompts.system_prompts import MASTER_SYSTEM_PROMPT
from backend.utils.json_repair import parse_and_repair_json

logger = logging.getLogger("lumen.gemini")

class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.models = settings.CANDIDATE_MODELS

    async def generate_response(
        self,
        session: ConversationSession,
        user_message: str,
        language_preference: Optional[str] = "auto",
        user_plan: str = "free"
    ) -> ChatResponse:
        """Call Gemini with model fallback, JSON schema enforcement, and Pydantic validation."""
        if not self.api_key:
            raise HTTPException(
                status_code=500,
                detail="GEMINI_API_KEY is not configured in .env file."
            )

        # Build contents payload
        contents: List[Dict[str, Any]] = []

        # History window based on user plan
        context_turns = settings.PLUS_CONTEXT_TURNS if user_plan == "plus" else settings.FREE_CONTEXT_TURNS
        history_slice = session.history[-context_turns:] if context_turns > 0 else session.history

        # Include prior conversation history
        for turn in history_slice:
            role = "user" if turn.role == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": turn.content}]
            })

        # Augment with current user message and language guidance
        current_text = user_message.strip()
        if language_preference and language_preference != "auto":
            current_text += f"\n[User specifically requested response in: {language_preference}]"

        contents.append({
            "role": "user",
            "parts": [{"text": current_text}]
        })

        last_error = None

        for model in self.models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            payload = {
                "contents": contents,
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.35,
                    "topP": 0.95
                },
                "systemInstruction": {
                    "parts": [{"text": MASTER_SYSTEM_PROMPT}]
                }
            }

            try:
                logger.info(f"Querying Gemini model: {model}")
                async with httpx.AsyncClient(timeout=32.0) as client:
                    resp = await client.post(url, json=payload)

                    if resp.status_code == 200:
                        raw_data = resp.json()
                        candidates = raw_data.get("candidates", [])
                        if not candidates:
                            raise ValueError(f"Empty candidate list from {model}")

                        raw_text = candidates[0]["content"]["parts"][0]["text"]
                        parsed_json = parse_and_repair_json(raw_text)

                        if parsed_json:
                            # Validate and cast into Pydantic model
                            try:
                                validated = ChatResponse.model_validate(parsed_json)
                                logger.info(f"Successfully received and validated response from {model} (mode: {validated.mode})")
                                return validated
                            except Exception as val_err:
                                logger.warning(f"Pydantic validation warning from {model}: {val_err}. Safe recovery.")
                                # Safe extraction of message text
                                raw_msg = parsed_json.get("message", "")
                                if isinstance(raw_msg, dict):
                                    text_content = str(raw_msg.get("text", ""))
                                else:
                                    text_content = str(raw_msg)

                                survey_dict = parsed_json.get("survey", {})
                                if not isinstance(survey_dict, dict):
                                    survey_dict = {}

                                assessment_dict = parsed_json.get("assessment", {})
                                if not isinstance(assessment_dict, dict):
                                    assessment_dict = {}

                                safety_dict = parsed_json.get("safety", {})
                                if not isinstance(safety_dict, dict):
                                    safety_dict = {}

                                return ChatResponse(
                                    language=str(parsed_json.get("language", "en")),
                                    mode=parsed_json.get("mode", "direct_answer"),
                                    message=MessageContent(text=text_content or "Here is the response."),
                                    survey=SurveyData(**survey_dict),
                                    assessment=AssessmentData(**assessment_dict),
                                    safety=SafetyData(**safety_dict),
                                    suggestions=parsed_json.get("suggestions", []) if isinstance(parsed_json.get("suggestions"), list) else []
                                )
                        else:
                            logger.warning(f"Failed to parse JSON string from {model}: {raw_text[:200]}")
                            # Fallback if raw text wasn't JSON
                            return ChatResponse(
                                language="en",
                                mode="direct_answer",
                                message=MessageContent(text=raw_text)
                            )
                    else:
                        logger.warning(f"Model {model} returned status {resp.status_code}: {resp.text[:150]}")
                        last_error = f"HTTP {resp.status_code}: {resp.text[:100]}"
            except Exception as e:
                logger.warning(f"Exception during call to {model}: {str(e)}")
                last_error = str(e)

        # If all models failed
        logger.error(f"All Gemini models exhausted. Final error: {last_error}")
        raise HTTPException(
            status_code=502,
            detail=f"Unable to reach AI services at this moment. Details: {last_error}"
        )

gemini_service = GeminiService()
