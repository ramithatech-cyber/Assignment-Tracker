import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.database import create_db_and_tables
from app.rate_limit import limiter
from app.routers import activities, admin, assignments, auth, submissions
from app.services.errors import AnalysisError
from app.services.scoring import RUBRIC, TOTAL_POINTS

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    if not settings.openai_api_key:
        logging.getLogger(__name__).warning(
            "OPENAI_API_KEY is not set - submissions will fail until it is."
        )
    yield


app = FastAPI(
    title=settings.app_name,
    description="Students submit a GitHub repository; it is analysed and scored out of 100.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AnalysisError)
async def analysis_error_handler(request: Request, exc: AnalysisError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(auth.router)
app.include_router(assignments.router)
app.include_router(submissions.router)
app.include_router(activities.router)
app.include_router(admin.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "openai_configured": bool(settings.openai_api_key),
        "model": settings.openai_model,
    }


@app.get("/api/rubric", tags=["meta"])
def rubric() -> dict:
    """The grading rubric, so the UI can explain the score without hardcoding it."""
    return {
        "total_points": TOTAL_POINTS,
        "categories": [
            {"key": i["key"], "label": i["label"], "max": i["max"], "guidance": i["guidance"]}
            for i in RUBRIC
        ],
    }
