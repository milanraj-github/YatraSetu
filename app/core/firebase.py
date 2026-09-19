import json
import logging
import os
from typing import Any, Optional

import firebase_admin
from fastapi import HTTPException, status
from firebase_admin import auth, credentials

from app.core.config import settings

logger = logging.getLogger(__name__)

_firebase_app: Optional[firebase_admin.App] = None


def initialize_firebase_app() -> Optional[firebase_admin.App]:
    """Initialize the singleton Firebase Admin App instance."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    # Check if a default app is already initialized in firebase_admin
    try:
        _firebase_app = firebase_admin.get_app()
        return _firebase_app
    except ValueError:
        pass  # Not yet initialized

    # 1. Initialize from credentials JSON string
    if settings.FIREBASE_CREDENTIALS_JSON:
        try:
            cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
            cred = credentials.Certificate(cred_dict)
            _firebase_app = firebase_admin.initialize_app(
                cred, {"projectId": settings.FIREBASE_PROJECT_ID}
            )
            logger.info("Firebase Admin initialized from credentials JSON")
            return _firebase_app
        except Exception as exc:
            logger.error(f"Failed to initialize Firebase from JSON: {exc}")
            raise

    # 2. Initialize from credentials file path
    if settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(
        settings.FIREBASE_CREDENTIALS_PATH
    ):
        try:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            _firebase_app = firebase_admin.initialize_app(
                cred, {"projectId": settings.FIREBASE_PROJECT_ID}
            )
            logger.info(
                f"Firebase Admin initialized from file: {settings.FIREBASE_CREDENTIALS_PATH}"
            )
            return _firebase_app
        except Exception as exc:
            logger.error(f"Failed to initialize Firebase from file: {exc}")
            raise

    # 3. Initialize with Application Default Credentials or Project ID if present
    if settings.FIREBASE_PROJECT_ID:
        try:
            _firebase_app = firebase_admin.initialize_app(
                options={"projectId": settings.FIREBASE_PROJECT_ID}
            )
            logger.info(
                f"Firebase Admin initialized for project: {settings.FIREBASE_PROJECT_ID}"
            )
            return _firebase_app
        except Exception as exc:
            logger.warning(f"Could not initialize default Firebase app: {exc}")

    logger.info("Firebase Admin app not configured with credentials.")
    return None


def verify_firebase_token(id_token: str) -> dict[str, Any]:
    """Verify a Firebase ID token and return the decoded token claims.

    Raises:
        HTTPException(401): If token is missing, invalid, or expired.
        HTTPException(503): If Firebase is uninitialized or public keys cannot be reached.
    """
    if not id_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Ensure app is initialized
    app = initialize_firebase_app()
    if app is None:
        logger.error("Firebase Admin SDK is not initialized with valid credentials")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured",
        )

    try:
        decoded_token = auth.verify_id_token(id_token, app=app)
        return decoded_token
    except auth.ExpiredIdTokenError as exc:
        logger.warning(f"Firebase token expired: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except auth.RevokedIdTokenError as exc:
        logger.warning(f"Firebase token revoked: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except auth.InvalidIdTokenError as exc:
        logger.warning(f"Invalid Firebase token: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except auth.CertificateFetchError as exc:
        logger.error(f"Failed to fetch public keys for token verification: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify authentication token at this time",
        ) from exc
    except Exception as exc:
        logger.error(f"Unexpected error during Firebase token verification: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
