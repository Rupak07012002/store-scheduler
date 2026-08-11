# Store Scheduler

An AI-assisted workforce scheduler for a multi-store retailer: it predicts customer footfall per store from POS transaction data, translates that into required staffing levels, and uses a constraint solver to build a draft weekly shift schedule that meets demand while minimizing scheduled hours - all reviewable and editable by a manager before anything goes live to employees.

Built for **on-premise deployment first** (a single machine you control, via Docker Compose), using **synthetic sample data** (8 stores, ~30 employees/store, ~100 footfall records/store) so the entire pipeline can be run and understood before connecting a real Shopify store or hiring data.

## Why this exists

Manually scheduling ~240 employees across 8 stores to match customer demand - without over- or under-staffing any shift - is a constraint-satisfaction problem that gets harder every time a store's hours, an employee's availability, or labor rules change. This system automates the repetitive part (translating demand into a legal, feasible draft schedule) while keeping a human in the loop for every publish.

## Quick start

```bash
cp .env.example .env
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed_synthetic_data.py
```

Then open http://localhost:5173 and log in with the credentials printed by the seed script (default: `owner@example.com` / `owner-password-change-me` - change these before any real deployment).

See [docs/setup-runbook.md](docs/setup-runbook.md) for the full step-by-step walkthrough, including what to check at each step and how to reset if something goes wrong.

## Documentation map

| Document | What it covers |
|---|---|
| [docs/architecture.md](docs/architecture.md) | System overview, the end-to-end pipeline, and why each component exists |
| [docs/data-model.md](docs/data-model.md) | Every database table, its fields, and the reasoning behind the schema |
| [docs/forecasting-and-optimization.md](docs/forecasting-and-optimization.md) | Plain-language explanation of the forecasting model and the scheduling optimizer - the "AI" parts |
| [docs/setup-runbook.md](docs/setup-runbook.md) | Step-by-step on-premise deployment, from a clean machine to a working app |
| [docs/public-exposure-guide.md](docs/public-exposure-guide.md) | Making that machine reachable from the internet (Cloudflare Tunnel or port-forwarding + TLS), plus a security checklist |
| [docs/scaling-guide.md](docs/scaling-guide.md) | The concrete, ordered path from this on-prem v1 to a real production deployment with live Shopify data |
| [docs/decisions/](docs/decisions/) | Short ADRs (Architecture Decision Records) explaining specific technical choices and their trade-offs |

## Tech stack at a glance

- **Backend**: FastAPI (Python) + PostgreSQL + SQLAlchemy/Alembic + Google OR-Tools (CP-SAT solver) + pandas
- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Auth**: JWT (access + refresh tokens), role-based (Owner, Store Manager, Employee)
- **Deployment**: Docker Compose (on-premise, single machine)
- **Background jobs**: APScheduler (in-process weekly draft-schedule generation)

Every one of these choices is explained - not just stated - in [docs/architecture.md](docs/architecture.md) and the ADRs.

## Current scope (v1)

Built: POS-transaction-based footfall forecasting, CP-SAT shift optimization, manager review/edit/publish workflow, compliance flagging (overtime, rest, coverage), employee self-service (availability, time-off, published schedule view), shift swaps with manager approval.

Explicitly deferred (see [docs/scaling-guide.md](docs/scaling-guide.md) for the path to each): live Shopify data sync, camera-based computer-vision footfall counting, true wage-based cost minimization, warehouse scheduling, multi-timezone support, cloud deployment.
