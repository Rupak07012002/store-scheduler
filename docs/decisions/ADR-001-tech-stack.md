# ADR-001: Backend in Python/FastAPI, frontend in React/TypeScript

## Status
Accepted

## Context
The system needs both a conventional CRUD/auth API and genuinely algorithmic code (forecasting, constraint-solving with OR-Tools) on the backend, and two distinct user experiences (manager dashboard, employee self-service) on the frontend.

## Decision
Backend: FastAPI (Python). Frontend: React + TypeScript + Vite + Tailwind CSS.

## Rationale
- Python has the strongest ecosystem for the numerical work here (pandas for the forecaster, OR-Tools for the solver) - writing the API in a different language would mean either a second language in the codebase just for the AI pieces, or a network boundary between "the API" and "the AI" for no real benefit at this scale.
- FastAPI's Pydantic-based validation gives request/response type-checking for free, which matters when the frontend is maintained somewhat independently and needs a clear contract.
- React's component model earns its keep with two meaningfully different UIs sharing one auth/API layer. TypeScript catches a mismatched field name against the backend schema at compile time.

## Consequences
- Two languages to maintain (Python, TypeScript) instead of one full-stack language (e.g., a Node/TypeScript backend). Accepted because the numerical libraries needed only exist in Python's ecosystem in mature form.
- Tailwind is a build-time dependency, not a runtime one - no CSS-in-JS performance cost, but requires the build step to be part of the frontend Docker image (see `frontend/Dockerfile`).
