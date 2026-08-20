import { Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext.jsx";
import { RequireAuth } from "./components/RequireAuth.jsx";
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
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/projects"
          element={
            <RequireAuth>
              <ProjectsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/projects/:projectId/api-keys"
          element={
            <RequireAuth>
              <ApiKeysPage />
            </RequireAuth>
          }
        />
        <Route
          path="/projects/:projectId/traces"
          element={
            <RequireAuth>
              <TracesPage />
            </RequireAuth>
          }
        />
        <Route
          path="/traces/:traceId"
          element={
            <RequireAuth>
              <TraceDetailPage />
            </RequireAuth>
          }
        />
        <Route
          path="/projects/:projectId/evaluators"
          element={
            <RequireAuth>
              <EvaluatorsPage />
            </RequireAuth>
          }
        />
      </Routes>
    </AuthProvider>
  );
}
