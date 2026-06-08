export type UserRole = "ADMIN" | "OPERATOR" | "VIEWER";
export type ServiceEnvironment = "dev" | "staging" | "production";
export type HealthStatus = "online" | "offline" | "degraded";

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MonitoredService {
  id: number;
  name: string;
  description: string | null;
  environment: ServiceEnvironment;
  healthcheck_url: string;
  owner: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  current_status: HealthStatus | null;
  last_http_status_code: number | null;
  last_response_time_ms: number | null;
  last_checked_at: string | null;
}

export interface HealthCheckResult {
  id: number;
  service_id: number;
  status: HealthStatus;
  http_status_code: number | null;
  response_time_ms: number | null;
  error_message: string | null;
  checked_at: string;
}

export interface ServiceDetail extends MonitoredService {
  average_response_time_ms: number | null;
  uptime_percent: number;
  recent_checks: HealthCheckResult[];
  recent_failures: HealthCheckResult[];
}

export interface DashboardSummary {
  total_services: number;
  online_services: number;
  offline_services: number;
  degraded_services: number;
  inactive_services: number;
  average_response_time_ms: number | null;
  overall_uptime_percent: number;
  recent_failures: HealthCheckResult[];
  services: MonitoredService[];
}

export interface ServicePayload {
  name: string;
  description: string | null;
  environment: ServiceEnvironment;
  healthcheck_url: string;
  owner: string;
  is_active: boolean;
}
