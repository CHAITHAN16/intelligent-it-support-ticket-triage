import Link from "next/link";

import type { TicketResponse } from "@/lib/api";

function confidenceLabel(value: number | null) {
  return value === null ? "-" : `${Math.round(value * 100)}%`;
}

function priorityClass(priority: string) {
  if (priority === "HIGH" || priority === "URGENT") return "bg-rose-50 text-rose-700";
  if (priority === "LOW") return "bg-slate-100 text-slate-600";
  return "bg-amber-50 text-amber-700";
}

function statusClass(status: string) {
  if (status === "RESOLVED" || status === "CLOSED") return "bg-emerald-50 text-emerald-700";
  if (status === "IN_PROGRESS") return "bg-sky-50 text-sky-700";
  return "bg-slate-100 text-slate-700";
}

function createdLabel(value: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

export function AgentTicketTable({ tickets }: { tickets: TicketResponse[] }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="hidden grid-cols-[0.45fr_2fr_0.8fr_0.75fr_0.9fr_0.75fr_1.1fr] gap-4 border-b border-slate-200 bg-slate-50 px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500 lg:grid">
        <span>ID</span><span>Ticket</span><span>Category</span><span>Priority</span><span>Status</span><span>AI confidence</span><span>Created</span>
      </div>
      <div className="divide-y divide-slate-100">
        {tickets.map((ticket) => (
          <Link key={ticket.id} href={`/agent/tickets/${ticket.id}`} className="block px-5 py-5 transition hover:bg-sky-50/50 focus-visible:bg-sky-50 focus-visible:outline-none">
            <div className="grid gap-4 lg:grid-cols-[0.45fr_2fr_0.8fr_0.75fr_0.9fr_0.75fr_1.1fr] lg:items-center lg:gap-4">
              <span className="text-xs font-semibold text-slate-500">#{ticket.id}</span>
              <span className="min-w-0"><span className="block truncate text-sm font-semibold text-slate-900">{ticket.title}</span><span className="mt-1 block truncate text-xs text-slate-500">{ticket.assigned_team_name ?? "Unassigned"}</span></span>
              <span className="text-sm text-slate-600">{ticket.category ?? "-"}</span>
              <span className={`w-fit rounded-full px-2.5 py-1 text-xs font-semibold ${priorityClass(ticket.priority)}`}>{ticket.priority}</span>
              <span className={`w-fit rounded-full px-2.5 py-1 text-xs font-semibold ${statusClass(ticket.status)}`}>{ticket.status.replaceAll("_", " ")}</span>
              <span className="text-sm font-medium text-slate-700">{confidenceLabel(ticket.ai_confidence)}</span>
              <span className="text-sm text-slate-500">{createdLabel(ticket.created_at)}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
