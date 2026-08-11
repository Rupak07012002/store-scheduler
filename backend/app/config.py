from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central config. Everything here is env-driven (see .env.example) so that
    moving from on-prem Docker Compose to a managed deployment later is a
    matter of changing environment variables, not code (see docs/scaling-guide.md).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database ---
    database_url: str = "postgresql+psycopg2://scheduler:scheduler@postgres:5432/scheduler"

    # --- Auth ---
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # --- Business timezone ---
    # All 8 stores share one timezone per current business scope (confirmed
    # with owner). If a future store spans a different timezone, this
    # becomes a per-Store field instead of a global setting - see
    # docs/data-model.md for the seam.
    business_timezone: str = "America/Chicago"

    # --- Scheduling defaults (overridable per-store in DB) ---
    default_footfall_to_staff_ratio: float = 25.0  # customers/hour per staff member
    default_min_staff_floor: int = 1
    default_avg_transaction_value: float = 35.0  # USD, revenue ESTIMATE input, not real revenue

    # --- Labor rule defaults (overridable via LaborRuleConfig rows) ---
    default_max_hours_before_overtime: float = 40.0
    default_overtime_multiplier: float = 1.5
    default_min_rest_hours_between_shifts: float = 10.0
    default_required_break_minutes: int = 30
    default_max_consecutive_days: int = 6

    # --- Optimizer ---
    solver_time_limit_seconds: float = 45.0

    # --- Synthetic data seed ---
    synthetic_footfall_rows_per_store: int = 100
    synthetic_employees_per_store: int = 30
    synthetic_footfall_days: int = 34  # ~34 days x 3 shift templates ~= 100 rows/store
    seed_owner_email: str = "owner@example.com"
    seed_owner_password: str = "owner-password-change-me"
    seed_manager_password: str = "manager-password-change-me"
    seed_random_seed: int = 42


settings = Settings()
