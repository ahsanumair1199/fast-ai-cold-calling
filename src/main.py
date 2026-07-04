import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

from .config import get_settings
from .db import init_db
from .routers.auth import auth_router
from .routers.calls import calls_router
from .routers.campaigns import campaigns_router
from .routers.voices import voices_router
from .services.campaign_dialer import run_dialer_loop

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    dialer_task = asyncio.create_task(run_dialer_loop())
    yield
    dialer_task.cancel()


app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    lifespan=lifespan,
)

cors_origins = settings.cors_allow_origins
if settings.environment == "dev" and not cors_origins:
    cors_origins = ["*"]
    logger.warning("CORS_ALLOW_ORIGINS not set - defaulting to '*' because ENVIRONMENT=dev. Set it explicitly in production.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(voices_router)
app.include_router(calls_router)
app.include_router(campaigns_router)
