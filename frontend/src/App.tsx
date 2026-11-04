import { useEffect, useState } from "react";

import { api } from "./api";
import { AuthProvider } from "./auth";
import { useAuth } from "./auth-hook";
import { EmptyState, ErrorState, ScoreGauge, StatusBadge } from "./components";
import { useOnboardingStream, useSimulationClock } from "./hooks";
import type { Persona, Role } from "./types";

const navigation: Record<Role, string[]> = {
  ADMIN: ["Command center", "Approvals", "Simulation", "Audit"],
  HR: ["Command center", "Approvals", "Audit"],
  MANAGER: ["My hires", "Approvals"],
  PAYROLL: ["My queue"],
  IT: ["My queue"],
  BENEFITS: ["My queue"],
  LEARNING: ["My queue"],
  FACILITIES: ["My queue"],
  NEW_HIRE: ["My checklist"],
};

function LoginScreen() {
  const { login } = useAuth();
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.listPersonas().then(setPersonas).catch(() => setError("Could not load demo personas"));
  }, []);
  async function submit() {
    const persona = personas.find((item) => item.id === selected);
    if (!persona) return;
    try {
      await login(persona);
    } catch {
      setError("Login failed. Start the backend and try again.");
    }
  }
  return (
    <main className="login-layout">
      <section className="login-card">
        <p className="eyebrow">Employee onboarding</p>
        <h1>One clear path to day one.</h1>
        <p className="muted">Choose a synthetic demo persona to enter the orchestrator.</p>
        {error && <ErrorState message={error} />}
        <label>
          Demo persona
          <select value={selected} onChange={(event) => setSelected(event.target.value)}>
            <option value="">Select a persona</option>
            {personas.map((persona) => (
              <option key={persona.id} value={persona.id}>
                {persona.display_name} · {persona.role}
              </option>
            ))}
          </select>
        </label>
        <button className="primary-button" disabled={!selected} onClick={submit}>
          Enter workspace
        </button>
      </section>
    </main>
  );
}

function Shell() {
  const { user, logout } = useAuth();
  const { clock, error: clockError } = useSimulationClock();
  const connected = useOnboardingStream();
  const [active, setActive] = useState(navigation[user?.role ?? "ADMIN"][0]);
  if (!user) return <LoginScreen />;
  const items = navigation[user.role];
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-mark">O</div>
        <p className="sidebar-title">Orchestrator</p>
        <nav aria-label="Primary navigation">
          {items.map((item) => (
            <button
              className={active === item ? "nav-item active" : "nav-item"}
              key={item}
              onClick={() => setActive(item)}
            >
              {item}
            </button>
          ))}
        </nav>
        <button className="logout-button" onClick={logout}>Sign out</button>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Workspace</p>
            <h1>{active}</h1>
          </div>
          <div className="topbar-meta">
            <span className="clock-chip">
              <span className="live-dot" /> {clock?.now ?? clockError ?? "Loading time"}
            </span>
            <StatusBadge label={connected ? "Live" : "Offline"} tone={connected ? "good" : "neutral"} />
            <button className="avatar" aria-label="Sign out" onClick={logout}>
              {user.display_name.slice(0, 1)}
            </button>
          </div>
        </header>
        <main className="content">
          <section className="welcome-panel">
            <div>
              <p className="eyebrow">Good morning, {user.display_name.split(" ")[0]}</p>
              <h2>Keep every new hire moving.</h2>
              <p className="muted">Monitor risks, coordinate owners, and make the next best action visible.</p>
            </div>
            <ScoreGauge score={82} />
          </section>
          <section className="metric-grid">
            <Metric label="Active hires" value="3" detail="All onboarding plans" />
            <Metric label="Open risks" value="2" detail="1 needs attention" tone="warning" />
            <Metric label="Readiness" value="82%" detail="Across active hires" tone="good" />
          </section>
          <EmptyState title={`${active} is ready for the next stage`}>
            Connect the backend to load live onboarding data. Navigation is filtered for your {user.role.toLowerCase()} role.
          </EmptyState>
        </main>
      </div>
    </div>
  );
}

function Metric({ label, value, detail, tone = "neutral" }: { label: string; value: string; detail: string; tone?: string }) {
  return (
    <article className="metric-card">
      <p className="muted">{label}</p>
      <strong className={`metric-value metric-${tone}`}>{value}</strong>
      <p className="metric-detail">{detail}</p>
    </article>
  );
}

export function App() {
  return (
    <AuthProvider>
      <Shell />
    </AuthProvider>
  );
}
