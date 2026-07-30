"use client";

import Link from "next/link";
import { ReactNode } from "react";

export const NAV_ITEMS = [
  { href: "/", label: "Overview", hint: "Platform at a glance" },
  { href: "/decisions", label: "Decisions", hint: "Test a retention action" },
  { href: "/monitoring", label: "Monitoring", hint: "Watch health and drift" },
  { href: "/simulation-lab", label: "Simulation Lab", hint: "Run what-if predictions" },
  { href: "/operations", label: "Operations", hint: "Run safe MLOps jobs" },
  { href: "/policy", label: "Policy", hint: "Manage decision rules" },
] as const;

type Props = {
  active: string;
  environment?: string;
  refreshedAt?: string;
  onRefresh?: () => void;
  refreshing?: boolean;
  children: ReactNode;
};

export function ControlCenterShell({ active, environment = "local", refreshedAt, onRefresh, refreshing, children }: Props) {
  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <span className="brand-mark">R</span>
          <div>
            <p className="eyebrow">RETENTIONOPS</p>
            <strong>Control Center</strong>
          </div>
        </div>
        <nav className="main-nav" aria-label="Control Center sections">
          {NAV_ITEMS.map((item) => (
            <Link className={`nav-item ${active === item.href ? "active" : ""}`} href={item.href} key={item.href}>
              <span>{item.label}</span>
              <small>{item.hint}</small>
            </Link>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="status-dot healthy" />
          <span>Connected to the platform</span>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">UPLIFT PLATFORM / {active === "/" ? "OVERVIEW" : active.slice(1).toUpperCase()}</p>
            <p className="muted topbar-subtitle">Manage decisions, models, monitoring, and policy from one place.</p>
          </div>
          <div className="topbar-actions">
            <span className="environment-pill"><span className="status-dot healthy" />{environment}</span>
            {onRefresh && <button className="secondary" onClick={onRefresh} disabled={refreshing}>{refreshing ? "Refreshing…" : "Refresh"}</button>}
          </div>
        </header>
        {children}
        <footer>RetentionOps Control Center{refreshedAt ? ` · Updated ${new Date(refreshedAt).toLocaleTimeString()}` : ""}</footer>
      </div>
    </main>
  );
}

export function PageIntro({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return <div className="page-intro"><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="lead muted">{description}</p></div>;
}

export function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{children}</section>;
}

export function PanelHeading({ eyebrow, title, action }: { eyebrow?: string; title: string; action?: ReactNode }) {
  return <div className="panel-heading"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h2>{title}</h2></div>{action}</div>;
}

export function StatusMessage({ kind = "info", children }: { kind?: "info" | "success" | "warning" | "error"; children: ReactNode }) {
  return <div className={`status-message ${kind}`} role={kind === "error" ? "alert" : "status"}>{children}</div>;
}

export function LoadingState({ label = "Loading platform data…" }: { label?: string }) {
  return <div className="loading-state" role="status"><span className="loading-spinner" />{label}</div>;
}

export function TechnicalDetails({ title = "Technical details", children }: { title?: string; children: ReactNode }) {
  return <details className="technical-details"><summary>{title}</summary><div className="technical-details-body">{children}</div></details>;
}

export function MetricCard({ label, value, unit, description }: { label: string; value: string; unit?: string; description?: string }) {
  return <div className="metric-card"><span className="muted">{label}</span><strong>{value}</strong>{unit && <small>{unit}</small>}{description && <p className="small muted">{description}</p>}</div>;
}
