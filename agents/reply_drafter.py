# File: agents/reply_drafter.py

import os
import sys
import time
from typing import Dict, Any, List

# Root directory ko system path mein add karna
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.rag_agent import retrieve_relevant_context
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

def draft_reply(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node that retrieves relevant context using RAG and drafts a professional 
    support reply using Gemini 3.6 Flash. Includes exponential backoff retry logic.
    """
    # 1. Extract necessary fields from state
    subject = state.get("subject", "")
    body = state.get("body", "")
    category = state.get("category", "General Inquiry")
    priority = state.get("priority", "Medium")
    tenant_id = state.get("tenant_id", 1)
    
    print(f"🤖 [Reply Drafter] Drafting reply for ticket: '{subject}' (Category: {category}, Priority: {priority})")
    
    # 2. Retrieve relevant context using RAG agent
    query = f"{subject} {body}"
    retrieved_chunks = retrieve_relevant_context(query, tenant_id=tenant_id, top_k=3)
    
    # Extract sources used
    sources_used = list(set([chunk["source"] for chunk in retrieved_chunks])) if retrieved_chunks else []
    
    # Format KB context for prompt
    if retrieved_chunks:
        kb_context = "\n\n".join([f"Source: {chunk['source']}\nContent: {chunk['content']}" for chunk in retrieved_chunks])
    else:
        kb_context = "No specific knowledge base context available for this query."
        
    # 3. Construct prompt template
    system_prompt = (
        "You are an expert AI customer support assistant for MailPilot AI. "
        "Your job is to draft a professional, empathetic, clear, and accurate reply to the customer's email ticket. "
        "Use the provided Knowledge Base context to answer any factual questions. If the context does not contain the answer, "
        "politely inform the customer that their request is under review by our support team.\n\n"
        "Ticket Details:\n"
        f"- Category: {category}\n"
        f"- Priority: {priority}\n\n"
        f"Knowledge Base Context:\n{kb_context}"
    )
    
    human_prompt = (
        "Customer Email Subject: {subject}\n"
        "Customer Email Body:\n{body}\n\n"
        "Draft a professional and helpful reply:"
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", human_prompt)
    ])
    
    # 4. Initialize Gemini 3.6 Flash LLM
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found!")
        return {
            "draft_reply": "Error generating reply. Manual review required.",
            "sources_used": [],
            "next_step": "end"
        }
        
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.6-flash",
            google_api_key=api_key,
            temperature=0.3
        )
        chain = prompt | llm
    except Exception as e:
        print(f"❌ Error initializing Gemini LLM: {str(e)}")
        return {
            "draft_reply": "Error generating reply. Manual review required.",
            "sources_used": [],
            "next_step": "end"
        }
        
    # 5. Invoke LLM with exponential backoff retry logic (2s, 4s, 8s)
    backoff_delays = [2, 4, 8]
    draft_text = None
    
    for attempt, delay in enumerate(backoff_delays + [0]):
        try:
            print(f"💬 [Reply Drafter] Generating draft via Gemini 3.6 Flash (Attempt {attempt + 1})...")
            response = chain.invoke({
                "subject": subject,
                "body": body
            })
            # Gemini 3.6 Flash returns a list format - extract text properly
            if isinstance(response.content, list):
                draft_text = " ".join([
                    item.get("text", "") if isinstance(item, dict) else str(item) 
                    for item in response.content
                ])
            else:
                draft_text = response.content if hasattr(response, "content") else str(response)
            break
        except Exception as e:
            error_str = str(e)
            print(f"❌ LLM generation error on attempt {attempt + 1}: {error_str}")
            if "503" in error_str or "Unavailable" in error_str or "429" in error_str or "ResourceExhausted" in error_str:
                if delay > 0:
                    print(f"⚠️ API limit/unavailable. Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print("❌ Failed to generate draft after 3 retries.")
            else:
                break
                
    if not draft_text:
        draft_text = "Error generating reply. Manual review required."
        
    print("✅ Reply successfully drafted.")
    
    # 6. Return ONLY updates (consistent with classifier and ticket_generator)
    return {
        "draft_reply": draft_text,
        "sources_used": sources_used,
        "next_step": "end"
    }


# Test Block
if __name__ == "__main__":
    print("Testing Reply Drafter Agent...")
    
    mock_state = {
        "subject": "Question regarding refund policy",
        "body": "Hi, I bought a subscription last week but I want to know if I am eligible for a refund.",
        "category": "Billing",
        "priority": "High",
        "tenant_id": 1
    }
    
    print("\n--- Mock State ---")
    for k, v in mock_state.items():
        print(f"{k}: {v}")
        
    print("\n--- Running draft_reply() ---")
    result_state = draft_reply(mock_state)
    
    print("\n--- Resulting State ---")
    print(f"Draft Reply:\n{result_state.get('draft_reply')}")
    print(f"\nSources Used: {result_state.get('sources_used')}")
    print(f"Next Step: {result_state.get('next_step')}")