# File: integrations/email_ingest.py

import sys
import os
import sqlite3
from datetime import datetime

# Root directory ko system path mein add karna taake backend module import ho sakay
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.db import get_db_connection

def ingest_mock_email(tenant_id: int, sender: str, subject: str, body: str) -> dict:
    """
    Ek mock email database mein insert karta hai for testing.
    Ye email un-processed mani jayegi jab tak iska ticket_id_str set na ho.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Email insert kar rahe hain, is_spam aur ticket_id_str default rahenge
            cursor.execute("""
                INSERT INTO emails (tenant_id, sender, subject, body)
                VALUES (?, ?, ?, ?)
            """, (tenant_id, sender, subject, body))
            email_id = cursor.lastrowid
            conn.commit()
            
            return {
                "success": True,
                "email_id": email_id,
                "message": "Mock email ingested successfully."
            }
    except Exception as e:
        return {"success": False, "message": f"Error inserting email: {str(e)}"}

def get_unprocessed_emails(tenant_id: int) -> list:
    """
    Database se wo emails fetch karta hai jinka abhi ticket_id_str NULL hai.
    Yahan se data nikal kar hum bilkul ussi format mein map karenge jo humne state.py mein define kiya tha.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Sirf wo emails jin par processing nahi hui
            cursor.execute("""
                SELECT id, sender, subject, body, created_at 
                FROM emails 
                WHERE tenant_id = ? AND ticket_id_str IS NULL
            """, (tenant_id,))
            
            rows = cursor.fetchall()
            emails_list = []
            
            for row in rows:
                # LangGraph ke CopilotState structure ke mutabiq exact mapping
                email_data = {
                    "tenant_id": str(tenant_id),
                    "role": "user",  # Defaulting context role
                    "email_id": str(row['id']),
                    "sender": row['sender'],
                    "subject": row['subject'],
                    "body": row['body'],
                    "timestamp": row['created_at'],
                    # Baki state fields abhi empty rahenge, LangGraph agents inhein fill karenge
                    "category": "",
                    "priority": "",
                    "sentiment": "",
                    "extracted_entities": {},
                    "messages": [],
                    "next_step": ""
                }
                emails_list.append(email_data)
                
            return emails_list
    except Exception as e:
        print(f"Error fetching emails: {str(e)}")
        return []

# Agar is file ko directly run karein to operations test kar sakte hain
if __name__ == "__main__":
    print("Testing Email Ingestion Module...")
    
    # Test Tenant ID (Phase 1 mein banaya tha)
    test_tenant = 1 
    
    print("\n--- 1. Ingesting a Mock Email ---")
    sender = "angry.customer@example.com"
    subject = "Production Server is DOWN!"
    body = "Hello, our main web server went offline at 8 AM today. Please fix this immediately, we are losing sales! My order number is #99882."
    
    result = ingest_mock_email(test_tenant, sender, subject, body)
    print(result)
    
    print("\n--- 2. Fetching Unprocessed Emails for LangGraph State ---")
    unprocessed = get_unprocessed_emails(test_tenant)
    print(f"Found {len(unprocessed)} unprocessed email(s).")
    
    if unprocessed:
        print("\nReady for LangGraph State Mapping:")
        state_dict = unprocessed[0]
        for key, value in state_dict.items():
            print(f"  {key}: {value}")