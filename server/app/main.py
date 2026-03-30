from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.db.bootstrap import ensure_database_ready


settings = get_settings()
logging.basicConfig(level=settings.log_level)

app = FastAPI(title="Conversation Tree API", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    ensure_database_ready()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "role": settings.service_role}


app.include_router(router)


def run() -> None:
    uvicorn.run("app.main:app", host=settings.bind_host, port=settings.bind_port, reload=False)


if __name__ == "__main__":
    run()
