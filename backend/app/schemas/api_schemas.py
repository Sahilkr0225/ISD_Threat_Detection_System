"""Pydantic v2 request and response schemas for the Phase 3 FastAPI backend."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

AlertStatusLiteral = Literal["OPEN", "UNDER_REVIEW", "RESOLVED", "DISMISSED"]
PriorityLiteral = Literal["Critical", "High", "Medium", "Low", "Informational"]
RoleLiteral = Literal["ADMINISTRATOR", "SECURITY_ANALYST", "AUDITOR"]


class HealthResponse(BaseModel):
    status: str
    phase: str


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class TopEmployeeItem(BaseModel):
    employee_id: str
    role: Optional[str] = None
    department: Optional[str] = None
    alert_count: int
    max_risk_score: float
    max_anomaly_score: float


class RecentInvestigationItem(BaseModel):
    history_id: int
    alert_id: int
    employee_id: str
    previous_status: str
    new_status: str
    analyst_note: Optional[str] = None
    changed_at: str
    actor_user_id: Optional[int] = None
    actor_username: Optional[str] = None
    actor_display_name: Optional[str] = None


class DashboardSummaryResponse(BaseModel):
    unique_employees: int
    total_observations: int
    flagged_observations: int
    total_alerts: int
    open_alerts: int
    critical_open_alerts: int = 0
    under_review_alerts: int
    resolved_alerts: int
    dismissed_alerts: int
    alerts_by_priority: Dict[str, int]
    top_employees: List[TopEmployeeItem]
    recent_investigations: List[RecentInvestigationItem]
    model_version: str
    coverage_start_date: Optional[str] = None
    coverage_end_date: Optional[str] = None


class DailyTrendPoint(BaseModel):
    activity_date: str
    total_observations: int
    flagged_count: int
    high_critical_count: int
    avg_risk_score: float


class DashboardTrendsResponse(BaseModel):
    items: List[DailyTrendPoint]


class EmployeeSummary(BaseModel):
    employee_id: str
    role: Optional[str] = None
    department: Optional[str] = None
    functional_unit: Optional[str] = None
    first_activity_date: str
    last_activity_date: str
    observation_count: int
    max_risk_score: float
    highest_priority: Optional[str] = None
    alert_count: int
    open_alert_count: int


class EmployeeListResponse(BaseModel):
    items: List[EmployeeSummary]
    pagination: PaginationMeta


class EmployeeDetailResponse(EmployeeSummary):
    avg_risk_score: float


class EmployeeObservationItem(BaseModel):
    observation_id: int
    employee_id: str
    activity_date: str
    login_count: int
    after_hours_login_count: int
    http_activity_count: int
    email_activity_count: int
    file_activity_count: int
    usb_activity_count: int
    total_activity_count: int
    after_hours_ratio: float
    is_weekend: int
    anomaly_score: float
    risk_score: float
    priority: str
    alert_id: Optional[int] = None
    alert_status: Optional[str] = None


class EmployeeHistoryResponse(BaseModel):
    employee_id: str
    items: List[EmployeeObservationItem]
    pagination: PaginationMeta


class AnomalyItem(BaseModel):
    observation_id: int
    employee_id: str
    activity_date: str
    login_count: int
    after_hours_login_count: int
    http_activity_count: int
    email_activity_count: int
    file_activity_count: int
    usb_activity_count: int
    total_activity_count: int
    anomaly_score: float
    risk_score: float
    priority: str
    alert_id: Optional[int] = None
    alert_status: Optional[str] = None


class AnomalyListResponse(BaseModel):
    items: List[AnomalyItem]
    pagination: PaginationMeta


class AlertExplanationItem(BaseModel):
    explanation_id: int
    feature_name: str
    activity_label: str
    current_value: float
    historical_mean: Optional[float] = None
    historical_std: Optional[float] = None
    deviation: Optional[float] = None
    direction: str
    historical_obs_count: int
    evidence_description: str
    investigation_recommendation: str


class AlertSummaryItem(BaseModel):
    alert_id: int
    observation_id: int
    employee_id: str
    role: Optional[str] = None
    department: Optional[str] = None
    activity_date: str
    anomaly_score: float
    risk_score: float
    priority: str
    status: str
    model_version: str
    activity_summary: Optional[str] = None
    created_at: str
    updated_at: str


class AlertListResponse(BaseModel):
    items: List[AlertSummaryItem]
    pagination: PaginationMeta


class AlertDetailResponse(AlertSummaryItem):
    functional_unit: Optional[str] = None
    login_count: int
    after_hours_login_count: int
    http_activity_count: int
    email_activity_count: int
    file_activity_count: int
    usb_activity_count: int
    total_activity_count: int
    after_hours_ratio: float
    is_weekend: int
    explanations: List[AlertExplanationItem]


class AlertStatusUpdateRequest(BaseModel):
    new_status: AlertStatusLiteral
    analyst_note: Optional[str] = Field(default=None, max_length=1000)


class InvestigationHistoryItem(BaseModel):
    history_id: int
    alert_id: int
    previous_status: str
    new_status: str
    analyst_note: Optional[str] = None
    changed_at: str
    actor_user_id: Optional[int] = None
    actor_username: Optional[str] = None
    actor_display_name: Optional[str] = None


class AlertHistoryResponse(BaseModel):
    alert_id: int
    items: List[InvestigationHistoryItem]


class FeatureVectorInput(BaseModel):
    login_count: float
    after_hours_login_count: float
    http_activity_count: float
    email_activity_count: float
    file_activity_count: float
    usb_activity_count: float
    total_activity_count: float
    after_hours_ratio: float
    is_weekend: float
    log_http_activity: float
    log_email_activity: float
    log_file_activity: float
    log_usb_activity: float
    login_hist_dev_14obs: float
    after_hours_hist_dev_14obs: float
    http_hist_dev_14obs: float
    email_hist_dev_14obs: float
    file_hist_dev_14obs: float
    usb_hist_dev_14obs: float
    total_activity_hist_dev_14obs: float


class ModelPredictBatchRequest(BaseModel):
    observations: List[FeatureVectorInput] = Field(..., min_length=1, max_length=500)


class ModelPredictionItem(BaseModel):
    anomaly_score: float
    risk_score: float
    priority: PriorityLiteral
    estimator_default_is_anomaly: bool
    is_flagged_for_review: bool


class ModelPredictResponse(BaseModel):
    model_version: str
    disclaimer: str
    predictions: List[ModelPredictionItem]


class ModelInfoResponse(BaseModel):
    model_version: str
    algorithm: str
    scaled: bool
    feature_count: int
    feature_names: List[str]
    hyperparameters: Dict[str, Any]
    calibrated_thresholds: Dict[str, float]
    disclaimer: str


class DataSummaryResponse(BaseModel):
    source_partition: str
    unique_employees: int
    observation_count: int
    unique_dates: int
    date_min: Optional[str] = None
    date_max: Optional[str] = None
    alert_count: int
    explanation_count: int
    investigation_history_count: int
    note: str


# --- Phase 6 Authentication, User Management & Audit Schemas ---

class UserPublic(BaseModel):
    user_id: int
    username: str
    display_name: str
    role: RoleLiteral
    is_active: bool
    created_at: str
    updated_at: str
    last_login_at: Optional[str] = None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class LoginResponse(BaseModel):
    user: UserPublic
    csrf_token: str
    expires_at: str


class CsrfResponse(BaseModel):
    csrf_token: str


class SessionMeResponse(BaseModel):
    user: UserPublic
    session_expires_at: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=12, max_length=128)


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=12, max_length=128)
    role: RoleLiteral


class UpdateUserRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    role: Optional[RoleLiteral] = None
    is_active: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=12, max_length=128)


class UserListResponse(BaseModel):
    items: List[UserPublic]
    pagination: PaginationMeta


class SecurityAuditLogItem(BaseModel):
    audit_id: int
    actor_user_id: Optional[int] = None
    actor_username: Optional[str] = None
    actor_display_name: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    outcome: str
    timestamp: str
    details: Optional[str] = None


class SecurityAuditLogListResponse(BaseModel):
    items: List[SecurityAuditLogItem]
    pagination: PaginationMeta

