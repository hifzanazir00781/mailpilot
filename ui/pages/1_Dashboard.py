# File: ui/pages/1_Dashboard.py

import streamlit as st
import sqlite3
import os
import sys

# Root directory ko system path mein add karna taake backend import ho sakay
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from backend.db import get_db_connection

def ensure_summary_column():
    """
    Agar 'summary' column tickets table mein nahi hai, toh ye safely add kar dega.
    Ye graceful schema update kehlata hai.
    """
    with get_db_connection() as conn:
        try:
            conn.execute("ALTER TABLE tickets ADD COLUMN summary TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass # Agar column pehle se mojood hai, toh ignore karein

# DB Patch Run karein
ensure_summary_column()

# Security Check: Agar user logged in nahi hai toh rok dein
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("🔒 Please log in from the main application first.")
    st.stop()

# Context se tenant_id nikalna (Row-Level Security)
tenant_id = st.session_state.user_data['tenant_id']

def update_status(ticket_id: int, new_status: str):
    """
    Ticket ka status update kar ke page ko real-time refresh karta hai.
    """
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE tickets SET status = ? WHERE id = ? AND tenant_id = ?", 
            (new_status, ticket_id, tenant_id)
        )
        conn.commit()
    st.rerun() # UI update karne ke liye Streamlit ko reload karein

st.title("📊 Real-time Ticket Dashboard")
st.markdown("Manage your AI-generated tickets and original emails here.")

# --- FILTERS & SEARCH ---
st.markdown("### 🔎 Filters")
f_col1, f_col2, f_col3, f_col4 = st.columns(4)
search_q = f_col1.text_input("Search (Subject, ID, Sender)")
cat_filter = f_col2.selectbox("Category", ["All", "Technical Support", "Billing", "Sales Inquiry", "Spam", "General"])
pri_filter = f_col3.selectbox("Priority", ["All", "Critical", "High", "Medium", "Low"])
stat_filter = f_col4.selectbox("Status", ["All", "Pending", "In Progress", "Done"])

# --- FETCH DATA WITH ROW-LEVEL SECURITY ---
with get_db_connection() as conn:
    # SQL JOIN lagaya hai taake ticket ke sath original email bhi fetch ho
    query = """
        SELECT t.id, t.ticket_id_str, t.subject, t.category, t.priority, 
               t.status, t.summary, t.suggested_action, t.created_at, 
               e.body as email_body, e.sender
        FROM tickets t
        LEFT JOIN emails e ON t.ticket_id_str = e.ticket_id_str
        WHERE t.tenant_id = ?
    """
    params = [tenant_id]

    # Apply filters dynamically
    if search_q:
        query += " AND (t.subject LIKE ? OR e.sender LIKE ? OR t.ticket_id_str LIKE ?)"
        params.extend([f"%{search_q}%", f"%{search_q}%", f"%{search_q}%"])
    if cat_filter != "All":
        query += " AND t.category = ?"
        params.append(cat_filter)
    if pri_filter != "All":
        query += " AND t.priority = ?"
        params.append(pri_filter)
    if stat_filter != "All":
        query += " AND t.status = ?"
        params.append(stat_filter)

    query += " ORDER BY t.created_at DESC"
    
    cursor = conn.execute(query, params)
    tickets = cursor.fetchall()

# --- CUSTOM TABLE LAYOUT ---
st.markdown("---")
# Header row banayen columns use kar ke
h_cols = st.columns([1, 2.5, 1.5, 1.5, 1, 1.5])
h_cols[0].markdown("**Ticket ID**")
h_cols[1].markdown("**Subject**")
h_cols[2].markdown("**Category**")
h_cols[3].markdown("**Priority**")
h_cols[4].markdown("**Status**")
h_cols[5].markdown("**Action**")
st.markdown("---")

if not tickets:
    st.info("No tickets found matching your filters.")

# Har ticket ke liye ek custom row banayen
for t in tickets:
    with st.container(border=True): # Streamlit 1.30+ feature for clean UI
        r_cols = st.columns([1, 2.5, 1.5, 1.5, 1, 1.5])
        
        r_cols[0].write(f"`{t['ticket_id_str']}`")
        r_cols[1].write(t['subject'])
        r_cols[2].write(t['category'])
        
        # Priority Color Coding
        p = t['priority']
        color = "🔴" if p == "Critical" else "🟠" if p == "High" else "🟡" if p == "Medium" else "🟢"
        r_cols[3].markdown(f"{color} {p}")
        
        r_cols[4].write(t['status'])
        
        # Status Buttons (Real-time DB update)
        with r_cols[5]:
            if t['status'] == "Pending":
                if st.button("Start ⏳", key=f"start_{t['id']}"):
                    update_status(t['id'], "In Progress")
            elif t['status'] == "In Progress":
                if st.button("Resolve ✅", key=f"done_{t['id']}"):
                    update_status(t['id'], "Done")
            else:
                st.success("Completed")
                
        # Click to Expand Section
        with st.expander("👁️ View Details & Original Email"):
            colA, colB = st.columns(2)
            with colA:
                st.markdown("**📧 Original Sender:**")
                st.code(t['sender'])
                st.markdown("**📝 Email Body:**")
                st.info(t['email_body'])
            with colB:
                st.markdown("**🤖 AI Summary:**")
                st.write(t['summary'] if t['summary'] else "No summary available.")
                st.markdown("**✅ Suggested Action:**")
                st.success(t['suggested_action'])