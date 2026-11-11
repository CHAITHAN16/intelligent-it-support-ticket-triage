"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AgentShell } from "@/components/agent-shell";
import { AgentTicketTable } from "@/components/agent-ticket-table";
import { getTickets, type TicketResponse } from "@/lib/api";

function Metric({ label, value, description }: { label: string; value: number; description: string }) {
  return <article className="rounded-lg border border-slate-200 bg-white px-4 py-4">
    <p className="text-xs font-medium text-slate-500">{label}</p>
    <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{value}</p>
    <p className="mt-1 text-xs text-slate-500">{description}</p>
  </article>;
}

export default function AgentDashboardPage() {
  const [tickets, setTickets] = useState<TicketResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const loadTickets = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setTickets(await getTickets());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Dashboard tickets could not be loaded.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { void loadTickets(); }, [loadTickets, refreshKey]);

  const openCount = tickets.filter((ticket) => !["RESOLVED", "CLOSED"].includes(ticket.status)).length;
  const urgentCount = tickets.filter((ticket) => ticket.priority === "URGENT" && !["RESOLVED", "CLOSED"].includes(ticket.status)).length;
  const unassignedCount = tickets.filter((ticket) => ticket.assigned_agent_id == null && !["RESOLVED", "CLOSED"].includes(ticket.status)).length;
  const resolvedCount = tickets.filter((ticket) => ticket.status === "RESOLVED").length;
  const recentTickets = [...tickets].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));

  return <AgentShell activeSection="overview" selectedTeamName="Agent overview">
    <div className="mx-auto max-w-[1320px] space-y-7">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-sky-700">Support operations</p><h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">Agent overview</h1><p className="mt-1.5 text-sm text-slate-600">A current view of tickets available to your account.</p></div>
        <button type="button" onClick={() => setRefreshKey((key) => key + 1)} disabled={isLoading} className="inline-flex items-center justify-center rounded-md border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50">{isLoading ? "Refreshing..." : "Refresh"}</button>
      </div>

      {error ? <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"><p className="font-medium">Could not load dashboard tickets</p><p className="mt-1">{error}</p><button type="button" onClick={() => setRefreshKey((key) => key + 1)} className="mt-3 rounded-md bg-rose-800 px-3 py-2 font-medium text-white hover:bg-rose-900">Retry</button></div> : isLoading ? <div role="status" className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">Loading overview...</div> : <>
        <section aria-label="Ticket metrics" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Metric label="Open" value={openCount} description="Not resolved or closed" />
          <Metric label="Urgent" value={urgentCount} description="Open urgent priority" />
          <Metric label="Unassigned" value={unassignedCount} description="Open without an assigned agent" />
          <Metric label="Resolved" value={resolvedCount} description="Currently resolved" />
        </section>

        <section className="space-y-3">
          <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end"><div><h2 className="text-lg font-semibold text-slate-950">Recent tickets</h2><p className="mt-1 text-sm text-slate-500">Latest tickets available to you, searchable by ID or subject.</p></div><Link href="/agent/tickets" className="text-sm font-medium text-sky-800 hover:underline">View all tickets <span aria-hidden="true">→</span></Link></div>
          <AgentTicketTable tickets={recentTickets} source="overview" limit={6} emptyTitle="No tickets yet" emptyDescription="Tickets available to your account will appear here." />
        </section>
      </>}
    </div>
  </AgentShell>;
}
