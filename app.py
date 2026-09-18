# File: app.py

import streamlit as st
import re
import secrets
from backend.auth import register_user, login_user
from backend.security import generate_session_token

# Page Config sab se pehle aani chahiye
st.set_page_config(page_title="MailPilot AI", page_icon="📧", layout="wide")

def init_session_state():
    """
    User ka login status aur data maintain karne ke liye variables initialize karte hain.
    """
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_data' not in st.session_state:
        st.session_state.user_data = None
    if 'session_token' not in st.session_state:
        st.session_state.session_token = None

def logout():
    """
    Logout function jo session state clear kar deta hai.
    """
    st.session_state.logged_in = False
    st.session_state.user_data = None
    st.session_state.session_token = None
    st.rerun() # UI refresh karne ke liye

def validate_email(email: str, is_org: bool) -> bool:
    """
    Email format check karta hai. Agar Organization mode hai, toh personal domains block karega.
    """
    # Basic email regex
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False
    
    # Organization ke liye gmail/yahoo block karna
    personal_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
    if is_org:
        domain = email.split('@')[-1].lower()
        if domain in personal_domains:
            return False
    return True

def auth_page():
    """
    Login aur Registration tabs ka UI.
    """
    st.title("📧 MailPilot AI")
    st.markdown("### Your AI copilot for email operations")
    
    # Tabs banayein Login aur Register ke liye
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    # === LOGIN TAB ===
    with tab1:
        st.subheader("Login to your Workspace")
        with st.form("login_form"):
            log_email = st.text_input("Email")
            log_pass = st.text_input("Password", type="password")
            log_submit = st.form_submit_button("Login")
            
            if log_submit:
                if not log_email or not log_pass:
                    st.error("Please fill all fields.")
                else:
                    # backend/auth.py se login function call karein
                    res = login_user(log_email, log_pass)
                    if res["success"]:
                        st.session_state.logged_in = True
                        st.session_state.user_data = res["user_data"]
                        # Secure session token generate karein
                        st.session_state.session_token = generate_session_token()
                        st.success("Login successful! Redirecting...")
                        st.rerun() # Refresh karke dashboard pe le jaye
                    else:
                        st.error(res["message"])
                        
    # === REGISTER TAB ===
    with tab2:
        st.subheader("Create a New Account")
        # User type select karein
        account_type = st.radio("Select Account Type:", ["Organization", "Individual"])
        
        with st.form("register_form"):
            if account_type == "Organization":
                st.info("Organizations get an isolated workspace for their team.")
                workspace_name = st.text_input("Company / Organization Name")
                reg_email = st.text_input("Official Company Email (e.g., you@company.com)")
            else:
                st.info("Individuals get a private workspace for their personal inbox.")
                workspace_name = st.text_input("Your Full Name (Workspace Name)")
                reg_email = st.text_input("Personal Email (e.g., you@gmail.com)")
                
            reg_pass = st.text_input("Password", type="password")
            reg_confirm = st.text_input("Confirm Password", type="password")
            
            reg_submit = st.form_submit_button("Register")
            
            if reg_submit:
                is_org_mode = (account_type == "Organization")
                
                # Validations
                if not workspace_name or not reg_email or not reg_pass:
                    st.error("Please fill all fields.")
                elif reg_pass != reg_confirm:
                    st.error("Passwords do not match!")
                elif len(reg_pass) < 6:
                    st.error("Password must be at least 6 characters long.")
                elif not validate_email(reg_email, is_org_mode):
                    if is_org_mode:
                        st.error("Please use an official company email (not Gmail/Yahoo).")
                    else:
                        st.error("Please enter a valid email address.")
                else:
                    # Register user via backend
                    db_account_type = account_type.lower()
                    res = register_user(reg_email, reg_pass, workspace_name, db_account_type)
                    
                    if res["success"]:
                        # Simulated Email Verification Token for MVP
                        simulated_token = secrets.token_hex(16)
                        st.success(f"✅ Registration successful!")
                        st.info(f"📧 **Simulated Email Verification:** In a real app, an email would be sent. For now, here is your verification token: `{simulated_token}`")
                        st.balloons()
                    else:
                        st.error(res["message"])

def main_app():
    """
    Main application UI jo sirf logged-in users ko dikhega.
    """
    user = st.session_state.user_data
    
    # Sidebar setup
    with st.sidebar:
        st.write(f"👤 **{user['email']}**")
        
        # UI badges for account type
        if user['tenant_type'] == 'organization':
            st.success(f"🏢 Org: {user['tenant_name']}")
        else:
            st.info(f"🏠 Individual: {user['tenant_name']}")
            
        st.write(f"🔑 Role: {user['role'].capitalize()}")
        st.divider()
        
        # Navigation placeholders for upcoming phases
        st.button("📊 Dashboard (Phase 3)", disabled=True)
        st.button("🤖 Chatbot (Phase 5)", disabled=True)
        st.button("📚 Knowledge Base (Phase 4)", disabled=True)
        st.divider()
        
        if st.button("Logout"):
            logout()
            
    # Main content area
    st.title(f"Welcome to your Workspace, {user['tenant_name']}! 👋")
    st.write(f"You are logged in as a **{user['tenant_type'].capitalize()}** account.")
    st.write("Your tenant ID is:", user['tenant_id'], "(This proves data is isolated!)")
    
    st.info("Phase 1 Complete! The Dashboard and Email Ingestion will appear here in the next phases.")

# Application flow control
def main():
    init_session_state()
    
    if not st.session_state.logged_in:
        auth_page()
    else:
        main_app()

if __name__ == "__main__":
    main()