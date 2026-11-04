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
