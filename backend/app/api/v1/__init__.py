from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.availability import router as availability_router
from app.api.v1.employees import router as employees_router
from app.api.v1.forecasts import router as forecasts_router
from app.api.v1.me import router as me_router
from app.api.v1.schedules import router as schedules_router
from app.api.v1.shift_templates import router as shift_templates_router
from app.api.v1.stores import router as stores_router
from app.api.v1.swaps import router as swaps_router
from app.api.v1.timeoff import router as timeoff_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(stores_router)
api_router.include_router(employees_router)
api_router.include_router(shift_templates_router)
api_router.include_router(availability_router)
api_router.include_router(timeoff_router)
api_router.include_router(forecasts_router)
api_router.include_router(schedules_router)
api_router.include_router(swaps_router)
api_router.include_router(me_router)
