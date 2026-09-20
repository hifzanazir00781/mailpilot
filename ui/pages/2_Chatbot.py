# File: ui/pages/2_Chatbot.py

import streamlit as st
import sqlite3
import os
import sys

# Root directory ko system path mein add karna taake backend/agents import ho sakay
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from backend.db import get_db_connection
from agents.chatbot_agent import process_chatbot_message

def ensure_chat_table():
    """
    Ensure the chat_history table exists in the database.
    """
    with get_db_connection() as conn:
        conn.execute("""
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

# Run table check
ensure_chat_table()

# Security Check: Agar user logged in nahi hai toh rok dein
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("🔒 Please log in from the main application first.")
    st.stop()

# Context se tenant_id aur user_id nikalna (Row-Level Security)
tenant_id = st.session_state.user_data['tenant_id']
user_id = st.session_state.user_data['user_id']

st.title("💬 MailPilot AI Copilot")
st.markdown("Your intelligent assistant for email operations, support tickets, RAG Q&A, and reply drafting.")

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown("---")
    st.subheader("🧹 Chat Controls")
    
    # New Chat Button (Clears visible session only, keeps DB history)
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
        
    # Clear Chat History Button (Deletes permanently from DB)
    if st.button("Clear Chat History", use_container_width=True):
        with get_db_connection() as conn:
            conn.execute(
                "DELETE FROM chat_history WHERE tenant_id = ? AND user_id = ?",
                (tenant_id, user_id)
            )
            conn.commit()
        st.session_state.messages = []
        st.success("Chat history cleared from database!")
        st.rerun()

def load_chat_history():
    """
    Database se last 20 messages fetch karta hai current user aur tenant ke liye.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, content 
            FROM chat_history 
            WHERE tenant_id = ? AND user_id = ? 
            ORDER BY created_at ASC 
            LIMIT 20
        """, (tenant_id, user_id))
        rows = cursor.fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in rows]

def save_message_to_db(role: str, content: str):
    """
    Ek message ko chat_history table mein save karta hai.
    """
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO chat_history (tenant_id, user_id, role, content) VALUES (?, ?, ?, ?)",
            (tenant_id, user_id, role, content)
        )
        conn.commit()

# --- INITIALIZE SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()

if "quick_prompt" not in st.session_state:
    st.session_state.quick_prompt = None

# --- CONVERSATION STARTERS / EMPTY STATE ---
if not st.session_state.messages:
    st.markdown("### 👋 Welcome to MailPilot AI Copilot!")
    st.markdown("I can help you with organizational email operations. Here's what I can do:")
    
    st.markdown("""
| Task | How to Trigger |
| :--- | :--- |
| 📧 **Classify an email** | Paste email text → I'll analyze it |
| 🎫 **Create a ticket** | Say "iska ticket banao" or "create ticket" |
| 📝 **Draft a reply** | Say "reply draft karo" or "draft reply" |
| 📚 **Query knowledge base** | Ask "What is the refund policy?" |
| 🌐 **Multi-language** | English, Roman Urdu, or Urdu — I respond in your language |
    """)
    
    st.markdown("#### 💡 Try a quick example:")
    qb_col1, qb_col2 = st.columns(2)
    if qb_col1.button("📧 What is the refund policy?", use_container_width=True):
        st.session_state.quick_prompt = "What is the refund policy?"
        st.rerun()
    if qb_col2.button("🎫 Iska ticket banao", use_container_width=True):
        st.session_state.quick_prompt = "iska ticket banao"
        st.rerun()
        
    qb_col3, qb_col4 = st.columns(2)
    if qb_col3.button("📝 Reply draft karo", use_container_width=True):
        st.session_state.quick_prompt = "reply draft karo"
        st.rerun()
    if qb_col4.button("📚 Tell me about billing policy", use_container_width=True):
        st.session_state.quick_prompt = "What is the billing policy?"
        st.rerun()
    st.markdown("---")

# --- DISPLAY CHAT HISTORY ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- INPUT HANDLING (Chat input OR Quick Prompt button) ---
user_input = st.chat_input("Ask about emails, type 'iska ticket banao', 'reply draft karo', or query KB...")

active_prompt = None
if user_input:
    active_prompt = user_input
elif st.session_state.quick_prompt:
    active_prompt = st.session_state.quick_prompt
    st.session_state.quick_prompt = None # Consume it immediately

if active_prompt:
    # 1. Display and save user message
    with st.chat_message("user"):
        st.markdown(active_prompt)
    save_message_to_db("user", active_prompt)
    st.session_state.messages.append({"role": "user", "content": active_prompt})
    
    # 2. Generate assistant response with thinking spinner
    with st.chat_message("assistant"):
        with st.spinner("🤖 Thinking..."):
            try:
                assistant_response = process_chatbot_message(tenant_id, user_id, active_prompt)
            except Exception as e:
                assistant_response = f"An error occurred while processing your request: {str(e)}"
        
        st.markdown(assistant_response)
        
    # 3. Save assistant response to DB
    save_message_to_db("assistant", assistant_response)
    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
    
    # Rerun to refresh empty state and chat view cleanly
    st.rerun()