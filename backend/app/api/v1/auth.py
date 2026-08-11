from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models.user import User
from app.schemas.auth import CurrentUser, LoginRequest, RefreshRequest, TokenPair
from app.services.auth import authenticate_user, issue_token_pair, refresh_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    user = authenticate_user(db, payload.email, payload.password)
    return issue_token_pair(user)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    return refresh_access_token(db, payload.refresh_token)


@router.get("/me", response_model=CurrentUser)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
