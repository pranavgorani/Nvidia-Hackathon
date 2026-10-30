import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.db.init_db import init_models, seed_data
from app.api import auth, crm, documents, agent, approvals, skills, audit, dashboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("docuflow")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing DocuFlow AI Agent OS database...")
    await init_models()
    async with AsyncSessionLocal() as session:
        await seed_data(session)
    logger.info("DocuFlow database initialized and seeded successfully.")
    yield
    logger.info("DocuFlow application shutting down.")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="DocuFlow AI Agent OS — SaaS2Agent Hackathon Platform powered by Google Gemini API",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler for safety
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Technical logs have been recorded safely."}
    )

# Include Routers
app.include_router(auth.router)
app.include_router(crm.router)
app.include_router(documents.router)
app.include_router(agent.router)
app.include_router(approvals.router)
app.include_router(skills.router)
app.include_router(audit.router)
app.include_router(dashboard.router)

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "ai_provider": settings.AI_PROVIDER,
        "gemini_model": settings.GEMINI_MODEL,
        "environment": settings.APP_ENV
    }

