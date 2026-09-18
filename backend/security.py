# File: backend/security.py

import bcrypt
import secrets

def hash_password(plain_password: str) -> str:
    """
    Plain password ko bcrypt hash mein convert karta hai.
    'gensalt' ek random string add karta hai taake hashes secure rahein.
    """
    # string ko bytes mein convert karna zaroori hai bcrypt ke liye
    password_bytes = plain_password.encode('utf-8')
    
    # Hash generate karna
    hashed_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    
    # Wapas string mein decode kar ke return karein (database mein save karne ke liye)
    return hashed_bytes.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    User ke dale gaye password ko database walay hash ke sath compare karta hai.
    Return True agar match kare, False agar wrong password ho.
    """
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    
    # bcrypt khud verify karega
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def generate_session_token() -> str:
    """
    Ek secure random token banata hai login session ke liye.
    e.g. '8f4e2a1b9c...'
    """
    # 32 bytes ka secure hex token (URL safe)
    return secrets.token_hex(32)

# Agar is file ko directly run karein to test kar sakte hain
if __name__ == "__main__":
    print("Testing Security module...")
    
    test_password = "MySuperSecretPassword123!"
    print(f"Original Password: {test_password}")
    
    # Hash the password
    hashed = hash_password(test_password)
    print(f"Hashed Password: {hashed}")
    
    # Verify correct password
    is_valid = verify_password(test_password, hashed)
    print(f"Verify Correct Password: {'Pass (True)' if is_valid else 'Fail (False)'}")
    
    # Verify wrong password
    is_valid_wrong = verify_password("WrongPassword!", hashed)
    print(f"Verify Wrong Password: {'Pass (False)' if not is_valid_wrong else 'Fail (True)'}")
    
    # Generate Token
    token = generate_session_token()
    print(f"Sample Session Token: {token}")