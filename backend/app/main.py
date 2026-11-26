"""FastAPI application entry point for the Insider Threat Detection System."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.routes import alerts, audit, auth, dashboard, employees, model, users
from backend.app.core.config import (
    APP_ENV,
    CORS_ORIGINS,
    DATABASE_PATH,
    MODEL_BUNDLE_PATH,
    VALIDATION_SCORE_REF_PATH,
)
from backend.app.database.schema import init_database
from backend.app.ml.predictor import ModelPredictor
from backend.app.risk.scoring import PriorityClassifier, RiskScorer
from backend.app.schemas.api_schemas import HealthResponse


def create_app(
    db_path: Optional[Path] = None,
    model_bundle_path: Optional[Path] = None,
    val_ref_path: Optional[Path] = None,
) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    resolved_db = Path(db_path or DATABASE_PATH)
    resolved_model = Path(model_bundle_path or MODEL_BUNDLE_PATH)
    resolved_val_ref = Path(val_ref_path or VALIDATION_SCORE_REF_PATH)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        init_database(resolved_db)
        predictor = ModelPredictor(resolved_model)
        risk_scorer = RiskScorer.from_npy(resolved_val_ref)
        priority_classifier = PriorityClassifier(predictor.calibrated_thresholds)

        application.state.db_path = resolved_db
        application.state.predictor = predictor
        application.state.risk_scorer = risk_scorer
        application.state.priority_classifier = priority_classifier
        yield

    is_dev = APP_ENV == "development"
    application = FastAPI(
        title="AI-Based Insider Threat Detection System API",
        version="0.6.0-phase6",
        description=(
            "Phase 6 backend API with server-side session authentication, CSRF protection, "
            "Role-Based Access Control (RBAC), and security audit logging."
        ),
        docs_url="/docs" if is_dev else None,
        redoc_url="/redoc" if is_dev else None,
        openapi_url="/openapi.json" if is_dev else None,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "PATCH", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    @application.exception_handler(Exception)
    async def safe_internal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred."},
        )

    @application.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
    def health_check() -> dict:
        """Minimal public liveness check (does not expose internal state)."""
        return {"status": "ok", "phase": "6"}

    application.include_router(auth.router, prefix="/api/v1")
    application.include_router(users.router, prefix="/api/v1")
    application.include_router(audit.router, prefix="/api/v1")
    application.include_router(dashboard.router, prefix="/api/v1")
    application.include_router(employees.router, prefix="/api/v1")
    application.include_router(alerts.router, prefix="/api/v1")
    application.include_router(model.router, prefix="/api/v1")

    return application


app = create_app()
