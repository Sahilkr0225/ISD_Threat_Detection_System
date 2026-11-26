"""FastAPI application entry point (Phase 1 minimal shell; full API planned for Phase 3+)."""

from fastapi import FastAPI

app = FastAPI(
    title="AI-Based Insider Threat Detection System API",
    version="0.1.0-phase1",
    description="Phase 1 data engineering foundation. Full inference and alert endpoints are planned for later phases.",
)


@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    """Basic liveness check."""
    return {"status": "ok", "phase": "1"}

