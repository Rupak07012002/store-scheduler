import uuid

from jose import JWTError
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.models.user import User
from app.schemas.auth import TokenPair


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password")
    return user


def issue_token_pair(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


def refresh_access_token(db: Session, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise UnauthorizedError("Expected a refresh token")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise UnauthorizedError("Invalid refresh token") from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return issue_token_pair(user)
