# File: agents/classifier.py

import os
import sys
from pydantic import BaseModel, Field
from typing import Dict, Any

# Root directory ko system path mein add karna
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# .env file load karein taake GEMINI_API_KEY mil sakay
load_dotenv()

# 1. Pydantic Schema: LLM ko is strict structure mein jawab dena hoga
class ClassificationResult(BaseModel):
    category: str = Field(description="Must be one of: Technical Support, Billing, Sales Inquiry, Spam, General")
    priority: str = Field(description="Must be one of: Critical, High, Medium, Low")
    sentiment: str = Field(description="Overall emotion of the email: Frustrated, Neutral, Satisfied, Urgent")
    extracted_entities: Dict[str, Any] = Field(description="Extract key info like order_number, company_name, dates, etc. Empty dict if none.")

def classify_email(state: dict) -> dict:
    """
    LangGraph node function. Ye email uthata hai, LLM se classify karwata hai,
    aur state ko update karne ke liye sirf naye fields return karta hai.
    """
    subject = state.get("subject", "")
    body = state.get("body", "")
    
    # 2. LLM Initialize karein (Gemini 1.5 Flash - fast and free tier friendly)
    # Ensure GEMINI_API_KEY is in your .env file
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        temperature=0.1, # Low temperature taake hallucination na ho
        max_retries=3
    )
    
    # 3. LLM ko batayen ke usay Pydantic schema follow karna hai
    structured_llm = llm.with_structured_output(ClassificationResult)
    
    # 4. Prompt Template define karein
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert IT/Operations email classifier for MailPilot.
        Analyze the incoming email and extract the category, priority, sentiment, and key entities.
        
        Priority Rules:
        - If server is down, system crashed, or urgent data loss -> Critical
        - If payment failed or login issues -> High
        - Normal queries -> Medium/Low
        """),
        ("human", "Subject: {subject}\nBody: {body}")
    ])
    
    # 5. Pipeline chain banayen (Prompt -> LLM)
    chain = prompt | structured_llm
    
    # 6. LLM ko call karein aur response lein
    try:
        print("🤖 [Classifier Node] Analyzing email with Gemini...")
        result: ClassificationResult = chain.invoke({"subject": subject, "body": body})
        
        # 7. LangGraph state update karne ke liye dictionary return karein
        return {
            "category": result.category,
            "priority": result.priority,
            "sentiment": result.sentiment,
            "extracted_entities": result.extracted_entities,
            "next_step": "ticket_generator" # Agla node decide kar diya
        }
    except Exception as e:
        print(f"❌ Error in classifier: {str(e)}")
        # Fallback mechanism agar LLM fail ho jaye
        return {
            "category": "General",
            "priority": "Medium",
            "sentiment": "Neutral",
            "extracted_entities": {},
            "next_step": "ticket_generator"
        }

# Agar is file ko directly run karein to node test kar sakte hain
if __name__ == "__main__":
    print("Testing Classifier Agent Node...")
    
    # API Key Check
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️ ERROR: GEMINI_API_KEY not found! Please create a .env file and add your key.")
        sys.exit(1)
        
    # Mock State (Email Ingestion step se li gayi hai)
    mock_state = {
        "subject": "Production Server is DOWN!",
        "body": "Hello, our main web server went offline at 8 AM today. Please fix this immediately, we are losing sales! My order number is #99882.",
        "category": "",
        "priority": "",
        "sentiment": "",
        "extracted_entities": {},
        "next_step": ""
    }
    
    print("\n--- Input State ---")
    print(f"Subject: {mock_state['subject']}")
    
    # Run Node
    updates = classify_email(mock_state)
    
    print("\n--- Output State Updates (JSON Structured) ---")
    for key, value in updates.items():
        print(f"{key}: {value}")