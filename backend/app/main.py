"""FastAPI application entry point for the Insider Threat Detection System."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.routes import alerts, dashboard, employees, model
from backend.app.core.config import (
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

    application = FastAPI(
        title="AI-Based Insider Threat Detection System API",
        version="0.3.0-phase3",
        description=(
            "Phase 3 backend API for unsupervised anomaly prioritization, "
            "causal behavioural explanations, and analyst alert investigation. "
            "Intended for local demonstration (localhost) prior to authentication/RBAC."
        ),
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "PATCH", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @application.exception_handler(Exception)
    async def safe_internal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred."},
        )

    @application.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
    def health_check(request: Request) -> dict:
        model_loaded = getattr(request.app.state, "predictor", None) is not None
        db_ready = getattr(request.app.state, "db_path", None) is not None
        return {
            "status": "ok",
            "phase": "3",
            "model_loaded": model_loaded,
            "database_ready": db_ready,
        }

    application.include_router(dashboard.router, prefix="/api/v1")
    application.include_router(employees.router, prefix="/api/v1")
    application.include_router(alerts.router, prefix="/api/v1")
    application.include_router(model.router, prefix="/api/v1")

    return application


app = create_app()
