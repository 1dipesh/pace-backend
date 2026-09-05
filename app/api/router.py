from fastapi import APIRouter

from app.api.routes.alcohol import router as alcohol_router
from app.api.routes.endurance import router as endurance_router
from app.api.routes.health import router as health_router
from app.api.routes.nutrition import router as nutrition_router
from app.api.routes.profile import router as profile_router
from app.api.routes.training import router as training_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(profile_router)
api_router.include_router(nutrition_router)
api_router.include_router(training_router)
api_router.include_router(endurance_router)
api_router.include_router(alcohol_router)
