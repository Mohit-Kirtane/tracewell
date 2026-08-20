async function unwrap(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

function request(path, options = {}) {
  return fetch(path, { credentials: "include", ...options }).then(unwrap);
}

export function register(email, password) {
  return request("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export function login(email, password) {
  return request("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export function logout() {
  return request("/api/auth/logout", { method: "POST" });
}

export function getMe() {
  return request("/api/auth/me");
}

export function listProjects() {
  return request("/api/projects");
}

export function createProject(name) {
  return request("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export function createApiKey(projectId) {
  return request(`/api/projects/${projectId}/api-keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
}

export function listApiKeys(projectId) {
  return request(`/api/projects/${projectId}/api-keys`);
}

export function revokeApiKey(projectId, keyId) {
  return request(`/api/projects/${projectId}/api-keys/${keyId}`, { method: "DELETE" });
}

export function listTraces(projectId) {
  return request(`/api/projects/${projectId}/traces`);
}

export function getTrace(traceId) {
  return request(`/api/traces/${traceId}`);
}

export function rescoreTrace(traceId) {
  return request(`/api/traces/${traceId}/rescore`, { method: "POST" });
}

export function listEvaluators(projectId) {
  return request(`/api/projects/${projectId}/evaluators`);
}

export function createEvaluator(projectId, name, judgePromptTemplate) {
  return request(`/api/projects/${projectId}/evaluators`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, judge_prompt_template: judgePromptTemplate }),
  });
}

export function updateEvaluator(projectId, evaluatorId, active) {
  return request(`/api/projects/${projectId}/evaluators/${evaluatorId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ active }),
  });
}
