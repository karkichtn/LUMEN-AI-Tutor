import os
import time
import uuid
import secrets
import hashlib
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from contextlib import asynccontextmanager
import aiosqlite
from backend.config import settings

logger = logging.getLogger("lumen.db")

def hash_password(password: str) -> Tuple[str, str]:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 600000)
    return key.hex(), salt

def verify_password(password: str, password_hash: str, salt: str) -> bool:
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 600000)
    return secrets.compare_digest(key.hex(), password_hash)

class DatabaseService:
    def __init__(self, db_path: str = settings.DATABASE_PATH):
        self.db_path = db_path

    @asynccontextmanager
    async def get_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("PRAGMA foreign_keys = ON;")
            yield db

    async def init_db(self):
        """Initialize SQLite database tables and indexes."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            
            # 1. Users Table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    plan TEXT NOT NULL DEFAULT 'free',
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
            """)

            # 2. Sessions Table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)

            # 3. Conversations Table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)

            # 4. Messages Table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    structured_data TEXT,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)

            # 5. Payment Requests Table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS payment_requests (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    amount INTEGER NOT NULL DEFAULT 699,
                    utr_reference TEXT NOT NULL,
                    screenshot_filename TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    admin_notes TEXT,
                    created_at REAL NOT NULL,
                    reviewed_at REAL,
                    reviewed_by TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)

            # 6. Usage Logs Table for Rate Limiting
            await db.execute("""
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)

            # Indexes for performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, updated_at DESC);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, created_at ASC);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_payments_user ON payment_requests(user_id, status);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_logs(user_id, created_at);")

            await db.commit()

            # Ensure default admin and guest accounts exist
            await self._ensure_admin_user(db)
            await db.execute("""
                INSERT OR IGNORE INTO users (id, name, email, password_hash, password_salt, plan, role, created_at, updated_at)
                VALUES ('guest-session', 'Guest User', 'guest@lumen.local', '', '', 'free', 'guest', 0, 0);
            """)
            await db.commit()
            logger.info("Database initialized successfully at %s", self.db_path)

    async def _ensure_admin_user(self, db: aiosqlite.Connection):
        cursor = await db.execute("SELECT id FROM users WHERE email = ?;", (settings.ADMIN_EMAIL,))
        admin = await cursor.fetchone()
        if not admin:
            admin_id = str(uuid.uuid4())
            pw_hash, salt = hash_password(settings.ADMIN_DEFAULT_PASSWORD)
            now = time.time()
            await db.execute("""
                INSERT INTO users (id, name, email, password_hash, password_salt, plan, role, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'plus', 'admin', ?, ?);
            """, (admin_id, "Lumen Administrator", settings.ADMIN_EMAIL, pw_hash, salt, now, now))
            await db.commit()
            logger.info("Default admin user created: %s", settings.ADMIN_EMAIL)

    # --------------------------------------------------------------------------
    # User & Auth Operations
    # --------------------------------------------------------------------------
    async def create_user(self, name: str, email: str, password: str) -> Dict[str, Any]:
        email = email.strip().lower()
        now = time.time()
        user_id = str(uuid.uuid4())
        pw_hash, salt = hash_password(password)

        async with self.get_db() as db:
            cursor = await db.execute("SELECT id FROM users WHERE email = ?;", (email,))
            if await cursor.fetchone():
                raise ValueError("An account with this email address already exists.")

            await db.execute("""
                INSERT INTO users (id, name, email, password_hash, password_salt, plan, role, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'free', 'user', ?, ?);
            """, (user_id, name.strip(), email, pw_hash, salt, now, now))
            await db.commit()

        return await self.get_user_by_id(user_id)

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        email = email.strip().lower()
        async with self.get_db() as db:
            cursor = await db.execute("""
                SELECT id, name, email, password_hash, password_salt, plan, role, created_at, updated_at
                FROM users WHERE email = ?;
            """, (email,))
            row = await cursor.fetchone()
            if not row:
                return None

            if not verify_password(password, row["password_hash"], row["password_salt"]):
                return None

            return {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "plan": row["plan"],
                "role": row["role"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        async with self.get_db() as db:
            cursor = await db.execute("""
                SELECT id, name, email, plan, role, created_at, updated_at
                FROM users WHERE id = ?;
            """, (user_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            return dict(row)

    async def update_user_profile(self, user_id: str, name: Optional[str] = None, password: Optional[str] = None):
        async with self.get_db() as db:
            now = time.time()
            if name and password:
                pw_hash, salt = hash_password(password)
                await db.execute("""
                    UPDATE users SET name = ?, password_hash = ?, password_salt = ?, updated_at = ? WHERE id = ?;
                """, (name.strip(), pw_hash, salt, now, user_id))
            elif name:
                await db.execute("""
                    UPDATE users SET name = ?, updated_at = ? WHERE id = ?;
                """, (name.strip(), now, user_id))
            elif password:
                pw_hash, salt = hash_password(password)
                await db.execute("""
                    UPDATE users SET password_hash = ?, password_salt = ?, updated_at = ? WHERE id = ?;
                """, (pw_hash, salt, now, user_id))
            await db.commit()

    async def set_user_plan(self, user_id: str, plan: str):
        async with self.get_db() as db:
            now = time.time()
            await db.execute("UPDATE users SET plan = ?, updated_at = ? WHERE id = ?;", (plan, now, user_id))
            await db.commit()

    # --------------------------------------------------------------------------
    # Session Operations
    # --------------------------------------------------------------------------
    async def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        now = time.time()
        expires_at = now + settings.SESSION_TTL_SECONDS

        async with self.get_db() as db:
            await db.execute("""
                INSERT INTO sessions (token, user_id, expires_at, created_at)
                VALUES (?, ?, ?, ?);
            """, (token, user_id, expires_at, now))
            await db.commit()
        return token

    async def get_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        now = time.time()
        async with self.get_db() as db:
            cursor = await db.execute("""
                SELECT s.expires_at, u.id, u.name, u.email, u.plan, u.role, u.created_at, u.updated_at
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.token = ?;
            """, (token,))
            row = await cursor.fetchone()
            if not row:
                return None

            if row["expires_at"] < now:
                # Expired session cleanup
                await db.execute("DELETE FROM sessions WHERE token = ?;", (token,))
                await db.commit()
                return None

            return {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "plan": row["plan"],
                "role": row["role"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }

    async def delete_session(self, token: str):
        async with self.get_db() as db:
            await db.execute("DELETE FROM sessions WHERE token = ?;", (token,))
            await db.commit()

    # --------------------------------------------------------------------------
    # Conversation Operations
    # --------------------------------------------------------------------------
    async def create_conversation(
        self,
        user_id: str,
        title: str = "New conversation",
        id: Optional[str] = None
    ) -> Dict[str, Any]:
        conv_id = id or str(uuid.uuid4())
        now = time.time()
        async with self.get_db() as db:
            await db.execute("""
                INSERT INTO conversations (id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?);
            """, (conv_id, user_id, title, now, now))
            await db.commit()
        return {"id": conv_id, "user_id": user_id, "title": title, "created_at": now, "updated_at": now}

    async def get_user_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        async with self.get_db() as db:
            cursor = await db.execute("""
                SELECT id, title, created_at, updated_at
                FROM conversations
                WHERE user_id = ?
                ORDER BY updated_at DESC;
            """, (user_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_conversation(self, conversation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        async with self.get_db() as db:
            cursor = await db.execute("""
                SELECT id, user_id, title, created_at, updated_at
                FROM conversations
                WHERE id = ? AND user_id = ?;
            """, (conversation_id, user_id))
            row = await cursor.fetchone()
            if not row:
                return None
            return dict(row)

    async def rename_conversation(self, conversation_id: str, user_id: str, new_title: str) -> bool:
        new_title = new_title.strip()[:100] or "Untitled conversation"
        now = time.time()
        async with self.get_db() as db:
            cursor = await db.execute("""
                UPDATE conversations
                SET title = ?, updated_at = ?
                WHERE id = ? AND user_id = ?;
            """, (new_title, now, conversation_id, user_id))
            await db.commit()
            return cursor.rowcount > 0

    async def touch_conversation(self, conversation_id: str, user_id: str, title: Optional[str] = None):
        now = time.time()
        async with self.get_db() as db:
            if title:
                await db.execute("""
                    UPDATE conversations
                    SET title = ?, updated_at = ?
                    WHERE id = ? AND user_id = ?;
                """, (title.strip()[:100], now, conversation_id, user_id))
            else:
                await db.execute("""
                    UPDATE conversations
                    SET updated_at = ?
                    WHERE id = ? AND user_id = ?;
                """, (now, conversation_id, user_id))
            await db.commit()

    async def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        async with self.get_db() as db:
            cursor = await db.execute("""
                DELETE FROM conversations WHERE id = ? AND user_id = ?;
            """, (conversation_id, user_id))
            await db.commit()
            return cursor.rowcount > 0

    # --------------------------------------------------------------------------
    # Message Operations
    # --------------------------------------------------------------------------
    async def add_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        structured_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        msg_id = str(uuid.uuid4())
        now = time.time()
        json_str = json.dumps(structured_data) if structured_data else None

        async with self.get_db() as db:
            await db.execute("""
                INSERT INTO messages (id, conversation_id, user_id, role, content, structured_data, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (msg_id, conversation_id, user_id, role, content, json_str, now))
            await db.commit()

        return {
            "id": msg_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "structured_data": structured_data,
            "created_at": now
        }

    async def get_conversation_messages(self, conversation_id: str, user_id: str) -> List[Dict[str, Any]]:
        async with self.get_db() as db:
            cursor = await db.execute("""
                SELECT id, conversation_id, role, content, structured_data, created_at
                FROM messages
                WHERE conversation_id = ? AND user_id = ?
                ORDER BY created_at ASC;
            """, (conversation_id, user_id))
            rows = await cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                if item.get("structured_data"):
                    try:
                        item["structured_data"] = json.loads(item["structured_data"])
                    except Exception:
                        pass
                results.append(item)
            return results

    # --------------------------------------------------------------------------
    # Rate Limiting & Usage Tracking
    # --------------------------------------------------------------------------
    async def check_and_log_usage(self, user_id: str, plan: str) -> Tuple[bool, int, int, int]:
        """
        Check rate limits. Returns (allowed, current_count, limit, reset_seconds).
        Plus users have unlimited messages.
        """
        if plan == "plus":
            return True, 0, 999999, 0

        now = time.time()
        window_start = now - (settings.FREE_WINDOW_HOURS * 3600)

        async with self.get_db() as db:
            # Clean old records occasionally
            await db.execute("DELETE FROM usage_logs WHERE created_at < ?;", (window_start - 3600,))
            
            # Count recent requests
            cursor = await db.execute("""
                SELECT COUNT(*) as count, MIN(created_at) as oldest
                FROM usage_logs
                WHERE user_id = ? AND created_at >= ?;
            """, (user_id, window_start))
            row = await cursor.fetchone()
            count = row["count"] if row else 0

            limit = settings.FREE_MESSAGE_LIMIT
            if count >= limit:
                oldest = row["oldest"] or now
                reset_sec = max(1, int((oldest + settings.FREE_WINDOW_HOURS * 3600) - now))
                return False, count, limit, reset_sec

            # Log this turn
            await db.execute("INSERT INTO usage_logs (user_id, created_at) VALUES (?, ?);", (user_id, now))
            await db.commit()
            return True, count + 1, limit, 0

    # --------------------------------------------------------------------------
    # Payment & Entitlement Operations
    # --------------------------------------------------------------------------
    async def create_payment_request(
        self,
        user_id: str,
        utr_reference: str,
        screenshot_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        req_id = str(uuid.uuid4())
        now = time.time()
        utr_clean = utr_reference.strip()

        async with self.get_db() as db:
            # Check if pending request already exists with this UTR
            cursor = await db.execute("""
                SELECT id FROM payment_requests WHERE utr_reference = ? AND status = 'pending';
            """, (utr_clean,))
            if await cursor.fetchone():
                raise ValueError("A payment verification request with this UTR is already pending review.")

            await db.execute("""
                INSERT INTO payment_requests (id, user_id, amount, utr_reference, screenshot_filename, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?);
            """, (req_id, user_id, settings.PLUS_PRICE_INR, utr_clean, screenshot_filename, now))
            await db.commit()

        return await self.get_payment_request_by_id(req_id)

    async def get_payment_request_by_id(self, req_id: str) -> Optional[Dict[str, Any]]:
        async with self.get_db() as db:
            cursor = await db.execute("""
                SELECT p.*, u.name as user_name, u.email as user_email
                FROM payment_requests p
                JOIN users u ON p.user_id = u.id
                WHERE p.id = ?;
            """, (req_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            return dict(row)

    async def get_user_payment_requests(self, user_id: str) -> List[Dict[str, Any]]:
        async with self.get_db() as db:
            cursor = await db.execute("""
                SELECT id, amount, utr_reference, screenshot_filename, status, admin_notes, created_at, reviewed_at
                FROM payment_requests
                WHERE user_id = ?
                ORDER BY created_at DESC;
            """, (user_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_all_payment_requests(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        async with self.get_db() as db:
            query = """
                SELECT p.*, u.name as user_name, u.email as user_email
                FROM payment_requests p
                JOIN users u ON p.user_id = u.id
            """
            params = []
            if status:
                query += " WHERE p.status = ?"
                params.append(status)
            query += " ORDER BY p.created_at DESC;"

            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def review_payment_request(
        self,
        request_id: str,
        admin_user_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        status = status.lower()
        if status not in ["approved", "rejected"]:
            raise ValueError("Status must be 'approved' or 'rejected'.")

        now = time.time()
        async with self.get_db() as db:
            cursor = await db.execute("SELECT id, user_id, status FROM payment_requests WHERE id = ?;", (request_id,))
            req = await cursor.fetchone()
            if not req:
                raise ValueError("Payment request not found.")

            target_user_id = req["user_id"]

            await db.execute("""
                UPDATE payment_requests
                SET status = ?, admin_notes = ?, reviewed_at = ?, reviewed_by = ?
                WHERE id = ?;
            """, (status, notes, now, admin_user_id, request_id))

            # If approved, grant permanent Plus entitlement
            if status == "approved":
                await db.execute("""
                    UPDATE users SET plan = 'plus', updated_at = ? WHERE id = ?;
                """, (now, target_user_id))

            await db.commit()

        return await self.get_payment_request_by_id(request_id)

db_service = DatabaseService()
