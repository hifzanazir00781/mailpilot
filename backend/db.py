# File: backend/db.py

import sqlite3
import os
from contextlib import contextmanager

# Hum data folder ke andar database banayenge
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "app.db")

@contextmanager
def get_db_connection():
    """
    Database connection manage karne ke liye helper function.
    Ye automatically connection close kar dega jab kaam khatam ho.
    """
    conn = sqlite3.connect(DB_PATH)
    # Return rows as dictionaries instead of tuples (data access asaan ho jata hai)
    conn.row_factory = sqlite3.Row 
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """
    Saray database tables create karega agar wo pehle se exist nahi karte.
    Har main table mein 'tenant_id' zaroori hai for data isolation.
    """
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Tenants Table: Ye organization ya individual user ka workspace define karta hai
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('organization', 'individual')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 2. Users Table: Login details yahan save hongi
        # Password hamesha hashed form mein hoga, plain text mein nahi!
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants (id)
        )
        """)
        
        # 3. Tickets Table: AI jo tickets banayega wo yahan store hongi
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            ticket_id_str TEXT UNIQUE NOT NULL, -- e.g., TKT-123456
            subject TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL CHECK(priority IN ('Critical', 'High', 'Medium', 'Low')),
            status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'In Progress', 'Done')),
            suggested_action TEXT,
            reply_draft TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants (id)
        )
        """)
        
        # 4. Emails Table: Ingested emails ka record
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
            FOREIGN KEY (tenant_id) REFERENCES tenants (id)
        )
        """)

        # 5. Chat History Table: Chatbot ki memory save karne ke liye
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)
        
        conn.commit()
        print(f"Database initialized successfully at {DB_PATH}")

# Agar is file ko directly run karein to tables create ho jayen
if __name__ == "__main__":
    init_db()