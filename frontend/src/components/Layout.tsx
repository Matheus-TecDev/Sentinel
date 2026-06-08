import {
  Activity,
  Gauge,
  LogOut,
  Menu,
  Server,
  Shield,
  Users
} from "lucide-react";
import type { ReactNode } from "react";

import { useAuth } from "../auth/AuthContext";

interface LayoutProps {
  children: ReactNode;
  currentPath: string;
  navigate: (path: string) => void;
}

export function Layout({ children, currentPath, navigate }: LayoutProps) {
  const { user, logout, canManageUsers } = useAuth();

  function isActive(path: string): boolean {
    if (path === "/dashboard") return currentPath === "/" || currentPath === "/dashboard";
    return currentPath.startsWith(path);
  }

  function handleLogout(): void {
    logout();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Shield size={22} aria-hidden="true" />
          </div>
          <div>
            <strong>Sentinel</strong>
            <span>Plataforma de Observabilidade</span>
          </div>
        </div>

        <nav className="nav-list" aria-label="Principal">
          <button
            className={isActive("/dashboard") ? "nav-item active" : "nav-item"}
            onClick={() => navigate("/dashboard")}
          >
            <Gauge size={18} aria-hidden="true" />
            Dashboard
          </button>
          <button
            className={isActive("/services") ? "nav-item active" : "nav-item"}
            onClick={() => navigate("/services")}
          >
            <Server size={18} aria-hidden="true" />
            Serviços
          </button>
          {canManageUsers && (
            <button
              className={isActive("/users") ? "nav-item active" : "nav-item"}
              onClick={() => navigate("/users")}
            >
              <Users size={18} aria-hidden="true" />
              Usuários
            </button>
          )}
        </nav>

        <div className="sidebar-footer">
          <Activity size={16} aria-hidden="true" />
          <span>Preparado para integração com Prometheus</span>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div>
            <div className="eyebrow">Monitoramento corporativo</div>
            <h1>Visão Operacional</h1>
          </div>
          <div className="topbar-actions">
            <div className="user-pill">
              <Menu size={16} aria-hidden="true" />
              <span>{user?.name}</span>
              <strong>{user?.role}</strong>
            </div>
            <button className="icon-button" onClick={handleLogout} title="Sair">
              <LogOut size={18} aria-hidden="true" />
            </button>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
