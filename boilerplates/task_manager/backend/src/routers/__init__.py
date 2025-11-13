from fastapi import APIRouter

from .auth import router as auth_router
from .tasks import router as tasks_router
from .projects import router as projects_router
from .comments import router as comments_router
from .activities import router as activities_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(comments_router, prefix="/comments", tags=["comments"])
api_router.include_router(activities_router, prefix="/activities", tags=["activities"])

__all__ = ["api_router"]
