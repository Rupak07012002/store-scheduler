from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.config import settings
from app.jobs.scheduler import start_scheduler, stop_scheduler

app = FastAPI(
    title="Store Scheduler API",
    description="AI-assisted footfall forecasting and shift scheduling for retail stores.",
    version="0.1.0",
)

# CORS_ALLOWED_ORIGINS="*" is fine while only reached on a local network.
# Set it to your real domain(s) once reachable from the internet - see
# docs/public-exposure-guide.md. allow_credentials=True + "*" is rejected by
# browsers anyway once a real origin is set, which is the point.
_cors_origins = (
    ["*"] if settings.cors_allowed_origins.strip() == "*" else [o.strip() for o in settings.cors_allowed_origins.split(",")]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
def on_startup() -> None:
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
