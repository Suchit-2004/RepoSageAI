
const API_BASE = "http://127.0.0.1:8000/api";

async function request(url, options = {}) {
  let response;

  try {
    response = await fetch(`${API_BASE}${url}`, options);
  } catch {
    throw new Error(
      "Cannot connect to the backend. Make sure FastAPI is running on port 8000."
    );
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || `Request failed (${response.status})`);
  }

  return data;
}

export function getHealth() {
  return request("/health");
}

export function analyzeProject(file) {
  const formData = new FormData();
  formData.append("file", file);

  return request("/projects/analyze", {
    method: "POST",
    body: formData,
  });
}

export function getDependencies() {
  return request("/dependencies");
}

export function getImpact(path) {
  return request(`/impact?path=${encodeURIComponent(path)}`);
}

export function getFunctions() {
  return request("/functions");
}

export function getFunctionImpact(name, file) {
  const params = new URLSearchParams({ name, file });
  return request(`/function-impact?${params.toString()}`);
}

export function getAIExplanation(path) {
  return request(`/ai/explanation?path=${encodeURIComponent(path)}`, {
    method: "POST",
  });
}



export async function getDependencyGraph() {
  const response = await fetch("http://127.0.0.1:8000/api/dependencies");

  if (!response.ok) {
    throw new Error("Failed to load dependency graph.");
  }

  return response.json();
}