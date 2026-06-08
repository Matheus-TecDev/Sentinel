import { Activity, ChevronLeft, Gauge, LogOut, Server, Shield, Users } from "lucide-react";
import { useState, type ReactNode } from "react";

import { useAuth } from "../auth/AuthContext";
import { userRoleLabel } from "../utils";

interface LayoutProps {
  children: ReactNode;
  currentPath: string;
  navigate: (path: string) => void;
}

export function Layout({ children, currentPath, navigate }: LayoutProps) {
  const { user, logout, canManageUsers, canManageServices } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  function isActive(path: string): boolean {
    if (path === "/dashboard") return currentPath === "/" || currentPath === "/dashboard";
    return currentPath.startsWith(path);
  }

  function handleLogout(): void {
    logout();
    navigate("/login");
  }

  return (
    <div className={sidebarOpen ? "app-shell" : "app-shell sidebar-collapsed"}>
      <aside className="sidebar">
        <div className="brand">
          <button
            className="brand-mark"
            onClick={() => !sidebarOpen && setSidebarOpen(true)}
            title={sidebarOpen ? "Sentinel" : "Expandir menu"}
            type="button"
          >
            <Shield size={22} aria-hidden="true" />
          </button>
          {sidebarOpen && (
            <>
              <div className="brand-copy">
                <strong>Sentinel</strong>
                <span>Observabilidade corporativa</span>
              </div>
              <button className="sidebar-toggle" onClick={() => setSidebarOpen(false)} title="Recolher menu" type="button">
                <ChevronLeft size={18} aria-hidden="true" />
              </button>
            </>
          )}
        </div>

        <nav className="nav-list" aria-label="Principal">
          <button
            className={isActive("/dashboard") ? "nav-item active" : "nav-item"}
            onClick={() => navigate("/dashboard")}
            title="Dashboard"
            type="button"
          >
            <Gauge size={18} aria-hidden="true" />
            {sidebarOpen && <span>Dashboard</span>}
          </button>
          <button
            className={isActive("/services") ? "nav-item active" : "nav-item"}
            onClick={() => navigate("/services")}
            title="Serviços"
            type="button"
          >
            <Server size={18} aria-hidden="true" />
            {sidebarOpen && <span>Serviços</span>}
          </button>
          {canManageServices && (
            <button
              className={isActive("/responsibles") ? "nav-item active" : "nav-item"}
              onClick={() => navigate("/responsibles")}
              title="Responsáveis"
              type="button"
            >
              <Users size={18} aria-hidden="true" />
              {sidebarOpen && <span>Responsáveis</span>}
            </button>
          )}
          {canManageUsers && (
            <button
              className={isActive("/users") ? "nav-item active" : "nav-item"}
              onClick={() => navigate("/users")}
              title="Usuários"
              type="button"
            >
              <Users size={18} aria-hidden="true" />
              {sidebarOpen && <span>Usuários</span>}
            </button>
          )}
        </nav>

        {sidebarOpen && (
          <div className="sidebar-footer">
            <Activity size={16} aria-hidden="true" />
            <span>Monitoramento ativo</span>
          </div>
        )}
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div>
            <div className="eyebrow">Operação</div>
            <h1>Visão operacional</h1>
          </div>
          <div className="topbar-actions">
            <div className="user-pill">
              <span>Olá, {user?.name}</span>
              <strong>{userRoleLabel(user?.role ?? "")}</strong>
            </div>
            <button className="logout-button" onClick={handleLogout} title="Sair" aria-label="Sair" type="button">
              <LogOut size={18} aria-hidden="true" />
            </button>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
