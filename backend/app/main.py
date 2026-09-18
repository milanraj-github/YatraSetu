import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.firebase import initialize_firebase
from app.api.v1.router import api_v1_router

from app.services.scheduler_service import start_background_scheduler

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("smartbus.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SMARTBUS Backend...")
    initialize_firebase()
    scheduler = start_background_scheduler()
    yield
    logger.info("Shutting down SMARTBUS Backend...")
    if scheduler:
        scheduler.shutdown()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Intelligent College Bus Tracking Backend — Firebase-Only Auth Module",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code = "HTTP_ERROR"
    message = str(exc.detail)

    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "HTTP_ERROR")
        message = exc.detail.get("message", str(exc.detail))

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message
            }
        },
        headers=exc.headers
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc)
            }
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception caught on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred."
            }
        }
    )

app.include_router(api_v1_router)

@app.get("/", tags=["Health Check"])
async def root():
    return {
        "success": True,
        "message": f"Welcome to {settings.PROJECT_NAME} — Firebase-Only Auth API",
        "docs": "/docs"
    }

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "environment": settings.ENVIRONMENT}

from fastapi.responses import FileResponse
import os

@app.get("/map", tags=["Live Tracking Map"])
async def serve_live_map():
    map_path = os.path.join(os.path.dirname(__file__), "..", "live_tracking_map.html")
    return FileResponse(map_path)

@app.get("/dashboard", tags=["Dashboard"])
async def serve_dashboard():
    dashboard_path = os.path.join(os.path.dirname(__file__), "..", "static", "dashboard.html")
    return FileResponse(dashboard_path)



