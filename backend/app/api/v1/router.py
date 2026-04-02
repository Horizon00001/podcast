from fastapi import APIRouter

from app.api.v1 import generation, interactions, podcasts, recommendations, users


api_router = APIRouter()
api_router.include_router(podcasts.router)
api_router.include_router(users.router)
api_router.include_router(interactions.router)
api_router.include_router(recommendations.router)
api_router.include_router(generation.router)
