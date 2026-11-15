"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AgentShell } from "@/components/agent-shell";
import { AgentTicketTable } from "@/components/agent-ticket-table";
import { UiIcon, type IconName } from "@/components/ui-icon";
import { getTickets, type TicketResponse } from "@/lib/api";

function Metric({ label, value, description, icon, tone }: { label: string; value: number; description: string; icon: IconName; tone: string }) {
  return <article className="flex min-h-32 items-start justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-900/[0.03]">
    <div><p className="text-xs font-medium text-slate-500">{label}</p><p className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">{value}</p><p className="mt-1 text-xs text-slate-500">{description}</p></div>
    <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${tone}`}><UiIcon name={icon} className="h-5 w-5" /></span>
  </article>;
}

function BreakdownCard({ title, rows, color }: { title: string; rows: Array<{ label: string; value: number }>; color: string }) {
  const maximum = Math.max(1, ...rows.map((row) => row.value));
  return <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-900/[0.03]">
    <div className="mb-4 flex items-center justify-between"><h2 className="text-sm font-semibold text-slate-900">{title}</h2><span className="text-xs text-slate-500">{rows.reduce((sum, row) => sum + row.value, 0)} tickets</span></div>
    {rows.length ? <ul className="space-y-3">{rows.map((row) => <li key={row.label}><div className="mb-1 flex items-center justify-between gap-3 text-xs"><span className="text-slate-600">{row.label}</span><span className="font-semibold tabular-nums text-slate-800">{row.value}</span></div><div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className={`h-full rounded-full ${color}`} style={{ width: `${row.value ? Math.max(3, row.value / maximum * 100) : 0}%` }} /></div></li>)}</ul> : <p className="text-sm text-slate-500">No ticket data available.</p>}
  </section>;
}

export default function AgentDashboardPage() {
  const [tickets, setTickets] = useState<TicketResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getTickets().then((result) => { if (!cancelled) setTickets(result); })
      .catch((reason: unknown) => { if (!cancelled) setError(reason instanceof Error ? reason.message : "Dashboard tickets could not be loaded."); })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, [refreshKey]);

  function refreshTickets() {
    setIsLoading(true);
    setError(null);
    setRefreshKey((key) => key + 1);
  }

  const openCount = tickets.filter((ticket) => !["RESOLVED", "CLOSED"].includes(ticket.status)).length;
  const urgentCount = tickets.filter((ticket) => ticket.priority === "URGENT" && !["RESOLVED", "CLOSED"].includes(ticket.status)).length;
  const unassignedCount = tickets.filter((ticket) => ticket.assigned_agent_id == null && !["RESOLVED", "CLOSED"].includes(ticket.status)).length;
  const resolvedCount = tickets.filter((ticket) => ticket.status === "RESOLVED").length;
  const recentTickets = [...tickets].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
  const priorityRows = ["URGENT", "HIGH", "MEDIUM", "LOW"].map((label) => ({ label, value: tickets.filter((ticket) => ticket.priority === label).length }));
  const categoryRows = [...new Set(tickets.map((ticket) => ticket.category ?? "Uncategorized"))].map((label) => ({ label, value: tickets.filter((ticket) => (ticket.category ?? "Uncategorized") === label).length })).sort((a, b) => b.value - a.value).slice(0, 6);

  return <AgentShell activeSection="overview" selectedTeamName="Agent overview">
      <div className="mx-auto max-w-[1440px] space-y-6">
      <div className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-900/[0.03] sm:flex-row sm:items-center">
        <div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-teal-700">Support operations</p><h1 className="mt-1.5 text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">Agent overview</h1><p className="mt-1.5 text-sm text-slate-600">A current view of tickets available to your account.</p></div>
        <button type="button" onClick={refreshTickets} disabled={isLoading} className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"><UiIcon name="activity" className="h-4 w-4" />{isLoading ? "Refreshing..." : "Refresh"}</button>
      </div>

      {error ? <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"><p className="font-medium">Could not load dashboard tickets</p><p className="mt-1">{error}</p><button type="button" onClick={refreshTickets} className="mt-3 rounded-md bg-rose-800 px-3 py-2 font-medium text-white hover:bg-rose-900">Retry</button></div> : isLoading ? <div role="status" className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">Loading overview...</div> : <>
        <section aria-label="Ticket metrics" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Metric label="Open tickets" value={openCount} description="Not resolved or closed" icon="inbox" tone="bg-blue-50 text-blue-700" />
          <Metric label="Urgent tickets" value={urgentCount} description="Open urgent priority" icon="flame" tone="bg-red-50 text-red-700" />
          <Metric label="Needs assignment" value={unassignedCount} description="Open without an assigned agent" icon="user-check" tone="bg-amber-50 text-amber-700" />
          <Metric label="Resolved" value={resolvedCount} description="Currently resolved" icon="check-circle" tone="bg-emerald-50 text-emerald-700" />
        </section>

        <section aria-label="Ticket breakdowns" className="grid gap-4 lg:grid-cols-2"><BreakdownCard title="Tickets by priority" rows={priorityRows} color="bg-teal-600" /><BreakdownCard title="Most common categories" rows={categoryRows} color="bg-blue-600" /></section>

        <section className="space-y-3">
          <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end"><div><h2 className="text-lg font-semibold text-slate-950">Recent tickets</h2><p className="mt-1 text-sm text-slate-500">Latest tickets available to you, searchable by ID or subject.</p></div><Link href="/agent/tickets" className="inline-flex items-center gap-1 text-sm font-semibold text-teal-700 hover:underline">View all tickets <UiIcon name="arrow-right" className="h-4 w-4" /></Link></div>
          <AgentTicketTable tickets={recentTickets} source="overview" limit={6} emptyTitle="No tickets yet" emptyDescription="Tickets available to your account will appear here." />
        </section>
      </>}
    </div>
  </AgentShell>;
}
