import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import { api } from "./api";
import { AuthProvider } from "./auth";
import { useAuth } from "./auth-hook";
import { EmptyState, ErrorState, ScoreGauge, StatusBadge } from "./components";
import { useOnboardingStream, useSimulationClock } from "./hooks";
import type {
  Hire,
  HireCreate,
  Persona,
  Readiness,
  Role,
  Task,
  TaskState,
  Risk,
  Recommendation,
  TimelineEvent,
  Notification,
} from "./types";

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

function HireOverview({ hire, onBack, onPlan, onRisks, onGraph }: { hire: Hire; onBack: () => void; onPlan: () => void; onRisks: () => void; onGraph: () => void }) {
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
        <div className="heading-actions">
          <div className="heading-actions"><button className="secondary-button" onClick={onPlan}>Plan</button><button className="secondary-button" onClick={onRisks}>Risks</button><button className="secondary-button" onClick={onGraph}>Graph</button></div>
          {readiness && <StatusBadge label={readiness.band.replace("_", " ")} tone={readiness.band === "READY" ? "good" : "warning"} />}
        </div>
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

function PlanView({ hire, onBack }: { hire: Hire; onBack: () => void }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selected, setSelected] = useState<Task | null>(null);
  const [filter, setFilter] = useState<TaskState | "ALL">("ALL");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.plan(hire.id).then((plan) => setTasks(plan.tasks)).catch(() => setError("Could not load the onboarding plan"));
  }, [hire.id]);
  const visible = filter === "ALL" ? tasks : tasks.filter((task) => task.state === filter);
  return (
    <section>
      <button className="back-button" onClick={onBack}>← {hire.full_name} overview</button>
      <div className="section-heading"><div><p className="eyebrow">Onboarding plan</p><h2>Task plan</h2></div><select className="filter-select" value={filter} onChange={(event) => setFilter(event.target.value as TaskState | "ALL")}><option value="ALL">All states</option>{["READY", "IN_PROGRESS", "BLOCKED", "REJECTED", "DONE", "SKIPPED"].map((state) => <option key={state}>{state}</option>)}</select></div>
      {error && <ErrorState message={error} />}
      {!error && tasks.length === 0 && <div className="loading-panel">Loading plan…</div>}
      {tasks.length > 0 && <div className="task-table"><div className="task-row task-header"><span>ID</span><span>Task</span><span>Owner</span><span>Due</span><span>State</span></div>{visible.map((task) => <button className="task-row task-button" key={task.id} onClick={() => setSelected(task)}><span className="task-key">{task.template_key}</span><span><strong>{task.title}</strong>{task.is_critical && <small>Critical gate</small>}</span><span>{task.owner_role}</span><span>{formatDate(task.due_date)}</span><StatusBadge label={task.state.replace("_", " ")} tone={stateTone(task.state)} /></button>)}</div>}
      {selected && <TaskDrawer task={selected} onClose={() => setSelected(null)} onUpdated={(updated) => { setTasks((current) => current.map((task) => task.id === updated.id ? updated : task)); setSelected(updated); }} />}
    </section>
  );
}

function TaskDrawer({ task, onClose, onUpdated }: { task: Task; onClose: () => void; onUpdated: (task: Task) => void }) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  async function transition(to: TaskState) {
    try {
      onUpdated(await api.transitionTask(task.id, to, reason || undefined));
      setReason("");
    } catch {
      setError("That transition is not available for the current role or state.");
    }
  }
  return <aside className="drawer" aria-label="Task details"><button className="drawer-close" onClick={onClose}>×</button><p className="eyebrow">{task.template_key}</p><h2>{task.title}</h2><StatusBadge label={task.state.replace("_", " ")} tone={stateTone(task.state)} /><dl className="task-details"><div><dt>Owner</dt><dd>{task.owner_role}</dd></div><div><dt>Due</dt><dd>{formatDate(task.due_date)}</dd></div><div><dt>Duration</dt><dd>{task.duration_days} business days</dd></div></dl>{error && <ErrorState message={error} />}{["REJECTED", "BLOCKED"].includes(task.state) && <label><span>Reason</span><textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Explain the change" required /></label>}<div className="drawer-actions">{task.state === "READY" && <button className="primary-button compact-button" onClick={() => transition("IN_PROGRESS")}>Start</button>}{task.state === "IN_PROGRESS" && <><button className="primary-button compact-button" onClick={() => transition("DONE")}>Complete</button><button className="secondary-button" onClick={() => transition("REJECTED")}>Reject</button></>}{task.state === "REJECTED" && <button className="primary-button compact-button" onClick={() => transition("IN_PROGRESS")}>Resubmit</button>}</div></aside>;
}

function QueueView() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.myTasks().then(setTasks).catch(() => setError("Could not load your task queue"));
  }, []);
  return <section><div className="section-heading"><div><p className="eyebrow">Owner queue</p><h2>Tasks assigned to your role</h2></div></div>{error && <ErrorState message={error} />}{tasks.length === 0 && !error ? <EmptyState title="Queue is clear">No tasks are currently assigned to you.</EmptyState> : <div className="task-table">{tasks.map((task) => <div className="task-row" key={task.id}><span className="task-key">{task.template_key}</span><span><strong>{task.title}</strong></span><span>{task.owner_role}</span><span>{formatDate(task.due_date)}</span><StatusBadge label={task.state.replace("_", " ")} tone={stateTone(task.state)} /></div>)}</div>}</section>;
}

function RisksView({ hire }: { hire: Hire }) {
  const [risks, setRisks] = useState<Risk[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.risks(hire.id).then(setRisks).catch(() => setError("Could not load risks")); }, [hire.id]);
  return <section><p className="eyebrow">Risk monitor</p><h2>{hire.full_name} risks</h2>{error && <ErrorState message={error} />}{risks.length === 0 && !error ? <EmptyState title="No open risks">This onboarding plan is currently on track.</EmptyState> : <div className="risk-list">{risks.map((risk) => <article className={`risk-card risk-${risk.level.toLowerCase()}`} key={risk.id}><div className="risk-card-heading"><div><StatusBadge label={risk.level} tone="warning" /><h3>Task {risk.task_id}</h3></div><strong>{risk.slack_days} days slack</strong></div><p className="muted">Predicted breach: {formatDate(risk.predicted_breach_date)}</p><p>Reasons: {risk.reason_codes.join(", ") || "Schedule pressure"}</p>{risk.root_cause_task_id && <p><strong>Root cause:</strong> {risk.root_cause_task_id}</p>}<div className="impact-tags">{(risk.impact.outcome_tags ?? []).map((tag) => <span key={tag}>{tag}</span>)}</div></article>)}</div>}</section>;
}

function ApprovalsView() {
  const [items, setItems] = useState<Recommendation[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.recommendations().then(setItems).catch(() => setError("Could not load approvals")); }, []);
  async function decide(id: string, decision: "approve" | "reject") {
    try { await api.decideRecommendation(id, decision); setItems((current) => current.filter((item) => item.id !== id)); } catch { setError("Approval could not be recorded"); }
  }
  return <section><p className="eyebrow">Governance</p><h2>Pending approvals</h2>{error && <ErrorState message={error} />}{items.length === 0 && !error ? <EmptyState title="No pending approvals">Recommendations needing your decision will appear here.</EmptyState> : <div className="approval-list">{items.map((item) => <article className="approval-card" key={item.id}><div className="risk-card-heading"><div><StatusBadge label={item.tier.replaceAll("_", " ")} tone="neutral" /><h3>{item.action_type.replaceAll("_", " ")}</h3></div><span>Rank {item.rank}</span></div><p>{item.rationale}</p><p className="muted">Simulated slack: {item.simulated_outcome.new_slack_days ?? "—"} days · {item.simulated_outcome.resolves_breach ? "Resolves breach" : "Does not fully resolve"}</p><div className="drawer-actions"><button className="primary-button compact-button" onClick={() => decide(item.id, "approve")}>Approve</button><button className="secondary-button" onClick={() => decide(item.id, "reject")}>Reject</button></div></article>)}</div>}</section>;
}

function GraphView({ hire }: { hire: Hire }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [edges, setEdges] = useState<{ from: string; to: string }[]>([]);
  useEffect(() => { api.plan(hire.id).then((plan) => { setTasks(plan.tasks); setEdges(plan.edges); }); }, [hire.id]);
  const layout = useMemo(() => {
    const incoming = new Map(tasks.map((task) => [task.id, [] as string[]]));
    edges.forEach(({ from, to }) => {
      incoming.get(to)?.push(from);
    });
    const levels = new Map<string, number>();
    function level(taskId: string, trail = new Set<string>()): number {
      const current = levels.get(taskId);
      if (current !== undefined) return current;
      if (trail.has(taskId)) return 0;
      const parents = incoming.get(taskId) ?? [];
      const next = parents.length === 0
        ? 0
        : Math.max(...parents.map((parent) => level(parent, new Set(trail).add(taskId)) + 1));
      levels.set(taskId, next);
      return next;
    }
    tasks.forEach((task) => level(task.id));
    const rows = new Map<number, number>();
    const positions = new Map<string, { x: number; y: number }>();
    tasks.forEach((task) => {
      const column = levels.get(task.id) ?? 0;
      const row = rows.get(column) ?? 0;
      rows.set(column, row + 1);
      positions.set(task.id, { x: column * 250 + 20, y: row * 135 + 20 });
    });
    const columns = Math.max(1, ...Array.from(levels.values())) + 1;
    const height = Math.max(220, ...Array.from(rows.values()).map((row) => row * 135 + 20));
    return { height, width: columns * 250, positions };
  }, [tasks, edges]);
  return (
    <section>
      <p className="eyebrow">Dependency graph</p>
      <h2>Onboarding flow</h2>
      <div className="graph-legend">
        <span>● Ready</span><span>● In progress</span><span>● Done</span><span>● Blocked</span>
        <span className="graph-direction">Arrow direction: prerequisite → dependent task</span>
      </div>
      <div className="graph-board">
        {tasks.length === 0 ? <EmptyState title="No graph data">This hire has no generated tasks.</EmptyState> : (
          <div className="graph-canvas" style={{ height: layout.height, minWidth: layout.width }}>
            <svg className="graph-lines" width={layout.width} height={layout.height} aria-label={`${edges.length} dependency connections`}>
              <defs>
                <marker id="graph-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <path d="M0,0 L8,4 L0,8 z" />
                </marker>
              </defs>
              {edges.map(({ from, to }) => {
                const source = layout.positions.get(from);
                const target = layout.positions.get(to);
                if (!source || !target) return null;
                return <path className="graph-line" key={`${from}-${to}`} d={`M ${source.x + 190} ${source.y + 52} C ${source.x + 225} ${source.y + 52}, ${target.x - 35} ${target.y + 52}, ${target.x} ${target.y + 52}`} markerEnd="url(#graph-arrow)" />;
              })}
            </svg>
            {tasks.map((task) => {
              const position = layout.positions.get(task.id) ?? { x: 20, y: 20 };
              return <div className={`graph-node node-${task.state.toLowerCase()}`} style={{ left: position.x, top: position.y }} key={task.id}><strong>{task.template_key}</strong><small>{task.title}</small><em>{task.state.replace("_", " ")}</em></div>;
            })}
          </div>
        )}
      </div>
      <p className="graph-edges">{edges.length} dependency connections</p>
    </section>
  );
}

function NewHireView() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.myTasks().then(setTasks).catch(() => setError("Could not load your checklist"));
  }, []);
  const completed = tasks.filter((task) => task.state === "DONE" || task.state === "SKIPPED").length;
  return <section><p className="eyebrow">Your onboarding</p><h2>Your checklist</h2><p className="muted">Complete each step to keep your first day on track.</p>{error && <ErrorState message={error} />}{tasks.length > 0 && <><div className="checklist-progress"><strong>{completed} of {tasks.length} complete</strong><span className="mini-bar"><i style={{ width: `${(completed / tasks.length) * 100}%` }} /></span></div><div className="checklist">{tasks.map((task) => <div className="checklist-item" key={task.id}><span className={`check-icon ${task.state === "DONE" ? "checked" : ""}`}>{task.state === "DONE" ? "✓" : "○"}</span><div><strong>{task.title}</strong><small>{task.state.replace("_", " ")} · Due {formatDate(task.due_date)}</small></div></div>)}</div></>}</section>;
}

function AdminView({ mode }: { mode: "Simulation" | "Audit" }) {
  const [collapsed, setCollapsed] = useState(false);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  async function advance(days: number) {
    try { await api.advanceClock(days); setMessage(`Advanced simulation by ${days} day${days === 1 ? "" : "s"}`); } catch { setMessage("Simulation action failed"); }
  }
  async function reset() {
    try { await api.reset(); setMessage("Scenario reset"); } catch { setMessage("Reset failed"); }
  }
  useEffect(() => {
    api.audit().then(setEvents).catch(() => setMessage("Could not load audit log"));
    api.notifications().then(setNotifications).catch(() => setMessage("Could not load outbox"));
  }, []);
  return <section><div className="section-heading"><div><p className="eyebrow">Admin controls</p><h2>{mode}</h2></div><StatusBadge label="ADMIN ONLY" tone="neutral" /></div>{message && <p className="success-message">{message}</p>}{mode === "Simulation" ? <div className={`sim-dock ${collapsed ? "collapsed" : ""}`}><button className="dock-toggle" onClick={() => setCollapsed((value) => !value)}>{collapsed ? "Expand simulation dock" : "Collapse simulation dock"}</button>{!collapsed && <><p className="muted">Control simulated time and replay a deterministic scenario without external integrations.</p><div className="sim-actions"><button className="primary-button compact-button" onClick={() => advance(1)}>+1 day</button><button className="secondary-button" onClick={() => advance(3)}>+3 days</button><button className="secondary-button" onClick={reset}>Reset scenario</button></div></>}</div> : <div className="timeline-list">{events.length === 0 ? <EmptyState title="No audit entries">Actions will appear here as the demo runs.</EmptyState> : events.map((event) => <article className="timeline-item" key={event.id}><strong>{event.action ?? event.type}</strong><span>{event.actor}</span><small>{formatDateTime(event.ts)}{event.reason ? ` · ${event.reason}` : ""}</small></article>)}</div>}<div className="outbox-panel"><h3>Outbox</h3>{notifications.length === 0 ? <p className="muted">No notifications sent.</p> : notifications.map((item) => <article className="notification-item" key={item.id}><strong>{item.subject}</strong><span>To {item.to_role_or_user}</span><p>{item.body}</p></article>)}</div></section>;
}

function stateTone(state: TaskState) {
  if (state === "DONE") return "good";
  if (state === "REJECTED" || state === "BLOCKED") return "warning";
  if (state === "IN_PROGRESS") return "neutral";
  return "neutral";
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
  const [detailView, setDetailView] = useState<"overview" | "plan" | "risks" | "graph">("overview");
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
              onClick={() => { setActive(item); setSelectedHire(null); setDetailView("overview"); }}
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
          {active === "My checklist" ? (
            <NewHireView />
          ) : active === "My queue" ? (
            <QueueView />
          ) : active === "Approvals" ? (
            <ApprovalsView />
          ) : active === "Simulation" || active === "Audit" ? (
            <AdminView mode={active} />
          ) : active === "My hires" || active === "Command center" ? (
            selectedHire ? (detailView === "plan" ? <PlanView hire={selectedHire} onBack={() => setDetailView("overview")} /> : detailView === "risks" ? <RisksView hire={selectedHire} /> : detailView === "graph" ? <GraphView hire={selectedHire} /> : <HireOverview hire={selectedHire} onBack={() => setSelectedHire(null)} onPlan={() => setDetailView("plan")} onRisks={() => setDetailView("risks")} onGraph={() => setDetailView("graph")} />) :
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
