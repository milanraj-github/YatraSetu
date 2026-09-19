import uuid
import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.database import async_session_factory
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserCreate, validate_student_domain


# --- Schema / Domain Validation Tests ---

def test_student_valid_domain():
    """Valid student email with @sode-edu.in domain should pass."""
    user_in = UserCreate(
        firebase_uid="firebase-uid-101",
        email="student.test@sode-edu.in",
        full_name="Student Test",
        role=UserRole.STUDENT,
    )
    assert user_in.email == "student.test@sode-edu.in"
    assert user_in.role == UserRole.STUDENT


def test_student_valid_domain_case_insensitive():
    """Case-insensitive student domain should pass."""
    user_in = UserCreate(
        firebase_uid="firebase-uid-102",
        email="JOHN.DOE@SODE-EDU.IN",
        full_name="John Doe",
        role=UserRole.STUDENT,
    )
    assert user_in.role == UserRole.STUDENT


def test_student_invalid_domain_rejected():
    """Student with non-sode-edu.in domain must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            firebase_uid="firebase-uid-103",
            email="student@gmail.com",
            full_name="Invalid Student",
            role=UserRole.STUDENT,
        )
    assert "Student email must use the @sode-edu.in domain" in str(exc_info.value)


def test_student_subdomain_or_spoofed_domain_rejected():
    """Domain spoofing like sode-edu.in.example.com must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            firebase_uid="firebase-uid-104",
            email="student@sode-edu.in.example.com",
            full_name="Spoofed Student",
            role=UserRole.STUDENT,
        )
    assert "Student email must use the @sode-edu.in domain" in str(exc_info.value)


def test_non_student_roles_can_use_any_domain():
    """Admin, Driver, and Parent can use any valid email domain."""
    for role, email in [
        (UserRole.ADMIN, "admin@campus.edu"),
        (UserRole.DRIVER, "driver.bob@gmail.com"),
        (UserRole.PARENT, "parent.alice@yahoo.com"),
    ]:
        user_in = UserCreate(
            firebase_uid=f"firebase-uid-{role.value}",
            email=email,
            full_name=f"{role.value} User",
            role=role,
        )
        assert user_in.email == email
        assert user_in.role == role


# --- Database User Model & Constraints Tests ---

@pytest.mark.asyncio
async def test_create_user_in_database():
    """Test creating and reading a User entity in PostgreSQL."""
    test_uid = f"fb-uid-{uuid.uuid4().hex[:8]}"
    test_email = f"user_{uuid.uuid4().hex[:8]}@sode-edu.in"

    async with async_session_factory() as session:
        new_user = User(
            firebase_uid=test_uid,
            email=test_email,
            full_name="Database Test User",
            role=UserRole.STUDENT,
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        assert new_user.id is not None
        assert new_user.firebase_uid == test_uid
        assert new_user.email == test_email
        assert new_user.role == UserRole.STUDENT
        assert new_user.created_at is not None
        assert new_user.updated_at is not None


@pytest.mark.asyncio
async def test_user_firebase_uid_unique_constraint():
    """Test that duplicate firebase_uid violates unique constraint."""
    shared_uid = f"fb-shared-{uuid.uuid4().hex[:8]}"

    async with async_session_factory() as session:
        user1 = User(
            firebase_uid=shared_uid,
            email=f"first_{uuid.uuid4().hex[:8]}@sode-edu.in",
            full_name="First User",
            role=UserRole.STUDENT,
        )
        session.add(user1)
        await session.commit()

    async with async_session_factory() as session:
        user2 = User(
            firebase_uid=shared_uid,
            email=f"second_{uuid.uuid4().hex[:8]}@sode-edu.in",
            full_name="Second User",
            role=UserRole.STUDENT,
        )
        session.add(user2)
        with pytest.raises(IntegrityError):
            await session.commit()
