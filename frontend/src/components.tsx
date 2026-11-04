import type { ReactNode } from "react";

export function StatusBadge({ label, tone = "neutral" }: { label: string; tone?: string }) {
  return <span className={`status-badge status-${tone}`}>{label}</span>;
}

export function ScoreGauge({ score }: { score: number }) {
  return (
    <div className="score-gauge" aria-label={`Readiness score ${score} out of 100`}>
      <strong>{score}</strong>
      <span>/ 100</span>
    </div>
  );
}

export function ProgressBar({ value }: { value: number }) {
  return (
    <div className="progress-track" aria-label={`${value}% complete`}>
      <span style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
}

export function Skeleton({ width = "100%" }: { width?: string }) {
  return <span className="skeleton" style={{ width }} aria-hidden="true" />;
}

export function EmptyState({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="empty-state">
      <h2>{title}</h2>
      <p>{children}</p>
    </section>
  );
}

export function ErrorState({ message }: { message: string }) {
  return <p className="error-state" role="alert">{message}</p>;
}
