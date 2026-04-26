import os

from fastapi import FastAPI

from .config import settings
from .database import Base, engine
from .logging_config import configure_logging
from .routers import admin_logs, feedback, predict, reports, training


def create_app() -> FastAPI:
    configure_logging("backend")
    os.makedirs(settings.upload_dir, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    app = FastAPI(title="Mosquito AI", version="0.1.0")
    app.include_router(predict.router)
    app.include_router(reports.router)
    app.include_router(feedback.router)
    app.include_router(training.router)
    app.include_router(admin_logs.router)
    return app


app = create_app()
