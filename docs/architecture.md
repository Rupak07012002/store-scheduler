# Architecture

## The problem this system solves

You have 8 stores, roughly 30 employees each, and customer traffic that varies by day of week, time of day, and season. Scheduling by hand means either guessing at staffing levels (usually erring toward overstaffing "just in case," which quietly eats margin) or under-staffing busy periods (which costs sales and burns out the staff who are on shift). This system replaces the guessing with:

1. A forecast of expected customer footfall, learned from your own store's history.
2. A translation of that forecast into "how many people do we need, when."
3. A solver that assigns actual employees to actual shifts to meet that requirement, while respecting labor law and each employee's availability - and does so while scheduling as few total hours as possible (not padding shifts beyond what's needed).
4. A human review step, because no algorithm should silently publish a schedule that pays your staff.

## The end-to-end pipeline

```mermaid
flowchart LR
    A[POS transactions\n(Shopify, or synthetic seed data)] --> B[FootfallRecord table]
    B --> C[Seasonal-baseline forecaster]
    C --> D[Labor requirement translation\n(footfall-to-staff ratio)]
    D --> E[CP-SAT optimizer]
    E --> F[Draft ScheduleRun +\nShiftAssignments]
    F --> G[Compliance check\n(overtime, rest, coverage)]
    G --> H{Manager review}
    H -->|edits| G
    H -->|publish| I[Published schedule]
    I --> J[Employee self-service\n(view, swap, availability, time off)]
    J -->|swap approved| G
```

Each stage reads and writes specific tables - see [data-model.md](data-model.md) for the full schema and [forecasting-and-optimization.md](forecasting-and-optimization.md) for how stages 2-4 actually work.

1. **Ingestion** - synthetic data today (`scripts/seed_synthetic_data.py`); a scheduled Shopify sync job later (same target table, see [scaling-guide.md](scaling-guide.md)).
2. **Forecast** - a transparent seasonal-average model predicts footfall per store/day/shift.
3. **Labor requirement translation** - an owner-tunable ratio converts predicted footfall into a required headcount per shift.
4. **Optimization** - Google OR-Tools' CP-SAT solver assigns real employees to shifts to meet that requirement at minimum total scheduled hours, respecting availability and labor rules.
5. **Compliance check** - automatically flags anything that would violate overtime, rest, or coverage rules, before a human can publish it.
6. **Review & publish** - a manager can edit the draft; publishing is blocked while any hard compliance flag is open.
7. **Employee self-service & swaps** - employees only ever see published schedules; shift swaps go through the same compliance check before being approved.

## Why each component exists

### Backend: FastAPI (Python)

The forecaster and optimizer are numerical/algorithmic code (pandas, OR-Tools) - writing the API in the same language avoids a network hop or serialization boundary between "the API" and "the AI," and keeps one deployable artifact. FastAPI specifically gives request/response validation via Pydantic for free, which matters when the frontend and backend are maintained somewhat independently.

### Database: PostgreSQL (self-hosted via Docker)

The data here is fundamentally relational (employees belong to stores, assignments belong to schedule runs, swaps reference two assignments) with real foreign-key integrity needs - a document store would just push that integrity checking into application code. Postgres also has a JSONB column type, used once (`ScheduleRun.forecast_snapshot`) to store a point-in-time forecast without needing a separate table. Self-hosting via Docker is the direct consequence of the on-premise-first requirement; the same Postgres, unmodified, is what a managed cloud database (RDS, Cloud SQL) would run - moving later is a connection-string change, not a rewrite.

### Frontend: React + TypeScript + Vite + Tailwind

Two genuinely different user experiences live in one app (a data-dense manager dashboard with tables and forms, and a simple employee self-service portal) - a component-based UI library earns its keep here more than for a single static page. TypeScript catches a mismatched field name against the backend's Pydantic schemas at compile time instead of as a runtime bug. Tailwind avoids introducing a second design-system dependency for what's currently a fairly small set of screens.

### Auth: JWT with access + refresh tokens, role-based dependencies

Three distinct audiences (Owner, Store Manager, Employee) need different visibility into the same data - most visibly, an Employee must never see a draft schedule, only a published one. Centralizing that as a `require_role(...)` FastAPI dependency (see `app/api/deps.py`) means every route's authorization is visible in its signature, not buried in an `if` statement three lines into the function body. Refresh tokens exist because employees are expected to stay logged into a personal device far longer than a manager sitting at a dashboard.

### Optimizer: Google OR-Tools (CP-SAT)

This is a real constraint-satisfaction problem (cover demand, respect availability, respect labor law, minimize hours) with roughly 30 employees x 7 days x 3 shift templates = ~630 decision variables per store - small enough that a general-purpose constraint solver finds a provably optimal (or near-optimal) answer in well under a second, without hand-writing a greedy heuristic that might silently produce a worse-than-necessary schedule. See [forecasting-and-optimization.md](forecasting-and-optimization.md) for the full model.

### Forecasting: a hand-written seasonal-baseline model, not a machine-learning library

With only weeks-to-months of real history available (confirmed with the store owner), a model that needs a year+ of data to be reliable (Prophet, gradient boosting) would either be undertrained or would require faking confidence it doesn't have. A day-of-week/shift-block average, blended with a recent-trend adjustment, is honest about what it knows, and - just as importantly - is explainable: an owner can ask "why does it think Saturday afternoon needs 2 people" and get a plain answer ("that's what recent Saturday afternoons have averaged"), not a shrug at a black box. The upgrade path to a real ML model, once 12+ months of real data exist, is documented in [scaling-guide.md](scaling-guide.md) and requires no changes outside `app/services/forecasting/`.

### Background jobs: APScheduler running in-process

One weekly job ("generate next week's draft schedules") across 8 stores does not need a message broker, a worker pool, or retry infrastructure - that's solving a problem this system doesn't have yet. APScheduler runs the job on a cron-like schedule inside the same process as the API, with zero extra services to operate. The job body (`app/jobs/tasks.py::generate_weekly_drafts`) is a plain function with no APScheduler-specific code in it, specifically so it can be handed to Celery later without being rewritten - see [scaling-guide.md](scaling-guide.md).

### Containerization: Docker Compose

The explicit requirement was "runs on-premise, on hardware I control, starting simple." Docker Compose gives a single `docker compose up` that starts Postgres, the API, and the frontend on one machine, with no orchestration layer to learn or operate. The same three container images are what a later Kubernetes or ECS deployment would run - Compose is a development/single-host convenience, not a different artifact.

## What "on-premise first" actually means here

Nothing in the backend or frontend code assumes it's running on a specific machine or network. "On-premise" is entirely a deployment-topology decision (Compose on a machine you own, vs. the same containers on a cloud provider) - see [scaling-guide.md](scaling-guide.md) for exactly what changes (and, more importantly, what *doesn't* change) when you move off a single local machine.
