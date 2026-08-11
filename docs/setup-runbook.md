# On-Premise Setup Runbook

Follow this on the machine that will actually run the scheduler day-to-day (a spare office PC, a small server, a NUC - anything that stays on and reachable on your local network). Every step says what it does and how to confirm it worked, so you're not just typing commands blind.

## 0. Prerequisites

- **Docker Desktop** (Mac/Windows) or **Docker Engine + Docker Compose** (Linux) installed and running.
  - Check: `docker --version` and `docker compose version` should both print a version number, not an error.
- At least 4GB of free RAM and a few GB of disk space (Postgres, the two app images, and their dependencies).
- This repository copied onto the machine (via `git clone`, a USB drive, whatever gets it there).

## 1. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and change, at minimum, before this ever touches real data:
- `POSTGRES_PASSWORD` - the database password.
- `JWT_SECRET_KEY` - a long random string (this signs login tokens; anyone who has it can forge a login).

Everything else has a sensible default and can be left alone for now - each variable is explained in `.env.example` itself.

**Why this step exists**: the app reads all configuration from environment variables (see `app/config.py`), never from hardcoded values, specifically so the same code runs correctly on your laptop, this on-prem machine, and a future cloud deployment - only the `.env` file changes.

## 2. Start the containers

```bash
docker compose up -d
```

This builds and starts three containers: `postgres` (the database), `backend` (the API + AI logic), and `frontend` (the web UI).

**Verify it worked**:
```bash
docker compose ps
```
All three should show `Up` (postgres should also say `healthy` after a few seconds).

If something failed, `docker compose logs backend` (or `postgres`, or `frontend`) shows why.

## 3. Apply database migrations

```bash
docker compose exec backend alembic upgrade head
```

This creates every table the app needs (see [data-model.md](data-model.md) for what they are). It's safe to re-run - Alembic tracks which migrations have already applied and skips them.

**Verify it worked**:
```bash
docker compose exec postgres psql -U scheduler -d scheduler -c "\dt"
```
You should see a list of ~14 tables (`stores`, `employees`, `schedule_runs`, etc.).

## 4. Seed synthetic sample data

```bash
docker compose exec backend python scripts/seed_synthetic_data.py
```

This creates 8 sample stores, ~30 employees each, ~100 historical footfall records each, and printable login credentials for an Owner account, one Store Manager per store, and one demo Employee login per store.

**This step is idempotent** - if you run it again, it detects that stores already exist and does nothing, rather than duplicating data. To start over from a truly empty database, see the "Resetting" section below.

**Verify it worked**: the script prints a summary line (`Seeded 8 stores, 240 employees, ~816 footfall records`) and the login credentials to use in step 6.

## 5. Confirm the API is healthy

```bash
curl http://localhost:8000/health
```
Should return `{"status":"ok"}`. If you want to see the full interactive API documentation, open http://localhost:8000/docs in a browser.

## 6. Log in

Open http://localhost:5173 in a browser on the same machine (or another machine on the same network, using this machine's IP address instead of `localhost`).

Log in with the Owner credentials printed in step 4 (default: `owner@example.com` / `owner-password-change-me`). **Change this password before this system holds any real schedule or employee data** - v1 doesn't have a "change password" UI yet, so do it by updating the `seed_owner_password` value and re-seeding a fresh database, or directly via the API's `/api/v1/auth` endpoints.

## 7. Try the whole pipeline once

1. Click into any store.
2. Look at the footfall forecast chart - it should show a plausible pattern (weekends busier than weekdays, since that's baked into the synthetic seed data).
3. Click "Generate schedule for this week."
4. Click "Review" on the new schedule run - you should see a full week of shift assignments and a "No compliance issues" message (or specific flags if something's off).
5. Click "Publish schedule."
6. Log out, log back in as one of the demo employee accounts (`employee.<store-slug>@example.com`, same password as the manager accounts), and confirm you can see your published shifts under "My Shifts."

If all of that works, the full pipeline - forecast, optimize, review, publish, employee view - is functioning correctly on your machine.

## Resetting to a clean slate

To wipe the database entirely and start over (e.g., after experimenting with the synthetic data and wanting a fresh start before connecting real data):

```bash
docker compose down -v   # -v also removes the Postgres data volume
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed_synthetic_data.py
```

**`docker compose down -v` permanently deletes all data in the database.** Only run it when you actually intend to start over.

## Day-to-day operation

- **Restarting after a reboot**: containers are configured to restart automatically (`restart: unless-stopped` in `docker-compose.yml`), so a machine reboot should bring everything back up. Confirm with `docker compose ps`.
- **Viewing logs**: `docker compose logs -f backend` (or `frontend`, or `postgres`) to watch what's happening live.
- **The weekly automatic draft job**: every Sunday at 02:00 UTC, the backend automatically generates a *draft* schedule for the coming week for every store (see `app/jobs/scheduler.py`). It only ever creates drafts - nothing is published without a manager reviewing it in the UI first.
- **Backing up**: with everything on one machine, `docker compose exec postgres pg_dump -U scheduler scheduler > backup.sql` produces a full database backup. Do this regularly once real data is involved - see [scaling-guide.md](scaling-guide.md) for moving to automated, managed backups.
