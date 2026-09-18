import os
import json
import logging
from typing import Dict, Any, Optional
import firebase_admin
from firebase_admin import credentials, auth
from app.core.config import settings

logger = logging.getLogger("smartbus.firebase")

_firebase_initialized = False

def initialize_firebase() -> None:
    global _firebase_initialized
    if _firebase_initialized or firebase_admin._apps:
        _firebase_initialized = True
        return

    if settings.FIREBASE_MOCK_MODE:
        logger.info("Firebase Admin SDK running in MOCK mode for testing.")
        _firebase_initialized = True
        return

    cred = None
    if settings.FIREBASE_SERVICE_ACCOUNT_JSON:
        try:
            service_account_info = json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
            cred = credentials.Certificate(service_account_info)
            logger.info("Firebase credentials loaded from environment JSON.")
        except Exception as e:
            logger.error(f"Failed to parse FIREBASE_SERVICE_ACCOUNT_JSON: {e}")

    if not cred and settings.FIREBASE_SERVICE_ACCOUNT_PATH:
        if os.path.exists(settings.FIREBASE_SERVICE_ACCOUNT_PATH):
            cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
            logger.info(f"Firebase credentials loaded from file: {settings.FIREBASE_SERVICE_ACCOUNT_PATH}")
        else:
            logger.warning(f"Firebase service account file not found at {settings.FIREBASE_SERVICE_ACCOUNT_PATH}")

    if cred:
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        logger.info("Firebase Admin SDK initialized successfully.")
    else:
        logger.warning("No Firebase credentials provided. Falling back to default app initialization if available.")
        try:
            firebase_admin.initialize_app()
            _firebase_initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")

# Global mock dict for testing token verification
_mock_tokens: Dict[str, Dict[str, Any]] = {}

def set_mock_firebase_token(token: str, decoded_payload: Dict[str, Any]) -> None:
    """Helper to set mock token payloads during unit tests."""
    _mock_tokens[token] = decoded_payload

def clear_mock_firebase_tokens() -> None:
    """Helper to clear mock tokens."""
    _mock_tokens.clear()

def verify_firebase_id_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies a Firebase ID token (JWT).
    Returns decoded token dictionary containing 'uid', 'email', 'email_verified', etc.
    Returns None if verification fails.
    """
    initialize_firebase()

    if settings.FIREBASE_MOCK_MODE or id_token in _mock_tokens:
        if id_token in _mock_tokens:
            return _mock_tokens[id_token]
        # Generic mock handling for tokens formatted as "mock-token-<email>"
        if id_token.startswith("mock-token-"):
            email = id_token.replace("mock-token-", "")
            return {
                "uid": f"mock_uid_{email.replace('@', '_').replace('.', '_')}",
                "email": email,
                "email_verified": True
            }

    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.error(f"Firebase ID Token verification failed: {e}")
        return None
