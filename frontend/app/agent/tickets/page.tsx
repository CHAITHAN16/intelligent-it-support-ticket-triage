"use client";

import { useEffect, useState } from "react";

import { AgentShell } from "@/components/agent-shell";
import { AgentTicketTable } from "@/components/agent-ticket-table";
import { getTickets, type TicketResponse } from "@/lib/api";

export default function AgentTicketsPage() {
  const [tickets, setTickets] = useState<TicketResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getTickets().then((result) => { if (!cancelled) setTickets(result); })
      .catch((reason: unknown) => { if (!cancelled) setError(reason instanceof Error ? reason.message : "Tickets could not be loaded."); })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, [refreshKey]);

  function refreshTickets() {
    setIsLoading(true);
    setError(null);
    setRefreshKey((key) => key + 1);
  }

  return <AgentShell activeSection="all" selectedTeamName="All tickets">
    <div className="mx-auto max-w-[1320px] space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-sky-700">Support operations</p><h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">All tickets</h1><p className="mt-1.5 text-sm text-slate-600">Tickets assigned to you or teams you belong to.</p></div><button type="button" onClick={refreshTickets} disabled={isLoading} className="rounded-md border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50">{isLoading ? "Refreshing..." : "Refresh"}</button></div>
      {error ? <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"><p className="font-medium">Tickets could not be loaded</p><p className="mt-1">{error}</p><button type="button" onClick={refreshTickets} className="mt-3 rounded-md bg-rose-800 px-3 py-2 font-medium text-white hover:bg-rose-900">Retry</button></div> : isLoading ? <div role="status" className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">Loading tickets...</div> : <AgentTicketTable tickets={tickets} source="all" emptyTitle="No tickets match these filters" emptyDescription="Try changing your search or filters, or refresh the ticket list." />}
    </div>
  </AgentShell>;
}
