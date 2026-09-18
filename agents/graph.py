# File: agents/graph.py

import os
import sys

# Root directory ko system path mein add karna taake modules import ho sakein
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.graph import StateGraph, END
from agents.state import CopilotState
from agents.classifier import classify_email
from agents.ticket_generator import generate_ticket
from integrations.email_ingest import ingest_mock_email, get_unprocessed_emails

def build_graph():
    """
    LangGraph pipeline ko assemble karta hai.
    Nodes ko define kar ke unke darmiyan flow (edges) set karta hai.
    """
    # 1. StateGraph initialize karein CopilotState definition ke sath
    workflow = StateGraph(CopilotState)
    
    # 2. Nodes add karein (Har node ek standalone Python function hai jo humne pehle banaya)
    workflow.add_node("classifier", classify_email)
    workflow.add_node("ticket_generator", generate_ticket)
    
    # 3. Graph ka start point (Entry point) define karein
    workflow.set_entry_point("classifier")
    
    # 4. Edges connect karein (Classifier se nikal kar sidha Ticket Generator par jaye)
    workflow.add_edge("classifier", "ticket_generator")
    
    # 5. Ticket generator ke baad abhi graph END ho jayega 
    # (Phase 4/6 mein hum yahan reply_drafter aur escalation add karenge)
    workflow.add_edge("ticket_generator", END)
    
    # 6. Graph ko compile karein taake run hone ke kabil ho jaye
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
    print("Testing LangGraph Orchestration (End-to-End)...")
    
    # API Key Check
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️ ERROR: GEMINI_API_KEY not found! Please create a .env file and add your key.")
        sys.exit(1)
        
    # Test Tenant ID (Phase 1)
    test_tenant = 1
    
    # --- STEP 1: Nayi email ingest karein ---
    print("\n--- Step 1: Ingesting New Test Email ---")
    sender = "finance@company.com"
    subject = "Invoice payment failed for October"
    body = "Hi, I tried to pay the invoice #INV-7781 using the portal but it keeps giving me a 500 Internal Server Error. Please look into this, the payment is due today."
    
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
    print("\n--- Step 3: Running LangGraph Pipeline ---")
    # Ye target_email pehle classifier mein jayegi, phir wahan se ticket_generator mein jayegi
    final_result = run_email_pipeline(target_email)
    
    print("\n🎉 --- Final Output State (End-to-End Success) --- 🎉")
    print(f"Ticket ID:        {final_result.get('ticket_id_str')}")
    print(f"Category:         {final_result.get('category')}")
    print(f"Priority:         {final_result.get('priority')}")
    print(f"Summary:          {final_result.get('summary')}")
    print(f"Suggested Action: {final_result.get('suggested_action')}")
    print(f"Entities:         {final_result.get('extracted_entities')}")
    print("-----------------------------------------------------")
    print("Pipeline orchestrated successfully!")