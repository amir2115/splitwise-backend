from fastapi import APIRouter

from app.api import auth, expenses, groups, health, members, settlements, sync

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
api_router.include_router(members.router, prefix="/members", tags=["members"])
api_router.include_router(expenses.router, prefix="/expenses", tags=["expenses"])
api_router.include_router(settlements.router, prefix="/settlements", tags=["settlements"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
