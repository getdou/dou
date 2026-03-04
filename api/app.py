"""Main FastAPI application for dòu.

Initializes all services on startup, mounts routes, serves web UI.

Run with:
    python -m api.app
"""

from __future__ import annotations

import logging
import os
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# configure logging first — no fancy imports needed
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("dou")


# ---- lazy config loading (avoid crashing if pydantic-settings is missing) ----
def _load_settings():
    try:
        from api.config import settings
        return settings
    except Exception as exc:
        logger.warning("Could not load settings: %s — using defaults", exc)
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared services on startup, cleanup on shutdown."""
    logger.info("starting dou...")

    settings = _load_settings()
    client = None
    translator = None

    # try to init gateway
    try:
        from gateway import DouyinClient, DeviceAuth
        auth = DeviceAuth(
            device_id=(settings.douyin_device_id if settings else "") or None,
            proxy=(settings.proxy_url if settings else "") or None,
        )
        client = DouyinClient(auth=auth)
        device_preview = (auth.fingerprint.device_id[:12] + "...") if auth.fingerprint.device_id else "new"
        logger.info("Gateway initialized: device=%s", device_preview)
    except Exception as exc:
        logger.warning("Gateway init failed: %s", exc)
        logger.debug(traceback.format_exc())

    # try to init translation engine
    try:
        from translate import TranslationEngine
        translator = TranslationEngine(
            api_key=(settings.deepseek_api_key if settings else "") or "",
            model=(settings.deepseek_model if settings else "deepseek-chat"),
            redis_url=(settings.redis_url if settings else "redis://localhost:6379"),
            cache_ttl=(settings.translation_cache_ttl if settings else 3600),
        )
        logger.info("Translation engine initialized")
    except Exception as exc:
        logger.warning("Translation engine init failed: %s", exc)

    app.state.douyin_client = client
    app.state.translator = translator
    logger.info("dou ready")

    yield

    # cleanup
    for svc in (client, translator):
        if svc and hasattr(svc, "close"):
            try:
                await svc.close()
            except Exception:
                pass
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

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # try to add custom middleware
    try:
        from api.middleware import RateLimitMiddleware, ErrorHandlerMiddleware
        settings = _load_settings()
        app.add_middleware(ErrorHandlerMiddleware)
        app.add_middleware(RateLimitMiddleware, rpm=settings.rate_limit_rpm if settings else 120)
    except Exception as exc:
        logger.warning("Could not load middleware: %s", exc)

    # ---- always-available endpoints ----
    @app.get("/")
    async def root():
        web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
        if os.path.isdir(web_dir) and os.path.isfile(os.path.join(web_dir, "index.html")):
            from fastapi.responses import FileResponse
            return FileResponse(os.path.join(web_dir, "index.html"))
        return {
            "name": "dou",
            "description": "Open access to Douyin. No VPN. No censorship.",
            "version": "0.2.0",
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "service": "dou",
            "gateway": app.state.douyin_client is not None if hasattr(app.state, "douyin_client") else False,
            "translator": app.state.translator is not None if hasattr(app.state, "translator") else False,
        }

    # ---- try to mount API routes (may fail if deps are broken) ----
    try:
        from api.routes import feed, video, user, translate as translate_routes
        app.include_router(feed.router, prefix="/api/feed", tags=["feed"])
        app.include_router(video.router, prefix="/api/video", tags=["video"])
        app.include_router(user.router, prefix="/api/user", tags=["user"])
        app.include_router(translate_routes.router, prefix="/api/translate", tags=["translate"])
        logger.info("API routes loaded")
    except Exception as exc:
        logger.warning("Could not load API routes: %s", exc)
        logger.debug(traceback.format_exc())

    # ---- try to mount websocket ----
    try:
        from api.ws import router as ws_router
        app.include_router(ws_router, prefix="/ws", tags=["websocket"])
    except Exception as exc:
        logger.warning("Could not load WebSocket routes: %s", exc)

    # ---- serve web UI static assets ----
    try:
        from fastapi.staticfiles import StaticFiles
        web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
        if os.path.isdir(web_dir):
            app.mount("/static", StaticFiles(directory=web_dir), name="web-static")
            logger.info("Static files mounted from %s", web_dir)
    except Exception as exc:
        logger.warning("Could not mount static files: %s", exc)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("api.app:app", host="0.0.0.0", port=port, log_level="info")
