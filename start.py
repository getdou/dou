"""Entrypoint for Railway / production deployment."""
import os
import uvicorn

port = int(os.environ.get("PORT", 8080))
print(f"Starting dou on port {port}")
uvicorn.run("api.app:app", host="0.0.0.0", port=port, log_level="info")
