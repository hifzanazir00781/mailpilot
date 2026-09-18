# File: agents/ticket_generator.py

import os
import sys
import random
import string
from pydantic import BaseModel, Field

# Root directory ko system path mein add karna
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from backend.db import get_db_connection

load_dotenv()

# 1. Pydantic Schema: LLM se humein summary aur action chahiye
class TicketAction(BaseModel):
    summary: str = Field(description="A concise 1-2 sentence summary of the email issue.")
    suggested_action: str = Field(description="Step-by-step suggested action the team should take to resolve this.")

def generate_ticket_id() -> str:
    """
    Ek unique 6-digit ticket ID generate karta hai (e.g., TKT-492018)
    """
    digits = ''.join(random.choices(string.digits, k=6))
    return f"TKT-{digits}"

def generate_ticket(state: dict) -> dict:
    """
    LangGraph node function. Ye email aur classification uthata hai, 
    LLM se summary banwata hai, DB mein ticket save karta hai, aur state update karta hai.
    """
    subject = state.get("subject", "")
    body = state.get("body", "")
    category = state.get("category", "General")
    priority = state.get("priority", "Medium")
    tenant_id = int(state.get("tenant_id", 0))
    email_id = int(state.get("email_id", 0))

    print("🤖 [Ticket Generator Node] Analyzing issue to suggest actions...")

    # 2. LLM Initialize karein (using gemini-3.6-flash as requested)
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        temperature=0.1,
        max_retries=3
    )
    
    structured_llm = llm.with_structured_output(TicketAction)
    
    # 3. Prompt Template
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert IT/Operations Assistant for MailPilot.
        Based on the email, provide a concise summary and a clear suggested action for the support team.
        Category: {category}
        Priority: {priority}
        """),
        ("human", "Subject: {subject}\nBody: {body}")
    ])
    
    chain = prompt | structured_llm
    
    try:
        # LLM ko call kar ke smart insights lein
        result: TicketAction = chain.invoke({
            "category": category, 
            "priority": priority, 
            "subject": subject, 
            "body": body
        })
        
        ticket_id_str = generate_ticket_id()
        
        # 4. Database Operations: Ticket create karein aur Email ko link karein
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Insert new ticket
            cursor.execute("""
                INSERT INTO tickets (tenant_id, ticket_id_str, subject, category, priority, status, suggested_action)
                VALUES (?, ?, ?, ?, ?, 'Pending', ?)
            """, (tenant_id, ticket_id_str, subject, category, priority, result.suggested_action))
            
            # Update the original email to link it to this ticket
            cursor.execute("""
                UPDATE emails 
                SET ticket_id_str = ? 
                WHERE id = ?
            """, (ticket_id_str, email_id))
            
            conn.commit()
            print(f"✅ Ticket {ticket_id_str} created successfully in database!")

        # 5. State update return karein
        return {
            "ticket_id_str": ticket_id_str,
            "summary": result.summary,
            "suggested_action": result.suggested_action,
            "next_step": "reply_drafter" # Agla node decide kar diya (Phase 4)
        }
        
    except Exception as e:
        print(f"❌ Error in ticket generator: {str(e)}")
        return {
            "ticket_id_str": "ERROR",
            "summary": "Error generating summary.",
            "suggested_action": "Manual review required.",
            "next_step": "end"
        }

# Agar is file ko directly run karein to node test kar sakte hain
if __name__ == "__main__":
    print("Testing Ticket Generator Node...")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️ ERROR: GEMINI_API_KEY not found! Please create a .env file and add your key.")
        sys.exit(1)
        
    # Mock State (Classifier ke output ke baad ka state)
    mock_state = {
        "tenant_id": "1", # Assuming tenant 1 from Phase 1
        "email_id": "1",  # Assuming email 1 from our ingest script
        "subject": "Production Server is DOWN!",
        "body": "Hello, our main web server went offline at 8 AM today. Please fix this immediately, we are losing sales! My order number is #99882.",
        "category": "Technical Support",
        "priority": "Critical"
    }
    
    print("\n--- Input State ---")
    print(f"Category: {mock_state['category']} | Priority: {mock_state['priority']}")
    
    # Run Node
    updates = generate_ticket(mock_state)
    
    print("\n--- Output State Updates ---")
    for key, value in updates.items():
        print(f"{key}: {value}")