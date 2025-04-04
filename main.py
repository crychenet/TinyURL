from fastapi import FastAPI, Depends
from auth.users import fastapi_users, auth_backend
from auth.schemas import UserRead, UserCreate, UserUpdate
from models import User
from auth.users import current_active_user
from init_db import init_db
from routes.links import router
import asyncio
from utils import start_stats_sync_loop
from logger import get_logger


logger = get_logger(__name__)

app = FastAPI()

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"]
)

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"]
)

app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/auth/users",
    tags=["auth"]
)


app.include_router(router)


@app.get("/me", tags=["me"])
async def read_current_user(user: User = Depends(current_active_user)):
    return {"email": user.email, "id": str(user.id)}


@app.on_event("startup")
async def startup():
    await init_db()
    logger.info("Database initialized")
    asyncio.create_task(start_stats_sync_loop())
    logger.info("Stats sync loop started")
