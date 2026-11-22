import { clearAuth, getToken, saveSession } from "./storage";

export const API_URL = import.meta.env.VITE_API_URL;

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = await getToken();
  return fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...options.headers,
      ...(token
        ? {
            Authorization: `Bearer ${token}`,
          }
        : {}),
    },
  });
}

// Set a key (+ model), or omit apiKey to change just the model when a key already exists. Never returns the raw key back.
export async function setOpenaiKey(apiKey: string | undefined, model: string) {
  const res = await apiFetch("/auth/openai-key", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: apiKey, model }),
  });
  const data = await res.json();
  return { ok: res.ok, data };
}

export async function clearOpenaiKey() {
  const res = await apiFetch("/auth/openai-key", { method: "DELETE" });
  const data = await res.json();
  return { ok: res.ok, data };
}

// After Firebase signs someone in: load (GET) or create (PATCH) their profile and keep it for the UI.
export async function startSession(uid: string, options: RequestInit = {}) {
  const res = await apiFetch("/auth/profile", options);
  if (!res.ok) {
    clearAuth();
    throw new Error(
      res.status === 404
        ? "No profile found for this account. Please sign up again."
        : "Couldn't load your profile. Please try again.",
    );
  }
  saveSession({ ...(await res.json()), id: uid });
}
