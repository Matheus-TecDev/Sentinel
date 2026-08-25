import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { AuthProvider } from "./auth/AuthContext";
import type { DashboardSummary, User, UserRole } from "./types";

const now = "2026-08-24T12:00:00.000Z";

function user(role: UserRole): User {
  return {
    id: 1,
    name: "Ana Silva",
    email: "ana@example.com",
    role,
    is_active: true,
    created_at: now,
    updated_at: now
  };
}

function service(id: number, name: string, current_status: "online" | "degraded" | "offline") {
  return {
    id,
    name,
    description: null,
    environment: "production" as const,
    healthcheck_url: `https://example.com/${id}/health`,
    owner: "SRE",
    responsible_id: null,
    is_active: true,
    created_at: now,
    updated_at: now,
    current_status,
    last_http_status_code: current_status === "offline" ? 503 : 200,
    last_response_time_ms: current_status === "degraded" ? 950 : 120,
    last_checked_at: now
  };
}

const dashboardSummary: DashboardSummary = {
  total_services: 3,
  online_services: 1,
  offline_services: 1,
  degraded_services: 1,
  inactive_services: 0,
  average_response_time_ms: 397,
  overall_uptime_percent: 66.67,
  open_incidents: 1,
  failures_last_24h: 1,
  recent_failures: [
    {
      id: 10,
      service_id: 3,
      status: "offline",
      http_status_code: 503,
      response_time_ms: null,
      error_message: "Connection refused",
      checked_at: now
    }
  ],
  recent_incidents: [
    {
      id: 20,
      service_id: 3,
      service_name: "Billing API",
      status: "open",
      started_at: now,
      resolved_at: null,
      duration_seconds: null,
      reason: "HTTP 503",
      last_error_message: "Connection refused",
      created_at: now,
      updated_at: now
    }
  ],
  recent_notifications: [],
  failed_notifications: [],
  unstable_services: [],
  slowest_services: [],
  services: [
    service(1, "Gateway API", "online"),
    service(2, "Search API", "degraded"),
    service(3, "Billing API", "offline")
  ]
};

function mockDashboardRequest(): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(dashboardSummary), { status: 200 }))
  );
}

function renderAuthenticatedApp(role: UserRole, path = "/dashboard"): void {
  localStorage.setItem("sentinel_token", "test-token");
  localStorage.setItem("sentinel_user", JSON.stringify(user(role)));
  window.history.pushState(null, "", path);

  render(
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}

describe("App dashboard", () => {
  beforeEach(() => {
    mockDashboardRequest();
  });

  it("renders monitored services with online, degraded and offline states", async () => {
    renderAuthenticatedApp("ADMIN");

    const gatewayRow = await screen.findByRole("row", { name: /Gateway API/i });
    const searchRow = screen.getByRole("row", { name: /Search API/i });
    const billingRow = screen.getByRole("row", { name: /Billing API/i });

    expect(within(gatewayRow).getByText("Online")).toBeTruthy();
    expect(within(searchRow).getByText("Degradado")).toBeTruthy();
    expect(within(billingRow).getByText("Offline")).toBeTruthy();
  });

  it("shows recent incident context on the operational dashboard", async () => {
    renderAuthenticatedApp("ADMIN");

    const incidentsPanel = await screen.findByText("Incidentes recentes");
    const panel = incidentsPanel.closest(".panel");

    expect(panel).not.toBeNull();
    expect(within(panel as HTMLElement).getByText("Billing API")).toBeTruthy();
    expect(within(panel as HTMLElement).getByText("HTTP 503")).toBeTruthy();
    expect(within(panel as HTMLElement).getByText("Aberto")).toBeTruthy();
  });

  it("prevents a viewer from accessing user management", async () => {
    renderAuthenticatedApp("VIEWER", "/users");

    expect(await screen.findByText("Dashboard operacional")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Usuários" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Usuários" })).toBeNull();
  });
});
