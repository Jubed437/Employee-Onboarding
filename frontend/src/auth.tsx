import { useMemo, useState, type ReactNode } from "react";

import { api } from "./api";
import { AuthContext, type AuthContextValue } from "./auth-context";
import type { Persona } from "./types";

function storedUser(): Persona | null {
  const raw = localStorage.getItem("onboarding-user");
  return raw ? (JSON.parse(raw) as Persona) : null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Persona | null>(storedUser);
  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      async login(persona) {
        const response = await api.login(persona.id);
        localStorage.setItem("onboarding-token", response.token);
        localStorage.setItem("onboarding-user", JSON.stringify(response.user));
        setUser(response.user);
      },
      logout() {
        localStorage.removeItem("onboarding-token");
        localStorage.removeItem("onboarding-user");
        setUser(null);
      },
    }),
    [user],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
