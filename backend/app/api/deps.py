import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise UnauthorizedError("Expected an access token")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise UnauthorizedError() from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return user


def require_role(*allowed_roles: UserRole):
    """
    Centralizing role checks as a dependency (instead of scattering `if`
    checks through route bodies) keeps authorization auditable in one place -
    see docs/architecture.md.
    """

    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise ForbiddenError(f"Requires one of roles: {[r.value for r in allowed_roles]}")
        return user

    return _check


def require_store_scope(store_id: uuid.UUID, user: User = Depends(get_current_user)) -> User:
    """
    Owner sees all stores. A StoreManager/Employee may only act on their own
    store_id - enforced here rather than trusting the client-supplied
    store_id in the URL.
    """
    if user.role == UserRole.OWNER:
        return user
    if user.store_id != store_id:
        raise ForbiddenError("Not scoped to this store")
    return user
