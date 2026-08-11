import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models.labor_rule_config import LaborRuleConfig


def get_effective_labor_rules(db: Session, store_id: uuid.UUID, as_of: date) -> LaborRuleConfig:
    """
    Store-specific config wins over the global default for the same
    as_of date; within each scope, the most recent effective_from wins -
    this is what makes past ScheduleRuns auditable against the rules that
    were actually active when they were generated, even after rules change.
    """
    store_specific = (
        db.query(LaborRuleConfig)
        .filter(LaborRuleConfig.store_id == store_id, LaborRuleConfig.effective_from <= as_of)
        .order_by(LaborRuleConfig.effective_from.desc())
        .first()
    )
    if store_specific is not None:
        return store_specific

    global_default = (
        db.query(LaborRuleConfig)
        .filter(LaborRuleConfig.store_id.is_(None), LaborRuleConfig.effective_from <= as_of)
        .order_by(LaborRuleConfig.effective_from.desc())
        .first()
    )
    if global_default is None:
        raise ValueError("No labor rule configuration found - seed script should have created a global default")
    return global_default
