# Scaling Guide: From On-Premise v1 to Real Production

This is the ordered, concrete path from what's running today (Docker Compose on one machine, synthetic data) to a real production deployment. Each section says exactly what changes, what doesn't, and why the seam was built where it was.

## 1. Connect real Shopify data (replaces synthetic footfall)

**What changes**: add a scheduled sync job (a new function alongside `app/jobs/tasks.py::generate_weekly_drafts`, wired into `app/jobs/scheduler.py` the same way) that calls the Shopify Admin API's Orders endpoint, aggregates transaction counts per store/hour-block, and writes `FootfallRecord` rows with `source="shopify"` instead of `source="synthetic"`.

**What doesn't change**: the forecaster, the labor-requirement translation, and the optimizer all read from `FootfallRecord` regardless of `source` - none of that code needs to know where the data came from. You can run both sources side by side (e.g., synthetic history for stores not yet on Shopify, real data for stores that are) without any schema change.

**Do this once you have**: a Shopify Admin API access token for each store (or one token if all stores share one Shopify account) and have decided how "a transaction" maps to "a customer" for your specific catalog (e.g., does one checkout with 5 items count as 1 customer, which is the assumption baked into using raw transaction count as a footfall proxy).

## 2. Turn on real labor-cost minimization (once wage data exists)

**What changes**: populate `Employee.wage_rate` for real employees (via the admin CRUD API, or a one-time import script). `app/services/optimization/cost.py::objective_weight_cents_per_hour` already checks for a populated `wage_rate` and uses it if present - this is a data change, not a code change.

**What doesn't change**: everything else in the optimizer. The objective function's shape is identical; only the per-employee weight changes from a flat placeholder to a real dollar figure.

## 3. Move Postgres to a managed database

**What changes**: point `DATABASE_URL` in `.env` (or your deployment's secret manager) at a managed Postgres instance (AWS RDS, GCP Cloud SQL, etc.) instead of the `postgres` container. Run `alembic upgrade head` once against the new database to create the schema, then either start fresh or migrate data with `pg_dump`/`pg_restore`.

**What doesn't change**: the schema, every model, every query. This is possible with zero code changes specifically because v1 used vanilla PostgreSQL via SQLAlchemy, not a Postgres-only feature that a managed provider doesn't support.

**Do this when**: you need automated backups/failover you don't want to operate yourself, or the on-premise machine's disk/uptime becomes a real risk to data you can't afford to lose.

## 4. Add TLS and a real domain

**What changes**: enable the `nginx` service already defined (but disabled by default) in `docker-compose.yml`: `docker compose --profile proxy up -d`. Configure `infra/nginx/` with your domain and a TLS certificate (Let's Encrypt via Certbot, or your provider's managed TLS). Point DNS at the machine.

**What doesn't change**: the backend and frontend containers - nginx sits in front of them as a reverse proxy; neither app needs to know about TLS itself.

**Do this before**: this system is reachable from outside your local network. Right now, CORS is wide open (`allow_origins=["*"]` in `app/main.py`) because it's assumed to be reached only from your own network - tighten this to your actual domain at the same time.

## 5. Move the weekly job from APScheduler to Celery

**What changes**: add a Redis container to `docker-compose.yml`, add `celery` to `requirements.txt`, and wrap `app/jobs/tasks.py::generate_weekly_drafts` as a `@celery_app.task` instead of registering it with APScheduler. The function body itself doesn't change - it was written as a plain, framework-agnostic function specifically for this move.

**Do this when**: you're running more stores than a single weekly cron-style job comfortably handles sequentially, or you need retry-on-failure/observability that APScheduler doesn't provide, or you're running multiple API replicas (see #7) and need exactly one of them to run the job, not all of them.

## 6. Add the camera-based computer-vision footfall pipeline (v2)

This was the second footfall-prediction approach discussed and explicitly deferred in favor of shipping the simpler POS-based approach first. When you're ready:

**What this adds**: an edge device per store (a Raspberry Pi or NVIDIA Jetson Nano is enough) running a lightweight person-detection model (e.g., YOLOv8-nano) on a camera feed pointed at the store entrance, counting people in and out. The device transmits only the resulting **counts**, never video, to the backend - both for privacy and bandwidth.

**What changes in this codebase**: a new authenticated API endpoint (e.g., `POST /api/v1/footfall/camera-count`) that writes `FootfallRecord` rows with `source="camera"` - the enum value already exists and is reserved for exactly this. The forecaster can then be configured to prefer `camera` data over `shopify`/`synthetic` where available, since raw people-counting is a more direct footfall measure than transaction count (it captures browsers who don't buy, which a POS-based count misses entirely).

**Before building this**: get a legal/privacy review of in-store camera use in your jurisdiction (customer notice requirements vary a lot by state/country) - this is explicitly a "consult a professional" item, not something to route around technically.

## 7. Move from Docker Compose to Kubernetes/ECS

**What changes**: the same three container images (`backend`, `frontend`, and a `worker` if you did step 5) get deployed as Deployments/Services on Kubernetes, or Tasks/Services on ECS, instead of Compose services. Environment variables become ConfigMaps/Secrets. This is a largely mechanical translation - Compose services and Kubernetes Deployments both express "run this image, with this config, expose this port."

**Do this when**: you need to run multiple stores' worth of load across multiple machines, need zero-downtime deploys, or need auto-scaling - none of which a single on-premise machine can give you.

## 8. Add monitoring and automated backups

**What changes**: add a metrics/logging stack (Prometheus + Grafana, or a hosted equivalent like Datadog) reading from the backend's logs and a `/metrics` endpoint (not yet built - a small addition to `app/main.py`). For backups, either rely on the managed database's automated backups (step 3) or set up a scheduled `pg_dump` job writing to off-machine storage.

**Do this before**: this system is something the business depends on daily and losing a week of schedules/availability data would be a real problem, not just an inconvenience.

## Multi-jurisdiction labor rules (if you expand beyond one region)

v1 assumes all 8 stores share one set of labor rules and one timezone (confirmed scope). `LaborRuleConfig` already supports a per-store override (`store_id` is nullable, falls back to a global default) - expanding to genuinely different state/country rules is mostly a data-entry exercise (add a row per store with different thresholds), not a schema change. Multiple timezones would require promoting `business_timezone` from a single global config value (`app/config.py`) to a per-`Store` column, which *is* a schema change - flagged here specifically because it's easy to defer accidentally if a 9th store gets added in a different timezone without anyone revisiting this assumption.
