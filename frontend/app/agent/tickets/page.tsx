"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AgentShell } from "@/components/agent-shell";
import { getTickets, type TicketPriority, type TicketResponse, type TicketStatus } from "@/lib/api";

const STATUSES: TicketStatus[] = ["NEW", "ASSIGNED", "IN_PROGRESS", "WAITING_FOR_USER", "RESOLVED", "CLOSED"];
const PRIORITIES: TicketPriority[] = ["LOW", "MEDIUM", "HIGH", "URGENT"];
const CATEGORIES = ["Network", "Security", "Software", "Other"];
type AssignmentFilter = "ALL" | "ASSIGNED" | "UNASSIGNED";

function formattedDate(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function confidenceLabel(value: number | null) {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

function pillClass(value: string) {
  return "inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700";
}

export default function AgentTicketsPage() {
  const [tickets, setTickets] = useState<TicketResponse[]>([]);
  const [status, setStatus] = useState<"ALL" | TicketStatus>("ALL");
  const [priority, setPriority] = useState<"ALL" | TicketPriority>("ALL");
  const [category, setCategory] = useState("ALL");
  const [assignment, setAssignment] = useState<AssignmentFilter>("ALL");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getTickets()
      .then((result) => { if (!cancelled) setTickets(result); })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "Tickets could not be loaded.");
      })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const filteredTickets = useMemo(() => tickets.filter((ticket) => {
    if (status !== "ALL" && ticket.status !== status) return false;
    if (priority !== "ALL" && ticket.priority !== priority) return false;
    if (category !== "ALL" && ticket.category !== category) return false;
    if (assignment === "ASSIGNED" && ticket.assigned_agent_id == null) return false;
    if (assignment === "UNASSIGNED" && ticket.assigned_agent_id != null) return false;
    return true;
  }), [tickets, status, priority, category, assignment]);

  return (
    <AgentShell selectedTeamName="Agent ticket queue">
      <div className="mx-auto max-w-7xl space-y-6">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-600">Support operations</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-[-0.04em] text-slate-950">Agent ticket queue</h1>
          <p className="mt-2 text-sm text-slate-600">Tickets assigned to you or teams you belong to.</p>
        </div>

        {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>}

        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap gap-3">
            <select aria-label="Filter by status" value={status} onChange={(event) => setStatus(event.target.value as "ALL" | TicketStatus)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
              <option value="ALL">All statuses</option>{STATUSES.map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}
            </select>
            <select aria-label="Filter by priority" value={priority} onChange={(event) => setPriority(event.target.value as "ALL" | TicketPriority)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
              <option value="ALL">All priorities</option>{PRIORITIES.map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
            <select aria-label="Filter by category" value={category} onChange={(event) => setCategory(event.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
              <option value="ALL">All categories</option>{CATEGORIES.map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
            <select aria-label="Filter by assigned agent" value={assignment} onChange={(event) => setAssignment(event.target.value as AssignmentFilter)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
              <option value="ALL">Assigned and unassigned</option><option value="ASSIGNED">Assigned to agent</option><option value="UNASSIGNED">Unassigned to agent</option>
            </select>
          </div>
        </section>

        {isLoading ? <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">Loading tickets...</div> : filteredTickets.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center"><p className="font-semibold text-slate-800">No tickets match these filters</p><p className="mt-1 text-sm text-slate-500">Try changing one or more filters.</p></div>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
            <table className="min-w-[1100px] w-full text-left text-sm">
              <thead className="bg-slate-50 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                <tr>{["Ticket", "Status", "Priority", "AI category", "AI confidence", "Assigned team", "Assigned agent", "Created", "Solution"].map((label) => <th key={label} scope="col" className="px-4 py-3">{label}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredTickets.map((ticket) => (
                  <tr key={ticket.id} className="hover:bg-sky-50/50">
                    <td className="px-4 py-4"><Link href={`/agent/tickets/${ticket.id}`} className="font-semibold text-sky-800 hover:underline">#{ticket.id} · {ticket.title}</Link></td>
                    <td className="px-4 py-4"><span className={pillClass(ticket.status)}>{ticket.status.replaceAll("_", " ")}</span></td>
                    <td className="px-4 py-4">{ticket.priority}</td>
                    <td className="px-4 py-4">{ticket.ai_predicted_category ?? "—"}</td>
                    <td className="px-4 py-4">{confidenceLabel(ticket.ai_confidence)}</td>
                    <td className="px-4 py-4">{ticket.assigned_team_name ?? "Unassigned"}</td>
                    <td className="px-4 py-4">{ticket.assigned_agent_id == null ? "Unassigned" : `Agent #${ticket.assigned_agent_id}`}</td>
                    <td className="whitespace-nowrap px-4 py-4">{formattedDate(ticket.created_at)}</td>
                    <td className="px-4 py-4">{ticket.solution_status ?? "Processing"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!isLoading && <p className="text-xs text-slate-500">Showing {filteredTickets.length} of {tickets.length} tickets available to you.</p>}
      </div>
    </AgentShell>
  );
}
