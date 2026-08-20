import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext.jsx";
import { RequireAuth } from "./components/RequireAuth.jsx";
import { DashboardLayout } from "./components/DashboardLayout.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import ProjectsPage from "./pages/ProjectsPage.jsx";
import ApiKeysPage from "./pages/ApiKeysPage.jsx";
import TracesPage from "./pages/TracesPage.jsx";
import TraceDetailPage from "./pages/TraceDetailPage.jsx";
import EvaluatorsPage from "./pages/EvaluatorsPage.jsx";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Navigate to="/projects" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        <Route
          element={
            <RequireAuth>
              <DashboardLayout />
            </RequireAuth>
          }
        >
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:projectId/api-keys" element={<ApiKeysPage />} />
          <Route path="/projects/:projectId/traces" element={<TracesPage />} />
          <Route path="/projects/:projectId/evaluators" element={<EvaluatorsPage />} />
          <Route path="/projects/:projectId/traces/:traceId" element={<TraceDetailPage />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
