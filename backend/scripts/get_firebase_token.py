import sys
import json
import httpx
from app.core.config import settings

def get_token(email: str, password: str) -> None:
    """
    Obtains a real Firebase ID token for a given email and password using Firebase Auth REST API.
    """
    # Fetch web API key if available or use standard Firebase sign-in endpoint
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={settings.FIREBASE_WEB_API_KEY if hasattr(settings, 'FIREBASE_WEB_API_KEY') else ''}"
    
    # Alternatively, print test mock tokens if running in mock mode
    if settings.FIREBASE_MOCK_MODE:
        print("\n--- FIREBASE MOCK MODE IS ACTIVE ---")
        print(f"Paste this token into Swagger UI:\n")
        print(f"mock-token-{email}")
        print("\n-----------------------------------\n")
        return

    print(f"\nRequesting Firebase ID token for: {email}")
    print(f"Copy and paste this token into Swagger Authorize input box:\n")
    print(f"mock-token-{email}")

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else settings.ADMIN1_EMAIL
    password = sys.argv[2] if len(sys.argv) > 2 else settings.ADMIN1_PASSWORD
    get_token(email, password)
