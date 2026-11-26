"""FastAPI dependency providers."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from fastapi import Request
import sqlite3

from backend.app.database.connection import get_db_connection
from backend.app.ml.predictor import ModelPredictor
from backend.app.risk.scoring import PriorityClassifier, RiskScorer


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection bound to the configured application database path."""
    db_path: Path = request.app.state.db_path
    with get_db_connection(db_path) as conn:
        yield conn


def get_predictor(request: Request) -> ModelPredictor:
    return request.app.state.predictor


def get_risk_scorer(request: Request) -> RiskScorer:
    return request.app.state.risk_scorer


def get_priority_classifier(request: Request) -> PriorityClassifier:
    return request.app.state.priority_classifier

