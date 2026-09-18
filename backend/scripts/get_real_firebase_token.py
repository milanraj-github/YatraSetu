import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from firebase_admin import auth
from app.core.config import settings
from app.core.firebase import initialize_firebase

def generate_real_token(email: str):
    """
    Generates a REAL, cryptographically signed Firebase ID token for testing with FIREBASE_MOCK_MODE=False.
    """
    initialize_firebase()
    
    try:
        user = auth.get_user_by_email(email)
        # Create custom token
        custom_token_bytes = auth.create_custom_token(user.uid)
        custom_token = custom_token_bytes.decode('utf-8') if isinstance(custom_token_bytes, bytes) else custom_token_bytes
        
        print("\n=======================================================")
        print(f"REAL FIREBASE TOKEN GENERATED FOR: {email}")
        print("=======================================================\n")
        print(custom_token)
        print("\n=======================================================")
        print("Copy the long token above and paste it into Swagger Authorize box!")
        print("=======================================================\n")
    except Exception as e:
        print(f"Error generating token for {email}: {e}")

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else settings.ADMIN1_EMAIL
    generate_real_token(email)
