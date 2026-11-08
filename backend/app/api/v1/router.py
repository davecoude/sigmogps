from fastapi import APIRouter

from app.api.v1.routes import auth, drivers, health, passengers, users, vehicles

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(vehicles.router)
api_router.include_router(drivers.router)
api_router.include_router(passengers.router)
api_router.include_router(users.router)
