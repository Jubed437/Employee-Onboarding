import type {
  Hire,
  HireCreate,
  LoginResponse,
  Persona,
  Readiness,
  SimulationClock,
  Plan,
  Task,
  TaskState,
  Recommendation,
  Risk,
} from "./types";

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
  listHires: () => request<Hire[]>("/hires"),
  createHire: (hire: HireCreate) =>
    request<Hire>("/hires", { method: "POST", body: JSON.stringify(hire) }),
  readiness: (hireId: string) => request<Readiness>(`/hires/${hireId}/readiness`),
  plan: (hireId: string) => request<Plan>(`/tasks/plans/${hireId}`),
  myTasks: (state?: TaskState) =>
    request<Task[]>(`/tasks/mine${state ? `?state=${state}` : ""}`),
  transitionTask: (taskId: string, to: TaskState, reason?: string) =>
    request<Task>(`/tasks/${taskId}/transition`, {
      method: "POST",
      body: JSON.stringify({ to, reason }),
    }),
  risks: (hireId: string) => request<Risk[]>(`/hires/${hireId}/risks`),
  recommendations: () => request<Recommendation[]>("/recommendations"),
  decideRecommendation: (id: string, decision: "approve" | "reject", comment?: string) =>
    request<Recommendation>(`/recommendations/${id}/${decision}`, {
      method: "POST",
      body: JSON.stringify({ comment }),
    }),
  streamUrl: (hireId?: string) =>
    `${API_BASE}/stream${hireId ? `?hire_id=${encodeURIComponent(hireId)}` : ""}`,
};
