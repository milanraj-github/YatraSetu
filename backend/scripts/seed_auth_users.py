import os
import sys
import asyncio
import logging
from typing import List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from firebase_admin import auth as firebase_auth
from app.core.config import settings
from app.core.firebase import initialize_firebase
from app.core.security import normalize_email
from app.schemas.auth import UserRole

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("smartbus.seed")

def seed_users():
    """
    Idempotently provisions the 3 Predefined Admin accounts and 3 Predefined Driver accounts
    directly in Firebase Auth and sets Firebase Custom User Claims ({"role": "ADMIN"} / {"role": "DRIVER"}).
    """
    logger.info("Starting SMARTBUS Firebase-Only Auth Provisioning Seed Script...")
    initialize_firebase()

    target_accounts: List[Tuple[str, str, str, UserRole]] = [
        (settings.ADMIN1_EMAIL, settings.ADMIN1_PASSWORD, "Admin One", UserRole.ADMIN),
        (settings.ADMIN2_EMAIL, settings.ADMIN2_PASSWORD, "Admin Two", UserRole.ADMIN),
        (settings.ADMIN3_EMAIL, settings.ADMIN3_PASSWORD, "Admin Three", UserRole.ADMIN),
        (settings.DRIVER1_EMAIL, settings.DRIVER1_PASSWORD, "Driver One", UserRole.DRIVER),
        (settings.DRIVER2_EMAIL, settings.DRIVER2_PASSWORD, "Driver Two", UserRole.DRIVER),
        (settings.DRIVER3_EMAIL, settings.DRIVER3_PASSWORD, "Driver Three", UserRole.DRIVER),
    ]

    for raw_email, password, name, role in target_accounts:
        email = normalize_email(raw_email)
        logger.info(f"Processing seed account: {email} (Role: {role.value})")

        if settings.FIREBASE_MOCK_MODE:
            logger.info(f"  [Mock Mode] Simulated provision for {email} with role {role.value}")
            continue

        try:
            fb_user = firebase_auth.get_user_by_email(email)
            logger.info(f"  [Firebase] User already exists with UID: {fb_user.uid}")
        except firebase_auth.UserNotFoundError:
            try:
                fb_user = firebase_auth.create_user(
                    email=email,
                    password=password,
                    display_name=name,
                    email_verified=True
                )
                logger.info(f"  [Firebase] Successfully created user with UID: {fb_user.uid}")
            except Exception as e:
                logger.error(f"  [Firebase] Failed to create user {email}: {e}")
                continue
        except Exception as e:
            logger.error(f"  [Firebase] Error querying user {email}: {e}")
            continue

        # Set Custom User Claim for Role
        try:
            firebase_auth.set_custom_user_claims(fb_user.uid, {"role": role.value})
            logger.info(f"  [Firebase Claims] Successfully set custom claim role '{role.value}' for {email}")
        except Exception as e:
            logger.error(f"  [Firebase Claims] Failed to set claim for {email}: {e}")

    logger.info("SMARTBUS Seed Script completed successfully!")

if __name__ == "__main__":
    seed_users()
