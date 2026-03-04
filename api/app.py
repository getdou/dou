"""Main FastAPI application for dòu.

Initializes all services on startup, mounts routes, serves web UI.

Run with:
    python -m api.app
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from gateway import DouyinClient, DeviceAuth
from translate import TranslationEngine
from api.config import settings
from api.middleware import RateLimitMiddleware, ErrorHandlerMiddleware
from api.routes import feed, video, user, translate as translate_routes
from api.ws import router as ws_router

# configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("dou")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared services on startup, cleanup on shutdown."""
    logger.info("starting dou...")

    # initialize gateway
    auth = DeviceAuth(
        device_id=settings.douyin_device_id or None,
        proxy=settings.proxy_url or None,
    )
    client = DouyinClient(auth=auth)

    # initialize translation engine
    translator = TranslationEngine(
        api_key=settings.deepseek_api_key,
        model=settings.deepseek_model,
        redis_url=settings.redis_url,
        cache_ttl=settings.translation_cache_ttl,
    )

    # store on app state for route access
    app.state.douyin_client = client
    app.state.translator = translator

    logger.info(
        "dou ready - device=%s, deepseek=%s, redis=%s",
        auth.fingerprint.device_id[:12] + "...",
        "configured" if settings.deepseek_api_key else "NOT SET",
        settings.redis_url,
    )

    yield

    # cleanup
    await client.close()
    await translator.close()
    logger.info("dou stopped")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="dou",
        description="Open access to Douyin. No VPN. No censorship. No phone number.",
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
    )

    # middleware (order matters — outermost first)
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        rpm=settings.rate_limit_rpm,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(feed.router, prefix="/api/feed", tags=["feed"])
    app.include_router(video.router, prefix="/api/video", tags=["video"])
    app.include_router(user.router, prefix="/api/user", tags=["user"])
    app.include_router(
        translate_routes.router, prefix="/api/translate", tags=["translate"]
    )
    app.include_router(ws_router, prefix="/ws", tags=["websocket"])

    # serve web UI as static files (fallback)
    web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
    if os.path.isdir(web_dir):
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level,
    )
