# state.py
from typing import TypedDict, Annotated, Dict, Any
from langgraph.graph.message import add_messages

class CopilotState(TypedDict):
    """
    Represents the state of our AI Ops Copilot graph as an email moves 
    through ingestion, classification, and routing.
    """
    # 1. Tenant/Context (Bridged from Phase 1)
    tenant_id: str
    role: str
    
    # 2. Ingestion Data (The raw email)
    email_id: str
    sender: str
    subject: str
    body: str
    timestamp: str
    
    # 3. Classifier Agent Outputs (What the LLM will fill in)
    category: str              # e.g., "Technical Support", "Billing", "Sales Inquiry"
    priority: str              # e.g., "High", "Medium", "Low"
    sentiment: str             # e.g., "Frustrated", "Neutral", "Satisfied"
    extracted_entities: Dict[str, Any]  # e.g., {"order_number": "12345", "company": "Acme Corp"}
    
        # 3b. Ticket Generator Agent Outputs
    ticket_id_str: str
    summary: str
    suggested_action: str
    
    # 4. LangGraph message history (Crucial for agent memory/reasoning)
    messages: Annotated[list, add_messages]
    
    # 5. Routing logic
    next_step: str             # Determines which specialized agent handles it next