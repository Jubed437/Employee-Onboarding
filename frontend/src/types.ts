export type Role =
  | "NEW_HIRE"
  | "MANAGER"
  | "HR"
  | "PAYROLL"
  | "IT"
  | "BENEFITS"
  | "LEARNING"
  | "FACILITIES"
  | "ADMIN";

export type Persona = {
  id: string;
  display_name: string;
  role: Role;
  team_id: string;
};

export type LoginResponse = {
  token: string;
  user: Persona;
};

export type SimulationClock = {
  now: string;
  mode: "SIM" | "REAL";
};

export type Hire = {
  id: string;
  full_name: string;
  email: string;
  join_date: string;
  profile_key: string;
};

export type HireCreate = {
  full_name: string;
  email: string;
  job_title: string;
  department: string;
  join_date: string;
  work_state: string;
  is_experienced: boolean;
  is_remote: boolean;
  manager_id?: string;
  profile_key: string;
};

export type Readiness = {
  id: string;
  employee_id: string;
  ts: string;
  score: number;
  band: "READY" | "WATCH" | "AT_RISK";
  breakdown: Record<string, number>;
  drivers: string[];
};

export type TaskState =
  | "NOT_STARTED"
  | "READY"
  | "IN_PROGRESS"
  | "BLOCKED"
  | "REJECTED"
  | "DONE"
  | "SKIPPED";

export type Task = {
  id: string;
  template_key: string;
  title: string;
  state: TaskState;
  due_date: string;
  owner_role: Role;
  assignee_user_id: string | null;
  duration_days: number;
  is_critical: boolean;
  is_mandatory: boolean;
  is_compliance: boolean;
  outcome_tags: string[];
  meta: Record<string, unknown>;
};

export type Plan = {
  tasks: Task[];
  edges: { from: string; to: string }[];
};
