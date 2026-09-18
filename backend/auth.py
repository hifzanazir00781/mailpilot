# File: backend/auth.py

import sqlite3
from backend.db import get_db_connection
from backend.security import hash_password, verify_password

def register_user(email: str, password: str, workspace_name: str, account_type: str) -> dict:
    """
    Naya account banata hai. Pehle tenant (workspace) create karta hai, phir user banata hai.
    account_type 'organization' ya 'individual' hona chahiye.
    Multi-tenant isolation yahan se start hoti hai.
    """
    if account_type not in ['organization', 'individual']:
        return {"success": False, "message": "Invalid account type. Must be organization or individual."}

    # Password ko plain text mein save nahi karna! Hash banayen.
    hashed_pw = hash_password(password)

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Tenant (Workspace) create karein
            cursor.execute(
                "INSERT INTO tenants (name, type) VALUES (?, ?)",
                (workspace_name, account_type)
            )
            tenant_id = cursor.lastrowid # Jo naya tenant bana, uska ID utha lein
            
            # 2. User create karein aur naye tenant se link karein
            cursor.execute(
                "INSERT INTO users (tenant_id, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
                (tenant_id, email, hashed_pw)
            )
            
            conn.commit()
            return {"success": True, "message": "Registration successful!", "tenant_id": tenant_id}
            
    except sqlite3.IntegrityError:
        # Agar email DB mein pehle se exist karti ho (UNIQUE constraint)
        return {"success": False, "message": "Email already exists."}
    except Exception as e:
        return {"success": False, "message": f"Error during registration: {str(e)}"}

def login_user(email: str, password: str) -> dict:
    """
    User ka email aur password check karta hai. 
    Agar credentials sahi hon, toh user aur uske tenant (workspace) ki details return karega.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # User aur uske tenant ki details SQL JOIN ke zariye nikalein
            cursor.execute("""
                SELECT u.id, u.tenant_id, u.email, u.password_hash, u.role, 
                       t.name as tenant_name, t.type as tenant_type 
                FROM users u
                JOIN tenants t ON u.tenant_id = t.id
                WHERE u.email = ?
            """, (email,))
            
            user = cursor.fetchone()
            
            # Agar user DB mein na mile
            if not user:
                return {"success": False, "message": "Invalid email or password."}
            
            # Bcrypt ke zariye password verify karein
            if not verify_password(password, user['password_hash']):
                return {"success": False, "message": "Invalid email or password."}
            
            # Login successful - sensitive data (password hash) return nahi karna
            return {
                "success": True,
                "message": "Login successful!",
                "user_data": {
                    "user_id": user['id'],
                    "tenant_id": user['tenant_id'],
                    "email": user['email'],
                    "role": user['role'],
                    "tenant_name": user['tenant_name'],
                    "tenant_type": user['tenant_type']
                }
            }
            
    except Exception as e:
        return {"success": False, "message": f"Error during login: {str(e)}"}

# Agar is file ko directly run karein to operations test kar sakte hain
if __name__ == "__main__":
    print("Testing Auth module...")
    
    # Test 1: Register Organization (e.g., Company)
    print("\n--- Test 1: Registering Organization ---")
    res_org = register_user("admin@company.com", "securepass123", "Company Inc Workspace", "organization")
    print(res_org)
    
    # Test 2: Register Individual (e.g., Personal Inbox)
    print("\n--- Test 2: Registering Individual ---")
    res_ind = register_user("me@gmail.com", "mypassword456", "My Personal Inbox", "individual")
    print(res_ind)
    
    # Test 3: Duplicate Email (This should FAIL safely)
    print("\n--- Test 3: Registering Duplicate Email ---")
    res_dup = register_user("admin@company.com", "newpass", "Another Workspace", "organization")
    print(res_dup)
    
    # Test 4: Login Success
    print("\n--- Test 4: Login Success ---")
    login_success = login_user("admin@company.com", "securepass123")
    print(login_success)
    
    # Test 5: Login Fail (Wrong Password)
    print("\n--- Test 5: Login Fail ---")
    login_fail = login_user("admin@company.com", "wrongpass")
    print(login_fail)