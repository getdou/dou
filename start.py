"""Entrypoint for Railway."""
import os
import sys

print("=== DOU STARTING ===", flush=True)
print(f"Python: {sys.version}", flush=True)
print(f"PORT env: {os.environ.get('PORT', 'NOT SET')}", flush=True)

port = int(os.environ.get("PORT", 8080))

try:
    import uvicorn
    print(f"uvicorn imported OK, starting on port {port}", flush=True)
except ImportError:
    print("ERROR: uvicorn not installed", flush=True)
    sys.exit(1)

try:
    from api.app import app
    print("app imported OK", flush=True)
except Exception as e:
    print(f"ERROR importing app: {e}", flush=True)
    # fallback: create minimal app
    from fastapi import FastAPI
    app = FastAPI()

    @app.get("/")
    async def root():
        return {"status": "ok", "error": str(e)}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    print("using fallback minimal app", flush=True)

uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
