export type PriorityLevel = "Critical" | "High" | "Medium" | "Low" | "Informational";
export type AlertStatus = "OPEN" | "UNDER_REVIEW" | "RESOLVED" | "DISMISSED";

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface HealthResponse {
  status: string;
  phase: string;
}

export type UserRole = "ADMINISTRATOR" | "SECURITY_ANALYST" | "AUDITOR";

export interface UserPublic {
  user_id: number;
  username: string;
  display_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
}

export interface LoginResponse {
  user: UserPublic;
  csrf_token: string;
  expires_at: string;
}

export interface SessionMeResponse {
  user: UserPublic;
  session_expires_at: string;
}

export interface UserListResponse {
  items: UserPublic[];
  pagination: PaginationMeta;
}

export interface CreateUserPayload {
  username: string;
  display_name: string;
  password: string;
  role: UserRole;
}

export interface UpdateUserPayload {
  display_name?: string;
  role?: UserRole;
  is_active?: boolean;
}

export interface SecurityAuditLogItem {
  audit_id: number;
  actor_user_id: number | null;
  actor_username: string | null;
  actor_display_name: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  outcome: string;
  timestamp: string;
  details: string | null;
}

export interface SecurityAuditLogListResponse {
  items: SecurityAuditLogItem[];
  pagination: PaginationMeta;
}

export interface TopEmployeeItem {
  employee_id: string;
  role: string | null;
  department: string | null;
  alert_count: number;
  max_risk_score: number;
  max_anomaly_score: number;
}

export interface RecentInvestigationItem {
  history_id: number;
  alert_id: number;
  employee_id: string;
  previous_status: string;
  new_status: string;
  analyst_note: string | null;
  changed_at: string;
  actor_user_id?: number | null;
  actor_username?: string | null;
  actor_display_name?: string | null;
  actor_role?: string | null;
}

export interface DashboardSummaryResponse {
  unique_employees: number;
  total_observations: number;
  flagged_observations: number;
  total_alerts: number;
  open_alerts: number;
  critical_open_alerts?: number;
  under_review_alerts: number;
  resolved_alerts: number;
  dismissed_alerts: number;
  alerts_by_priority: Record<string, number>;
  top_employees: TopEmployeeItem[];
  recent_investigations: RecentInvestigationItem[];
  model_version: string;
  coverage_start_date: string | null;
  coverage_end_date: string | null;
}

export interface DailyTrendPoint {
  activity_date: string;
  total_observations: number;
  flagged_count: number;
  high_critical_count: number;
  avg_risk_score: number;
}

export interface DashboardTrendsResponse {
  items: DailyTrendPoint[];
}

export interface EmployeeSummary {
  employee_id: string;
  role: string | null;
  department: string | null;
  functional_unit: string | null;
  first_activity_date: string;
  last_activity_date: string;
  observation_count: number;
  max_risk_score: number;
  highest_priority?: PriorityLevel | string | null;
  alert_count: number;
  open_alert_count: number;
}

export interface EmployeeListResponse {
  items: EmployeeSummary[];
  pagination: PaginationMeta;
}

export interface EmployeeDetailResponse extends EmployeeSummary {
  avg_risk_score: number;
}

export interface EmployeeObservationItem {
  observation_id: number;
  employee_id: string;
  activity_date: string;
  login_count: number;
  after_hours_login_count: number;
  http_activity_count: number;
  email_activity_count: number;
  file_activity_count: number;
  usb_activity_count: number;
  total_activity_count: number;
  after_hours_ratio: number;
  is_weekend: number;
  anomaly_score: number;
  risk_score: number;
  priority: PriorityLevel;
  alert_id: number | null;
  alert_status: AlertStatus | null;
}

export interface EmployeeHistoryResponse {
  employee_id: string;
  items: EmployeeObservationItem[];
  pagination: PaginationMeta;
}

export interface AlertExplanationItem {
  explanation_id: number;
  feature_name: string;
  activity_label: string;
  current_value: number;
  historical_mean: number | null;
  historical_std: number | null;
  deviation: number | null;
  direction: string;
  historical_obs_count: number;
  evidence_description: string;
  investigation_recommendation: string;
}

export interface AlertSummaryItem {
  alert_id: number;
  observation_id: number;
  employee_id: string;
  role: string | null;
  department: string | null;
  activity_date: string;
  anomaly_score: number;
  risk_score: number;
  priority: PriorityLevel;
  status: AlertStatus;
  model_version: string;
  activity_summary?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AlertListResponse {
  items: AlertSummaryItem[];
  pagination: PaginationMeta;
}

export interface AlertDetailResponse extends AlertSummaryItem {
  functional_unit: string | null;
  login_count: number;
  after_hours_login_count: number;
  http_activity_count: number;
  email_activity_count: number;
  file_activity_count: number;
  usb_activity_count: number;
  total_activity_count: number;
  after_hours_ratio: number;
  is_weekend: number;
  explanations: AlertExplanationItem[];
}

export interface InvestigationHistoryItem {
  history_id: number;
  alert_id: number;
  previous_status: string;
  new_status: string;
  analyst_note: string | null;
  changed_at: string;
  actor_user_id?: number | null;
  actor_username?: string | null;
  actor_display_name?: string | null;
  actor_role?: string | null;
}

export interface AlertHistoryResponse {
  alert_id: number;
  items: InvestigationHistoryItem[];
}

export interface AlertStatusUpdateRequest {
  new_status: AlertStatus;
  analyst_note?: string | null;
}

export interface ModelInfoResponse {
  model_version: string;
  algorithm: string;
  scaled: boolean;
  feature_count: number;
  feature_names: string[];
  hyperparameters: {
    n_estimators: number;
    max_samples: number;
    contamination: string;
    random_state: number;
  };
  calibrated_thresholds: Record<string, number>;
  disclaimer: string;
}

export interface ThresholdEvaluationMetrics {
  threshold: number;
  tp: number;
  fp: number;
  tn: number;
  fn: number;
  precision: number;
  recall: number;
  f1: number;
  fpr: number;
  specificity: number;
  total_alerts: number;
  alert_rate_pct: number;
  avg_alerts_per_date: number;
}

export interface ModelMetricsResponse {
  model_version: string;
  metric_definitions: Record<string, string>;
  validation_ablation: Record<
    string,
    {
      n_samples: number;
      n_positives: number;
      base_positive_rate: number;
      roc_auc: number;
      pr_auc: number;
      fit_seconds: number;
      feature_count: number;
    }
  >;
  validation_trapezoidal_pr_auc: number | null;
  validation_threshold_metrics: Record<string, ThresholdEvaluationMetrics>;
  held_out_test_summary: {
    n_samples: number;
    n_positives: number;
    base_positive_rate: number;
    roc_auc: number;
    average_precision: number;
    trapezoidal_pr_auc: number | null;
  };
  held_out_test_threshold_metrics: Record<string, ThresholdEvaluationMetrics>;
}

export interface DataSummaryResponse {
  source_partition: string;
  unique_employees: number;
  observation_count: number;
  unique_dates: number;
  date_min: string | null;
  date_max: string | null;
  alert_count: number;
  explanation_count: number;
  investigation_history_count: number;
  note: string;
}

