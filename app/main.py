"""CodeSense — AI Code Intelligence Agent — FastAPI entry point."""
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.db.postgres import init_db
from app.core.config import settings

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting CodeSense", model=settings.ollama_model)
    await init_db()
    log.info("Database initialised")
    yield
    log.info("CodeSense shutting down")


app = FastAPI(
    title="CodeSense — AI Code Intelligence Agent",
    description=(
        "AI-powered code intelligence across 11 workflows: "
        "PR review · bug detection · code explanation · refactoring · "
        "test generation · migration planning · impact analysis · "
        "version bump · license compliance · vulnerability scanning."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", tags=["System"])
async def root():
    return {
        "name":    "CodeSense",
        "version": "1.0.0",
        "docs":    "/docs",
        "health":  "/api/v1/health",
    }
