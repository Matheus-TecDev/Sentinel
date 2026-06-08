import { useEffect, useState } from "react";

import { useAuth } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { ServiceDetailPage } from "./pages/ServiceDetail";
import { ServiceFormPage } from "./pages/ServiceForm";
import { ServicesPage } from "./pages/Services";
import { UsersPage } from "./pages/Users";

export interface PageProps {
  navigate: (path: string) => void;
}

function getPath(): string {
  return window.location.pathname || "/dashboard";
}

export default function App() {
  const auth = useAuth();
  const [path, setPath] = useState(getPath);

  useEffect(() => {
    const onPopState = () => setPath(getPath());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  function navigate(nextPath: string): void {
    window.history.pushState(null, "", nextPath);
    setPath(nextPath);
  }

  if (!auth.isAuthenticated) {
    return <Login navigate={navigate} />;
  }

  const serviceEditMatch = path.match(/^\/services\/(\d+)\/edit$/);
  const serviceDetailMatch = path.match(/^\/services\/(\d+)$/);

  let page = <Dashboard navigate={navigate} />;
  if (path === "/services") page = <ServicesPage navigate={navigate} />;
  if (path === "/services/new") page = <ServiceFormPage mode="create" navigate={navigate} />;
  if (serviceEditMatch) {
    page = <ServiceFormPage mode="edit" serviceId={Number(serviceEditMatch[1])} navigate={navigate} />;
  }
  if (serviceDetailMatch) {
    page = <ServiceDetailPage serviceId={Number(serviceDetailMatch[1])} navigate={navigate} />;
  }
  if (path === "/users") {
    page = auth.canManageUsers ? <UsersPage /> : <Dashboard navigate={navigate} />;
  }
  if (path === "/login") {
    page = <Dashboard navigate={navigate} />;
  }

  return (
    <Layout currentPath={path} navigate={navigate}>
      {page}
    </Layout>
  );
}
