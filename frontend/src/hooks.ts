import { useEffect, useState } from "react";

import { api } from "./api";
import type { SimulationClock } from "./types";

export function useSimulationClock(): {
  clock: SimulationClock | null;
  error: string | null;
} {
  const [clock, setClock] = useState<SimulationClock | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    api.clock().then(
      (value) => active && setClock(value),
      () => active && setError("Simulation clock unavailable"),
    );
    return () => {
      active = false;
    };
  }, []);
  return { clock, error };
}

export function useOnboardingStream(hireId?: string): boolean {
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    if (!localStorage.getItem("onboarding-token")) {
      return;
    }
    const source = new EventSource(api.streamUrl(hireId));
    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);
    return () => source.close();
  }, [hireId]);
  return connected;
}
