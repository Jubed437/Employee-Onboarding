import { createContext } from "react";

import type { Persona } from "./types";

export type AuthContextValue = {
  user: Persona | null;
  login: (persona: Persona) => Promise<void>;
  logout: () => void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);
