const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || "";
const API_BASE_URL = configuredBaseUrl.replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status = 0, details = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

function errorMessage(status, body) {
  if (typeof body?.detail === "string") return body.detail;

  if (Array.isArray(body?.detail)) {
    const messages = body.detail
      .map((item) => item?.msg)
      .filter((item) => typeof item === "string");
    if (messages.length) return messages.join(" ");
  }

  if (status === 401) return "Your session is missing or no longer valid.";
  if (status === 403) return "Your account does not have permission for this action.";
  if (status === 502 || status === 503 || status === 504) {
    return "The Cognivault backend or its local AI runtime is unavailable.";
  }
  return `The backend returned an unexpected ${status} response.`;
}

async function request(path, { token, ...options } = {}) {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(
      "The Cognivault backend is unavailable. Check that FastAPI is running.",
      0,
    );
  }

  let body = null;
  try {
    body = await response.json();
  } catch {
    // Preserve a normalized error when a proxy/server returns non-JSON content.
  }

  if (!response.ok) {
    throw new ApiError(errorMessage(response.status, body), response.status, body);
  }

  return body;
}

export function login(username, password) {
  return request("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function getCurrentUser(token) {
  return request("/api/v1/auth/me", { token });
}

export function runAgent(token, userQuery, file = null) {
  if (file) {
    const formData = new FormData();
    formData.append("user_query", userQuery);
    formData.append("file", file);
    return request("/api/v1/agent/run", {
      method: "POST",
      token,
      body: formData,
    });
  }

  return request("/api/v1/agent/run", {
    method: "POST",
    token,
    body: JSON.stringify({ user_query: userQuery }),
  });
}

export function getHealth() {
  return request("/health");
}
