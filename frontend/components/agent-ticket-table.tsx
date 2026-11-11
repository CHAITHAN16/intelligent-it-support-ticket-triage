"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { TicketPriority, TicketResponse, TicketStatus } from "@/lib/api";

type TicketSource = "team" | "all";
type AssignmentFilter = "ALL" | "ASSIGNED" | "UNASSIGNED";

const STATUSES: TicketStatus[] = ["NEW", "ASSIGNED", "IN_PROGRESS", "WAITING_FOR_USER", "RESOLVED", "CLOSED"];
const PRIORITIES: TicketPriority[] = ["LOW", "MEDIUM", "HIGH", "URGENT"];

function dateLabel(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function priorityClass(priority: TicketPriority) {
  if (priority === "URGENT" || priority === "HIGH") return "bg-rose-50 text-rose-700 ring-rose-200";
  if (priority === "LOW") return "bg-slate-100 text-slate-600 ring-slate-200";
  return "bg-amber-50 text-amber-800 ring-amber-200";
}

function statusClass(status: TicketStatus) {
  if (status === "RESOLVED" || status === "CLOSED") return "bg-emerald-50 text-emerald-700 ring-emerald-200";
  if (status === "IN_PROGRESS") return "bg-sky-50 text-sky-700 ring-sky-200";
  if (status === "WAITING_FOR_USER") return "bg-violet-50 text-violet-700 ring-violet-200";
  return "bg-slate-100 text-slate-700 ring-slate-200";
}

function Badge({ children, className }: { children: React.ReactNode; className: string }) {
  return <span className={`inline-flex w-fit items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${className}`}>{children}</span>;
}

export function AgentTicketTable({
  tickets,
  source = "team",
  limit,
  showFilters = true,
  emptyTitle = "No tickets found",
  emptyDescription = "Tickets will appear here when they are available.",
}: {
  tickets: TicketResponse[];
  source?: TicketSource;
  limit?: number;
  showFilters?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
}) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<"ALL" | TicketStatus>("ALL");
  const [priority, setPriority] = useState<"ALL" | TicketPriority>("ALL");
  const [category, setCategory] = useState("ALL");
  const [assignment, setAssignment] = useState<AssignmentFilter>("ALL");
  const categories = useMemo(() => [...new Set(tickets.flatMap((ticket) => ticket.category ? [ticket.category] : []))].sort(), [tickets]);

  const filteredTickets = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    return tickets.filter((ticket) => {
      if (normalizedQuery && !`${ticket.id} ${ticket.title}`.toLocaleLowerCase().includes(normalizedQuery)) return false;
      if (status !== "ALL" && ticket.status !== status) return false;
      if (priority !== "ALL" && ticket.priority !== priority) return false;
      if (category !== "ALL" && ticket.category !== category) return false;
      if (assignment === "ASSIGNED" && ticket.assigned_agent_id == null) return false;
      if (assignment === "UNASSIGNED" && ticket.assigned_agent_id != null) return false;
      return true;
    });
  }, [tickets, query, status, priority, category, assignment]);
  const visibleTickets = limit === undefined ? filteredTickets : filteredTickets.slice(0, limit);

  return <section aria-label="Ticket list" className="overflow-hidden rounded-lg border border-slate-200 bg-white">
    {showFilters && <div className="flex flex-col gap-3 border-b border-slate-200 p-3 sm:flex-row sm:flex-wrap sm:items-center">
      <label className="relative min-w-0 flex-1 sm:min-w-60"><span className="sr-only">Search tickets by ID or subject</span><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search ticket ID or subject" className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 outline-none focus:border-sky-600 focus:ring-2 focus:ring-sky-100" /></label>
      <select aria-label="Filter by status" value={status} onChange={(event) => setStatus(event.target.value as "ALL" | TicketStatus)} className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"><option value="ALL">All statuses</option>{STATUSES.map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select>
      <select aria-label="Filter by priority" value={priority} onChange={(event) => setPriority(event.target.value as "ALL" | TicketPriority)} className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"><option value="ALL">All priorities</option>{PRIORITIES.map((value) => <option key={value} value={value}>{value}</option>)}</select>
      <select aria-label="Filter by category" value={category} onChange={(event) => setCategory(event.target.value)} className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"><option value="ALL">All categories</option>{categories.map((value) => <option key={value} value={value}>{value}</option>)}</select>
      {source === "all" && <select aria-label="Filter by agent assignment" value={assignment} onChange={(event) => setAssignment(event.target.value as AssignmentFilter)} className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"><option value="ALL">All assignments</option><option value="ASSIGNED">Assigned to agent</option><option value="UNASSIGNED">Unassigned to agent</option></select>}
    </div>}

    {filteredTickets.length === 0 ? <div className="px-5 py-12 text-center"><p className="text-sm font-semibold text-slate-800">{emptyTitle}</p><p className="mt-1 text-sm text-slate-500">{emptyDescription}</p></div> : <>
      <p className="border-b border-slate-100 px-4 py-2.5 text-xs text-slate-500">{limit === undefined ? `${filteredTickets.length} ticket${filteredTickets.length === 1 ? "" : "s"}` : `Showing ${visibleTickets.length} recent of ${filteredTickets.length} matching ticket${filteredTickets.length === 1 ? "" : "s"}`}</p>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[980px] text-left text-sm">
          <thead className="bg-slate-50 text-[11px] font-semibold uppercase tracking-wide text-slate-500"><tr>{["ID", "Ticket", "Category", "Priority", "Status", "Assigned team / agent", "Created"].map((label) => <th key={label} scope="col" className="px-4 py-3">{label}</th>)}</tr></thead>
          <tbody className="divide-y divide-slate-100">{visibleTickets.map((ticket) => <tr key={ticket.id} className="hover:bg-slate-50">
            <td className="whitespace-nowrap px-4 py-3 text-xs font-medium text-slate-500">#{ticket.id}</td>
            <td className="max-w-[300px] px-4 py-3"><Link href={`/agent/tickets/${ticket.id}?from=${source}`} className="block truncate font-medium text-sky-800 hover:underline focus-visible:outline-2 focus-visible:outline-sky-600">{ticket.title}</Link></td>
            <td className="px-4 py-3 text-slate-600">{ticket.category ?? "Uncategorized"}</td>
            <td className="px-4 py-3"><Badge className={priorityClass(ticket.priority)}>{ticket.priority}</Badge></td>
            <td className="px-4 py-3"><Badge className={statusClass(ticket.status)}>{ticket.status.replaceAll("_", " ")}</Badge></td>
            <td className="px-4 py-3"><span className="block text-slate-700">{ticket.assigned_team_name ?? "Unassigned team"}</span><span className="mt-0.5 block text-xs text-slate-500">{ticket.assigned_agent_id == null ? "No agent" : `Agent #${ticket.assigned_agent_id}`}</span></td>
            <td className="whitespace-nowrap px-4 py-3 text-slate-500">{dateLabel(ticket.created_at)}</td>
          </tr>)}</tbody>
        </table>
      </div>
      <div className="divide-y divide-slate-100 md:hidden">{visibleTickets.map((ticket) => <Link key={ticket.id} href={`/agent/tickets/${ticket.id}?from=${source}`} className="block px-4 py-4 hover:bg-slate-50 focus-visible:bg-sky-50 focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-sky-600">
        <div className="flex items-start justify-between gap-3"><span className="min-w-0"><span className="block text-xs font-medium text-slate-500">Ticket #{ticket.id}</span><span className="mt-1 block text-sm font-semibold text-slate-950">{ticket.title}</span></span><Badge className={priorityClass(ticket.priority)}>{ticket.priority}</Badge></div>
        <div className="mt-3 flex flex-wrap items-center gap-2"><Badge className={statusClass(ticket.status)}>{ticket.status.replaceAll("_", " ")}</Badge><span className="text-xs text-slate-600">{ticket.category ?? "Uncategorized"}</span><span className="text-xs text-slate-500">{ticket.assigned_team_name ?? "Unassigned team"}</span></div>
        <time dateTime={ticket.created_at} className="mt-2 block text-xs text-slate-500">{dateLabel(ticket.created_at)}</time>
      </Link>)}</div>
    </>}
  </section>;
}
