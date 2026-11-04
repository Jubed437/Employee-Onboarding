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
