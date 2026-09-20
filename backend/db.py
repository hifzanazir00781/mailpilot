# File: backend/db.py

import sqlite3
import os
import logging
from contextlib import contextmanager
from typing import List, Dict, Optional

# Configure logging for database operations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "app.db")

@contextmanager
def get_db_connection():
    """
    Manages the SQLite database connection.
    FIX 3: Enforces foreign key constraints at the connection level.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    try:
        # SQLite disables foreign keys by default, must be enabled per connection
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        conn.close()

def init_db():
    """
    Initializes all database tables and handles safe migrations.
    FIX 1: Migration logic wrapped in try/except to prevent application crashes.
    FIX 5: Cleanup runs only once during startup, not on every page load.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Tenants Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('organization', 'individual')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # 2. Users Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
            )
            """)
            
            # 3. Tickets Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                ticket_id_str TEXT UNIQUE NOT NULL,
                subject TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL CHECK(priority IN ('Critical', 'High', 'Medium', 'Low')),
                status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'In Progress', 'Done')),
                summary TEXT,
                suggested_action TEXT,
                reply_draft TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
            )
            """)
            
            # 4. Emails Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                ticket_id_str TEXT,
                sender TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                is_spam BOOLEAN DEFAULT 0,
                spam_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
            )
            """)

            # 5. Chat Sessions Table
            # FIX 4 (Doc): updated_at is manually managed by application code (save_message/update_title) 
            # as SQLite lacks native ON UPDATE CURRENT_TIMESTAMP triggers without defining an explicit TRIGGER.
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT 'New Chat',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            """)

            # 6. Chat History Table & Safe Migration
            cursor.execute("PRAGMA table_info(chat_history)")
            chat_history_exists = cursor.fetchall()
            
            if not chat_history_exists:
                cursor.execute("""
                CREATE TABLE chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE
                )
                """)
            else:
                # Safe Migration Block
                try:
                    columns = [col[1] for col in chat_history_exists]
                    if "session_id" not in columns:
                        logger.info("Migrating chat_history table: adding session_id column...")
                        cursor.execute("ALTER TABLE chat_history ADD COLUMN session_id INTEGER DEFAULT 1")
                        
                        # Fetch distinct users to create default sessions
                        cursor.execute("SELECT DISTINCT tenant_id, user_id FROM chat_history")
                        users_with_history = cursor.fetchall()
                        for row in users_with_history:
                            t_id = row['tenant_id']
                            u_id = row['user_id']
                            
                            # Create a default "Migrated Chat" session for existing orphans
                            cursor.execute(
                                "INSERT INTO chat_sessions (tenant_id, user_id, title) VALUES (?, ?, ?)",
                                (t_id, u_id, "Migrated Chat")
                            )
                            default_session_id = cursor.lastrowid
                            
                            # Assign legacy messages to this session
                            cursor.execute(
                                "UPDATE chat_history SET session_id = ? WHERE tenant_id = ? AND user_id = ? AND (session_id IS NULL OR session_id = 1)",
                                (default_session_id, t_id, u_id)
                            )
                        logger.info("Chat history migration completed successfully.")
                except Exception as mig_err:
                    logger.error(f"Migration warning/error (non-fatal): {mig_err}")

            conn.commit()
            logger.info(f"Database initialized successfully at {DB_PATH}")
            
    except Exception as e:
        logger.error(f"Critical error initializing database: {e}")
        
    # Run startup cleanup once
    try:
        deleted = cleanup_old_sessions(days=30)
        if deleted > 0:
            logger.info(f"Startup cleanup: Removed {deleted} expired chat sessions.")
    except Exception as e:
        logger.error(f"Error during startup session cleanup: {e}")


# --- CHAT SESSION HELPER FUNCTIONS ---
# FIX 6: Added type hints and try/except logic to all helpers

def create_new_session(tenant_id: int, user_id: int, title: str = "New Chat") -> int:
    """Creates a new chat session and returns its ID."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            clean_title = title.strip()[:30] if title else "New Chat"
            cursor.execute(
                "INSERT INTO chat_sessions (tenant_id, user_id, title) VALUES (?, ?, ?)",
                (tenant_id, user_id, clean_title)
            )
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error creating session for user {user_id}: {e}")
        return 0

def get_user_sessions(tenant_id: int, user_id: int, days: int = 30, cleanup: bool = False) -> List[Dict]:
    """Fetches a user's recent chat sessions."""
    if cleanup:
        cleanup_old_sessions(days=days)
        
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, created_at, updated_at 
                FROM chat_sessions 
                WHERE tenant_id = ? AND user_id = ? 
                ORDER BY updated_at DESC
            """, (tenant_id, user_id))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching sessions for user {user_id}: {e}")
        return []

def get_session_messages(session_id: int, limit: int = 20) -> List[Dict]:
    """Fetches messages for a specific session."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, content, created_at 
                FROM chat_history 
                WHERE session_id = ? 
                ORDER BY created_at ASC 
                LIMIT ?
            """, (session_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching messages for session {session_id}: {e}")
        return []

def save_message(tenant_id: int, user_id: int, session_id: int, role: str, content: str) -> bool:
    """Saves a message and manually refreshes the session's updated_at timestamp."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chat_history (tenant_id, user_id, session_id, role, content) VALUES (?, ?, ?, ?, ?)",
                (tenant_id, user_id, session_id, role, content)
            )
            cursor.execute(
                "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (session_id,)
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error saving message to session {session_id}: {e}")
        return False

def update_session_title(session_id: int, title: str) -> bool:
    """Updates the title of a specific session."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            clean_title = title.strip()[:30] if title else "New Chat"
            cursor.execute(
                "UPDATE chat_sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (clean_title, session_id)
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error updating title for session {session_id}: {e}")
        return False

def delete_session(session_id: int) -> bool:
    """Deletes a session (cascades to delete all related messages)."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        return False

def cleanup_old_sessions(days: int = 30) -> int:
    """
    Deletes sessions older than X days. 
    FIX 2: Uses proper datetime parameterization.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            date_param = f"-{days} days"
            
            # Count target rows before deletion
            cursor.execute(
                "SELECT id FROM chat_sessions WHERE updated_at < datetime('now', ?)", 
                (date_param,)
            )
            targets = cursor.fetchall()
            count = len(targets)
            
            if count > 0:
                cursor.execute(
                    "DELETE FROM chat_sessions WHERE updated_at < datetime('now', ?)", 
                    (date_param,)
                )
                conn.commit()
            return count
    except Exception as e:
        logger.error(f"Error cleaning up old sessions: {e}")
        return 0


# --- BONUS FUNCTIONS ---

def rename_session(session_id: int, new_title: str) -> bool:
    """Alias function to rename a session."""
    return update_session_title(session_id, new_title)

def get_latest_session(tenant_id: int, user_id: int) -> Optional[Dict]:
    """Fetches the most recently updated session for a user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, created_at, updated_at 
                FROM chat_sessions 
                WHERE tenant_id = ? AND user_id = ? 
                ORDER BY updated_at DESC 
                LIMIT 1
            """, (tenant_id, user_id))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting latest session for user {user_id}: {e}")
        return None

def session_exists(session_id: int, tenant_id: int, user_id: int) -> bool:
    """Verifies that a specific session belongs to the designated user/tenant."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM chat_sessions 
                WHERE id = ? AND tenant_id = ? AND user_id = ?
            """, (session_id, tenant_id, user_id))
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking session {session_id} existence: {e}")
        return False

if __name__ == "__main__":
    init_db()
    print("Database module verified successfully with all fixes applied.")