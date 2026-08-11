import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db import get_db
from app.models.shift_template import ShiftTemplate
from app.models.user import User, UserRole
from app.schemas.shift_template import ShiftTemplateCreate, ShiftTemplateRead

router = APIRouter(prefix="/shift-templates", tags=["shift-templates"])


def _assert_store_scope(user: User, store_id: uuid.UUID) -> None:
    if user.role != UserRole.OWNER and user.store_id != store_id:
        raise ForbiddenError("Not scoped to this store")


@router.get("", response_model=list[ShiftTemplateRead])
def list_shift_templates(
    store_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ShiftTemplate]:
    _assert_store_scope(current_user, store_id)
    return (
        db.query(ShiftTemplate)
        .filter(ShiftTemplate.store_id == store_id, ShiftTemplate.is_active.is_(True))
        .order_by(ShiftTemplate.start_time)
        .all()
    )


@router.post("", response_model=ShiftTemplateRead, status_code=201)
def create_shift_template(
    store_id: uuid.UUID,
    payload: ShiftTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.STORE_MANAGER)),
) -> ShiftTemplate:
    _assert_store_scope(current_user, store_id)
    template = ShiftTemplate(store_id=store_id, **payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=204)
def deactivate_shift_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.STORE_MANAGER)),
) -> None:
    template = db.get(ShiftTemplate, template_id)
    if template is None:
        raise NotFoundError("Shift template not found")
    _assert_store_scope(current_user, template.store_id)
    template.is_active = False
    db.commit()
