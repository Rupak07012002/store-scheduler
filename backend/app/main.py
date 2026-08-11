from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.jobs.scheduler import start_scheduler, stop_scheduler

app = FastAPI(
    title="Store Scheduler API",
    description="AI-assisted footfall forecasting and shift scheduling for retail stores.",
    version="0.1.0",
)

# Wide-open CORS is fine for an on-prem v1 reached only over a local network;
# tighten this to explicit origins before exposing the app beyond localhost -
# see docs/scaling-guide.md.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
