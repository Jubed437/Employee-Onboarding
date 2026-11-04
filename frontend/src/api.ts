import type { LoginResponse, Persona, SimulationClock } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem("onboarding-token");
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listPersonas: () => request<Persona[]>("/auth/personas"),
  login: (userId: string) =>
    request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),
  clock: () => request<SimulationClock>("/sim/clock"),
  streamUrl: (hireId?: string) =>
    `${API_BASE}/stream${hireId ? `?hire_id=${encodeURIComponent(hireId)}` : ""}`,
};
