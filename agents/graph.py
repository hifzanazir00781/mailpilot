# File: agents/graph.py

import os
import sys

# Root directory ko system path mein add karna taake modules import ho sakein
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.graph import StateGraph, END
from agents.state import CopilotState
from agents.classifier import classify_email
from agents.ticket_generator import generate_ticket
from agents.reply_drafter import draft_reply
from integrations.email_ingest import ingest_mock_email, get_unprocessed_emails

def build_graph():
    """
    LangGraph pipeline ko assemble karta hai.
    Nodes ko define kar ke unke darmiyan flow (edges) set karta hai.
    """
    # 1. StateGraph initialize karein CopilotState definition ke sath
    workflow = StateGraph(CopilotState)
    
    # 2. Nodes add karein (Har node ek standalone Python function hai jo humne banaya hai)
    workflow.add_node("classifier", classify_email)
    workflow.add_node("ticket_generator", generate_ticket)
    workflow.add_node("reply_drafter", draft_reply)
    
    # 3. Graph ka start point (Entry point) define karein
    workflow.set_entry_point("classifier")
    
    # 4. Edges connect karein (Classifier -> Ticket Generator -> Reply Drafter -> END)
    workflow.add_edge("classifier", "ticket_generator")
    workflow.add_edge("ticket_generator", "reply_drafter")
    workflow.add_edge("reply_drafter", END)
    
    # 5. Graph ko compile karein taake run hone ke kabil ho jaye
    app = workflow.compile()
    return app

# Ek global instance bana lein taake server run hone par baar baar compile na karna paray
copilot_graph = build_graph()

def run_email_pipeline(email_state: dict):
    """
    Ek unprocessed email state leta hai aur poore graph se guzaarta hai.
    """
    print(f"\n🚀 Starting AI pipeline for Email ID: {email_state.get('email_id')}...")
    # .invoke() automatically state ko har node se pass karta hai aur updates merge karta hai
    final_state = copilot_graph.invoke(email_state)
    return final_state

# Agar is file ko directly run karein to end-to-end pipeline test kar sakte hain
if __name__ == "__main__":
    print("Testing LangGraph Orchestration (End-to-End with RAG Reply Drafter)...")
    
    # API Key Check
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️ ERROR: GEMINI_API_KEY not found! Please create a .env file and add your key.")
        sys.exit(1)
        
    # Test Tenant ID (Phase 1)
    test_tenant = 1
    
    # --- STEP 1: Nayi email ingest karein ---
    print("\n--- Step 1: Ingesting New Test Email ---")
    sender = "finance@company.com"
    subject = "Question regarding refund policy"
    body = "Hi, I tried to request a refund for subscription #INV-7781 last week but I want to know if I am eligible and what the process is."
    
    ingest_res = ingest_mock_email(test_tenant, sender, subject, body)
    
    if not ingest_res["success"]:
        print("❌ Failed to ingest mock email.")
        sys.exit(1)
        
    print(f"✅ Mock email saved in DB with Email ID: {ingest_res['email_id']}")
    
    # --- STEP 2: DB se un-processed email fetch karein (CopilotState format mein) ---
    unprocessed = get_unprocessed_emails(test_tenant)
    
    if not unprocessed:
        print("❌ No unprocessed emails found!")
        sys.exit(1)
        
    # Hum target email uthayenge jo abhi abhi ingest ki hai (latest wali)
    target_email = unprocessed[-1] 
    
    # --- STEP 3: LangGraph Pipeline Run Karein ---
    print("\n--- Step 3: Running LangGraph Pipeline (Classifier -> Ticket -> Reply Drafter) ---")
    final_result = run_email_pipeline(target_email)
    
    print("\n🎉 --- Final Output State (End-to-End Success) --- 🎉")
    print(f"Ticket ID:        {final_result.get('ticket_id_str')}")
    print(f"Category:         {final_result.get('category')}")
    print(f"Priority:         {final_result.get('priority')}")
    print(f"Summary:          {final_result.get('summary')}")
    print(f"Suggested Action: {final_result.get('suggested_action')}")
    print(f"Entities:         {final_result.get('extracted_entities')}")
    print(f"Sources Used:     {final_result.get('sources_used')}")
    print("-----------------------------------------------------")
    print(f"Draft Reply:\n{final_result.get('draft_reply')}")
    print("-----------------------------------------------------")
    print("Pipeline orchestrated successfully!")