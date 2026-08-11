import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.exceptions import NotFoundError
from app.db import get_db
from app.models.store import Store
from app.models.user import User, UserRole
from app.schemas.store import StoreCreate, StoreRead, StoreUpdate

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("", response_model=list[StoreRead])
def list_stores(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[Store]:
    query = db.query(Store)
    if current_user.role != UserRole.OWNER:
        query = query.filter(Store.id == current_user.store_id)
    return query.order_by(Store.name).all()


@router.get("/{store_id}", response_model=StoreRead)
def get_store(store_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Store:
    store = db.get(Store, store_id)
    if store is None:
        raise NotFoundError("Store not found")
    if current_user.role != UserRole.OWNER and current_user.store_id != store_id:
        raise NotFoundError("Store not found")
    return store


@router.post("", response_model=StoreRead, status_code=201)
def create_store(payload: StoreCreate, db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.OWNER))) -> Store:
    store = Store(**payload.model_dump())
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.patch("/{store_id}", response_model=StoreRead)
def update_store(
    store_id: uuid.UUID,
    payload: StoreUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.OWNER)),
) -> Store:
    store = db.get(Store, store_id)
    if store is None:
        raise NotFoundError("Store not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(store, field, value)
    db.commit()
    db.refresh(store)
    return store
