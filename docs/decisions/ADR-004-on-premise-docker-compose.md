# ADR-004: On-premise deployment via Docker Compose for v1

## Status
Accepted

## Context
The store owner explicitly requested the system run on-premise first (self-hosted, on hardware they control), starting simple, with a clear and concrete path to a cloud/production deployment later - rather than depending on a managed cloud SaaS from day one.

## Decision
Ship v1 as three Docker containers (Postgres, backend, frontend) orchestrated by a single `docker-compose.yml`, runnable with `docker compose up` on one machine.

## Rationale
- Docker Compose is the smallest amount of infrastructure that still cleanly separates the three concerns (database, API, UI) into independently manageable, independently restartable units, without requiring the owner to learn or operate Kubernetes for a single-machine deployment.
- Every component chosen (PostgreSQL, FastAPI, React) is fully open-source and runs identically whether self-hosted or on a managed cloud service - nothing here is a cloud-vendor-specific dependency that would need to be ripped out later.
- The three container images this produces are exactly what a later Kubernetes/ECS deployment would run - Compose-to-orchestrator is a mechanical translation (see `docs/scaling-guide.md` item 7), not a rewrite.

## Consequences
- No built-in high availability, auto-scaling, or zero-downtime deploys - acceptable for a single-owner, single-machine v1, and explicitly out of scope until the business's scale actually needs it.
- Backups, TLS, and monitoring are opt-in, documented next steps (`docs/scaling-guide.md` items 4 and 8) rather than defaults - appropriate for a system currently reachable only on a local network with synthetic data, but **must** be addressed before real employee/schedule data is at stake or the system is exposed beyond the local network.
