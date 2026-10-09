import uuid
import time
from typing import Dict, Optional, List, Any
from backend.models.conversation import ConversationSession, MessageTurn, KnownContext
from backend.config import settings

class ConversationManager:
    def __init__(self):
        self._sessions: Dict[str, ConversationSession] = {}

    def get_or_create(self, session_id: Optional[str] = None) -> ConversationSession:
        if not session_id or session_id not in self._sessions:
            new_id = session_id or str(uuid.uuid4())
            session = ConversationSession(conversation_id=new_id)
            self._sessions[new_id] = session
            self._cleanup_old_sessions()
            return session
        
        session = self._sessions[session_id]
        session.updated_at = time.time()
        return session

    def add_user_message(self, session_id: str, content: str):
        session = self.get_or_create(session_id)
        session.history.append(MessageTurn(role="user", content=content))
        session.updated_at = time.time()
        self._prune_history(session)

    def add_model_message(self, session_id: str, content: str, mode: str = "direct_answer"):
        session = self.get_or_create(session_id)
        session.history.append(MessageTurn(role="model", content=content))
        session.current_mode = mode
        session.updated_at = time.time()
        self._prune_history(session)

    def clear_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        return self._sessions.get(session_id)

    def _prune_history(self, session: ConversationSession):
        max_h = settings.MAX_CONVERSATION_HISTORY
        if len(session.history) > max_h:
            session.history = session.history[-max_h:]

    def _cleanup_old_sessions(self):
        max_stored = settings.MAX_STORED_SESSIONS
        if len(self._sessions) > max_stored:
            # Sort by updated_at and drop oldest 20%
            sorted_items = sorted(self._sessions.items(), key=lambda item: item[1].updated_at)
            remove_count = len(self._sessions) - max_stored + 10
            for k, _ in sorted_items[:remove_count]:
                self._sessions.pop(k, None)

conversation_manager = ConversationManager()
