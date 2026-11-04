import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { api } from "./api";
import { AuthProvider } from "./auth";
import { useAuth } from "./auth-hook";
import { EmptyState, ErrorState, ScoreGauge, StatusBadge } from "./components";
import { useOnboardingStream, useSimulationClock } from "./hooks";
import type { Hire, HireCreate, Persona, Readiness, Role } from "./types";

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

function HiresDashboard({ onSelect, onNew }: { onSelect: (hire: Hire) => void; onNew: () => void }) {
  const [hires, setHires] = useState<Hire[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.listHires().then(setHires).catch(() => setError("Could not load hires"));
  }, []);
  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Portfolio</p>
          <h2>Active hires</h2>
        </div>
        <button className="primary-button compact-button" onClick={onNew}>New hire</button>
      </div>
      {error && <ErrorState message={error} />}
      {!error && hires.length === 0 && (
        <EmptyState title="No hires yet">Create a hire to generate a deterministic onboarding plan.</EmptyState>
      )}
      {hires.length > 0 && (
        <div className="hire-table">
          <div className="hire-table-row hire-table-header">
            <span>Hire</span><span>Join date</span><span>Readiness</span><span>Plan</span>
          </div>
          {hires.map((hire) => (
            <button className="hire-table-row hire-row-button" key={hire.id} onClick={() => onSelect(hire)}>
              <span><strong>{hire.full_name}</strong><small>{hire.email}</small></span>
              <span>{formatDate(hire.join_date)}</span>
              <span><StatusBadge label="View score" tone="neutral" /></span>
              <span className="row-arrow">View overview →</span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

function CreateHire({ onCreated, onCancel }: { onCreated: (hire: Hire) => void; onCancel: () => void }) {
  const [form, setForm] = useState<HireCreate>({
    full_name: "", email: "", job_title: "", department: "", join_date: "",
    work_state: "", is_experienced: false, is_remote: false, profile_key: "india_full_time",
  });
  const [error, setError] = useState<string | null>(null);
  const update = (key: keyof HireCreate, value: string | boolean) =>
    setForm((current) => ({ ...current, [key]: value }));
  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      onCreated(await api.createHire(form));
    } catch {
      setError("Could not create hire. Check the fields and try again.");
    }
  }
  return (
    <section className="form-card">
      <div className="section-heading"><div><p className="eyebrow">New onboarding</p><h2>Create a hire</h2></div></div>
      {error && <ErrorState message={error} />}
      <form className="hire-form" onSubmit={submit}>
        <Field label="Full name" value={form.full_name} onChange={(value) => update("full_name", value)} required />
        <Field label="Email" type="email" value={form.email} onChange={(value) => update("email", value)} required />
        <Field label="Job title" value={form.job_title} onChange={(value) => update("job_title", value)} required />
        <Field label="Department" value={form.department} onChange={(value) => update("department", value)} required />
        <Field label="Join date" type="date" value={form.join_date} onChange={(value) => update("join_date", value)} required />
        <Field label="Work state" value={form.work_state} onChange={(value) => update("work_state", value)} required />
        <label className="check-field"><input type="checkbox" checked={form.is_experienced} onChange={(event) => update("is_experienced", event.target.checked)} /> Experienced hire</label>
        <label className="check-field"><input type="checkbox" checked={form.is_remote} onChange={(event) => update("is_remote", event.target.checked)} /> Remote hire</label>
        <div className="form-actions"><button type="button" className="secondary-button" onClick={onCancel}>Cancel</button><button className="primary-button compact-button">Generate plan</button></div>
      </form>
    </section>
  );
}

function HireOverview({ hire, onBack }: { hire: Hire; onBack: () => void }) {
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.readiness(hire.id).then(setReadiness).catch(() => setError("Readiness is not available yet"));
  }, [hire.id]);
  return (
    <section>
      <button className="back-button" onClick={onBack}>← All hires</button>
      <div className="section-heading">
        <div><p className="eyebrow">Hire overview</p><h2>{hire.full_name}</h2><p className="muted">{hire.email} · Joining {formatDate(hire.join_date)}</p></div>
        {readiness && <StatusBadge label={readiness.band.replace("_", " ")} tone={readiness.band === "READY" ? "good" : "warning"} />}
      </div>
      {error && <ErrorState message={error} />}
      {readiness ? (
        <div className="overview-grid">
          <article className="overview-score"><ScoreGauge score={readiness.score} /><h3>Readiness score</h3><p className="muted">Last updated {formatDateTime(readiness.ts)}</p></article>
          <article className="breakdown-card"><h3>Score breakdown</h3>{Object.entries(readiness.breakdown).map(([key, value]) => <div className="breakdown-row" key={key}><span>{key}</span><strong>{Math.round(value * 100)}%</strong><span className="mini-bar"><i style={{ width: `${value * 100}%` }} /></span></div>)}</article>
          <article className="drivers-card"><h3>Why did it change?</h3>{readiness.drivers.length ? <ul>{readiness.drivers.map((driver) => <li key={driver}>{driver}</li>)}</ul> : <p className="muted">No readiness drivers recorded.</p>}</article>
        </div>
      ) : !error ? <div className="loading-panel">Loading readiness…</div> : null}
    </section>
  );
}

function Field({ label, value, onChange, type = "text", required = false }: { label: string; value: string; onChange: (value: string) => void; type?: string; required?: boolean }) {
  return <label><span>{label}</span><input type={type} value={value} required={required} onChange={(event) => onChange(event.target.value)} /></label>;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`));
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function Shell() {
  const { user, logout } = useAuth();
  const { clock, error: clockError } = useSimulationClock();
  const connected = useOnboardingStream();
  const [active, setActive] = useState(navigation[user?.role ?? "ADMIN"][0]);
  const [selectedHire, setSelectedHire] = useState<Hire | null>(null);
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
              onClick={() => { setActive(item); setSelectedHire(null); }}
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
          {active === "My hires" || active === "Command center" ? (
            selectedHire ? <HireOverview hire={selectedHire} onBack={() => setSelectedHire(null)} /> :
            <HiresDashboard onSelect={setSelectedHire} onNew={() => setActive("New hire")} />
          ) : active === "New hire" ? (
            <CreateHire onCreated={(hire) => { setSelectedHire(hire); setActive(user.role === "ADMIN" ? "Command center" : "My hires"); }} onCancel={() => setActive("My hires")} />
          ) : (
            <>
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
            </>
          )}
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
