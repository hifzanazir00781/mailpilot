# File: agents/chatbot_agent.py

import os
import sys
import time
from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# Root directory ko system path mein add karna
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.rag_agent import retrieve_relevant_context
from backend.db import (
    get_db_connection,
    create_new_session,
    save_message,
    get_session_messages,
    get_user_sessions
)
from agents.classifier import classify_email
from agents.ticket_generator import generate_ticket
from agents.reply_drafter import draft_reply

# Gemini API configuration via LangChain (using gemini-3.6-flash)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def get_llm():
    """
    Returns ChatGoogleGenerativeAI instance with gemini-3.6-flash.
    """
    return ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0.2
    )


def invoke_with_retry(llm, messages, max_retries=3):
    """
    Exponential backoff retry handler (2s, 4s, 8s) for 429/503/ResourceExhausted errors.
    """
    delay = 2
    for attempt in range(max_retries):
        try:
            return llm.invoke(messages)
        except Exception as e:
            err_str = str(e)
            if ("429" in err_str or "503" in err_str or "ResourceExhausted" in err_str) and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                raise e


def parse_llm_content(raw_content) -> str:
    """
    Safely extracts string content whether response.content is a string, list, or dict.
    Handles Gemini 3.6 Flash return type variations.
    """
    if isinstance(raw_content, list):
        return " ".join([item.get("text", "") if isinstance(item, dict) else str(item) for item in raw_content]).strip()
    return str(raw_content).strip()


def check_scope_guardrail(user_message: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> bool:
    """
    HYBRID SCOPE GUARDRAIL:
    1. Fast Rule-Based Filter (~70% cases, Instant, No LLM call)
       - Strong off-topic signals -> REJECT instantly
       - Strong email/support/KB signals -> ALLOW instantly
    2. LLM Fallback (~30% ambiguous cases)
       - Evaluates context and intent using Gemini 3.6 Flash
    """
    msg_lower = user_message.lower().strip()

    # --- FAST PATH 1: STRONG OFF-TOPIC SIGNALS (REJECT INSTANTLY) ---
    off_topic_keywords = [
        "movie", "film", "cinema", "actor", "actress", "song", "music", "singer",
        "joke", "story", "game", "cricket", "football", "sports", "recipe", "cook",
        "dish", "restaurant", "weather", "mausam", "president", "prime minister",
        "politics", "election", "critical problems", "country critical", "capital of",
        "who is the president", "suggest me a movie", "gana", "siyasat", "wazir-e-azam",
        "poem", "poetry", "horoscope", "astrology"
    ]
    if any(kw in msg_lower for kw in off_topic_keywords):
        return False

    # --- FAST PATH 2: STRONG IN-SCOPE SIGNALS (ALLOW INSTANTLY) ---
    in_scope_keywords = [
        "email", "mail", "inbox", "ticket", "reply", "draft", "customer",
        "refund", "policy", "return", "complaint", "support", "escalate",
        "knowledge base", "kb", "document", "sop", "workflow", "spam",
        "phishing", "priority", "classification", "banao", "draft reply",
        "angry customer", "refund policy", "iska", "usko", "wohi"
    ]
    if any(kw in msg_lower for kw in in_scope_keywords):
        return True

    # --- FALLBACK: LLM CHECK FOR AMBIGUOUS CASES ---
    return _check_scope_guardrail_llm(user_message, conversation_history)


def _check_scope_guardrail_llm(user_message: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> bool:
    """
    LLM Fallback for ambiguous scope checks. Includes recent conversation context if available.
    """
    if not GEMINI_API_KEY:
        return True

    context_str = ""
    if conversation_history:
        recent = conversation_history[-3:]
        context_str = "Recent Chat History:\n" + "\n".join(
            [f"- {m.get('role', 'user')}: {m.get('content', '')}" for m in recent]
        ) + "\n\n"

    prompt = f"""{context_str}You are a strict scope guardrail for an AI email operations platform called MailPilot.
The platform ONLY handles:
- Email reading, classification, priority tagging.
- Creating support tickets from emails or text.
- Drafting professional email replies using knowledge bases.
- Spam/phishing detection and escalation.
- Querying company knowledge bases regarding internal policies, products, and operations.

Does the following user message fall strictly within organizational email operations, support tickets, email replies, or internal knowledge base queries?
User Message: "{user_message}"

Answer ONLY with 'YES' or 'NO'. No explanation.
"""
    try:
        llm = get_llm()
        response = invoke_with_retry(llm, [HumanMessage(content=prompt)])
        answer = parse_llm_content(response.content).upper()
        return "YES" in answer
    except Exception:
        return True


def generate_decline_message(user_message: str, reason: str = "scope") -> str:
    """
    LLM se language-aware, polite decline message generate karwata hai.
    reason: 'scope' (out of scope) or 'no_info' (no reliable info)
    User ki language mein hi jawab deta hai — English, Roman Urdu, ya Urdu.
    """
    if reason == "scope":
        instruction = (
            "The user asked something OUTSIDE organizational email operations.\n"
            "Write a polite, warm decline in 2-3 sentences, in the SAME language/script the user used.\n\n"
            "Structure:\n"
            "1) Politely apologize (e.g., 'I'm sorry, I can't help with that specific request.')\n"
            "2) Briefly explain what you CAN do: assist with organizational email operations — "
            "including email classification, support ticket creation, professional reply drafting, "
            "and answering questions from the company's knowledge base.\n"
            "3) Invite the user to try an email-related task (e.g., 'If you have an email-related task, "
            "I'd be happy to help!')\n\n"
            "Tone: warm, professional, helpful. Do NOT engage with the off-topic subject. "
            "Do NOT lecture the user."
        )
    else:
        instruction = (
            "You don't have reliable information in the knowledge base to answer this question.\n"
            "Write a polite, helpful response in 2-3 sentences, in the SAME language/script the user used.\n\n"
            "Structure:\n"
            "1) Politely acknowledge you don't have reliable information (e.g., "
            "'I don't have reliable information about that in the knowledge base.')\n"
            "2) Suggest next steps: add relevant documents to the Knowledge Base, or contact the "
            "support team for manual review.\n"
            "3) Offer further help with email operations.\n\n"
            "Do NOT invent facts. Keep the tone polite and supportive."
        )

    prompt = f"""{instruction}

User message: "{user_message}"

Your reply (in the same language as user):"""

    try:
        llm = get_llm()
        response = invoke_with_retry(llm, [HumanMessage(content=prompt)])
        decline_msg = parse_llm_content(response.content)
        if decline_msg and len(decline_msg) > 10:
            return decline_msg
    except Exception:
        pass

    if reason == "scope":
        return (
            "I'm sorry, I can't help with that specific request. "
            "My purpose is to assist with organizational email operations — including email "
            "classification, support ticket creation, professional reply drafting, and answering "
            "questions from your company's knowledge base. If you have an email-related task, "
            "I'd be happy to help!"
        )
    else:
        return (
            "I don't have reliable information about that in the knowledge base. "
            "Please add relevant documents to the Knowledge Base, or contact the support team "
            "for manual review. Let me know if I can help with any email-related tasks!"
        )


def _format_history_for_langchain(conversation_history: Optional[List[Dict[str, Any]]], max_messages: int = 10) -> List:
    """
    Converts raw conversation history list into LangChain Message objects (HumanMessage / AIMessage).
    Takes up to `max_messages` (default: last 10 messages).
    """
    if not conversation_history:
        return []

    recent = conversation_history[-max_messages:]
    formatted_messages = []

    for msg in recent:
        role = msg.get("role", "user") if isinstance(msg, dict) else getattr(msg, "role", "user")
        content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")

        if not content:
            continue

        if role in ["user", "human"]:
            formatted_messages.append(HumanMessage(content=content))
        elif role in ["assistant", "bot", "system"]:
            formatted_messages.append(AIMessage(content=content))

    return formatted_messages


def process_chatbot_message(
    tenant_id: int,
    user_id: int,
    user_message: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Main chatbot handler implementing:
    1. Hybrid Scope Guardrail (Fast rule-based + LLM fallback)
    2. Context-Aware Memory (Last 10 messages passed to LLM)
    3. Intent Recognition & Execution (Ticket creation, Reply drafting, KB RAG Q&A)
    4. Hallucination Control & Language-aware polite decline
    """
    # 1. HYBRID SCOPE GUARDRAIL CHECK
    if not check_scope_guardrail(user_message, conversation_history):
        return generate_decline_message(user_message, reason="scope")

    msg_lower = user_message.lower()

    # 2. INTENT A: Ticket creation request
    if "ticket" in msg_lower and ("banao" in msg_lower or "create" in msg_lower or "generate" in msg_lower):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, sender, subject, body FROM emails WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
                (tenant_id,)
            )
            latest_email = cursor.fetchone()

        if not latest_email:
            return "Koi recent email nahi mili jiska ticket banaya jaye. Pehle email paste karein ya ingest karein."

        state = {
            "tenant_id": str(tenant_id),
            "role": "admin",
            "email_id": str(latest_email['id']),
            "sender": latest_email['sender'],
            "subject": latest_email['subject'],
            "body": latest_email['body'],
            "timestamp": "Now"
        }

        # Run classification
        res_class = classify_email(state) if callable(classify_email) else {}
        if not isinstance(res_class, dict):
            res_class = {}

        # Safely extract category & priority (supporting direct keys, nested objects, and alternate key aliases)
        category = (
            res_class.get("category")
            or res_class.get("classification", {}).get("category")
            or res_class.get("email_category")
            or "General Support"
        )
        priority = (
            res_class.get("priority")
            or res_class.get("classification", {}).get("priority")
            or res_class.get("urgency")
            or "Medium"
        )

        # Merge state with explicit top-level non-null category and priority
        merged_state = {
            **state,
            **res_class,
            "category": category,
            "priority": priority
        }

        # Generate ticket
        res_ticket = generate_ticket(merged_state)
        if not isinstance(res_ticket, dict):
            res_ticket = {}

        ticket_id = res_ticket.get("ticket_id_str") or "TICK-UNKNOWN"
        final_category = res_ticket.get("category") or category
        final_priority = res_ticket.get("priority") or priority
        summary = res_ticket.get("summary") or "Ticket generated from recent email."

        return (
            f"✅ Ticket successfully created!\n\n"
            f"- **Ticket ID:** `{ticket_id}`\n"
            f"- **Category:** {final_category}\n"
            f"- **Priority:** {final_priority}\n"
            f"- **Summary:** {summary}"
        )

    # 3. INTENT B: Reply draft request
    elif "reply" in msg_lower and ("draft" in msg_lower or "karo" in msg_lower or "banao" in msg_lower):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.subject, t.category, t.priority, e.body
                FROM tickets t
                LEFT JOIN emails e ON t.ticket_id_str = e.ticket_id_str
                WHERE t.tenant_id = ?
                ORDER BY t.id DESC LIMIT 1
            """, (tenant_id,))
            latest_ticket = cursor.fetchone()

        if not latest_ticket:
            return "Koi recent ticket nahi mili jiska reply draft kiya jaye."

        state = {
            "tenant_id": str(tenant_id),
            "subject": latest_ticket['subject'],
            "body": latest_ticket['body'] if latest_ticket['body'] else latest_ticket['subject'],
            "category": latest_ticket['category'],
            "priority": latest_ticket['priority']
        }
        res_draft = draft_reply(state)
        return (
            f"📝 **Generated Professional Reply:**\n\n{res_draft.get('draft_reply')}\n\n"
            f"*Sources Consulted:* {', '.join(res_draft.get('sources_used', []))}"
        )

    # 4. INTENT C: Knowledge Base RAG Q&A (Context-Aware)
    else:
        try:
            chunks = retrieve_relevant_context(user_message, tenant_id=int(tenant_id), top_k=3)
        except Exception:
            chunks = []

        if not chunks:
            return generate_decline_message(user_message, reason="no_info")

        context_text = "\n\n".join([f"Source: {c['source']}\n{c['content']}" for c in chunks])

        system_instruction = (
            "You are MailPilot AI, an expert email operations and knowledge base assistant.\n"
            "Answer the user's question accurately using ONLY the provided knowledge base context below.\n"
            "Use the recent conversation history to understand contextual references like 'iska', 'usko', 'wohi', 'that email', 'previous ticket', etc.\n\n"
            "CRITICAL RULES:\n"
            "- Never invent or hallucinate facts.\n"
            "- Respond in the EXACT same language/script the user used (English, Roman Urdu, or Urdu).\n"
            "- Keep your answer concise, clear, and direct."
        )

        user_prompt = f"Knowledge Base Context:\n{context_text}\n\nCurrent User Question: \"{user_message}\""

        # Build message history stack (System instruction + Last 10 conversation messages + Current query)
        messages = [SystemMessage(content=system_instruction)]
        
        # Inject up to 10 previous messages for context memory
        history_objs = _format_history_for_langchain(conversation_history, max_messages=10)
        messages.extend(history_objs)

        # Append current user prompt
        messages.append(HumanMessage(content=user_prompt))

        try:
            llm = get_llm()
            response = invoke_with_retry(llm, messages)
            answer = parse_llm_content(response.content)

            if not answer:
                return generate_decline_message(user_message, reason="no_info")
            return answer
        except Exception as e:
            return f"Error processing query: {str(e)}"