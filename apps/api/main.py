import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.api.router import router as research_router
from apps.db.database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("research_system.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Research System API...")
    yield
    logger.info("Shutting down Research System API...")
    await engine.dispose()


app = FastAPI(
    title="Research Agent System API",
    description="Multi-Agent Research System with PostgreSQL persistence and human approval flow.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "research_agent_system"}
