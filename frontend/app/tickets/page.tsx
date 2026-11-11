"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { SiteHeader } from "@/components/site-header";
import { getMyTickets, type TicketResponse } from "@/lib/api";

const STATUSES = ["NEW", "ASSIGNED", "IN_PROGRESS", "WAITING_FOR_USER", "RESOLVED", "CLOSED"] as const;
const PRIORITIES = ["LOW", "MEDIUM", "HIGH", "URGENT"] as const;

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function confidenceValue(ticket: TicketResponse) {
  return ticket.ai_confidence === null ? "Not available" : `${Math.round(ticket.ai_confidence * 100)}%`;
}

function statusClass(status: TicketResponse["status"]) {
  switch (status) {
    case "RESOLVED":
    case "CLOSED":
      return "bg-emerald-50 text-emerald-700 ring-emerald-100";
    case "IN_PROGRESS":
      return "bg-amber-50 text-amber-700 ring-amber-100";
    case "ASSIGNED":
      return "bg-sky-50 text-sky-700 ring-sky-100";
    case "WAITING_FOR_USER":
      return "bg-violet-50 text-violet-700 ring-violet-100";
    default:
      return "bg-slate-100 text-slate-700 ring-slate-200";
  }
}

function TicketRow({ ticket }: { ticket: TicketResponse }) {
  return (
    <Link href={`/tickets/${ticket.id}`} aria-label={`View details for ticket ${ticket.id}: ${ticket.title}`} className="grid gap-4 px-5 py-5 transition hover:bg-sky-50/60 focus-visible:bg-sky-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-500 sm:grid-cols-[1fr_auto] sm:items-center">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold text-slate-950">#{ticket.id}</p>
          <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] ring-1 ring-inset ${statusClass(ticket.status)}`}>{ticket.status.replaceAll("_", " ")}</span>
        </div>
        <h2 className="mt-2 truncate text-base font-semibold text-slate-950">{ticket.title}</h2>
        <p className="mt-1 line-clamp-2 text-sm leading-6 text-slate-600">{ticket.description}</p>
      </div>
      <div className="grid gap-2 text-sm text-slate-600 sm:text-right">
        <p><span className="font-semibold text-slate-900">Category:</span> {ticket.ai_predicted_category ?? "AI processing in progress"}</p>
        <p><span className="font-semibold text-slate-900">Priority:</span> {ticket.ai_predicted_priority ?? "AI processing in progress"}</p>
        <p><span className="font-semibold text-slate-900">Team:</span> {ticket.assigned_team_name ?? ticket.assigned_team?.name ?? "AI processing in progress"}</p>
        <p><span className="font-semibold text-slate-900">Created:</span> {formatDate(ticket.created_at)}</p>
        <p><span className="font-semibold text-slate-900">AI confidence:</span> {confidenceValue(ticket)}</p>
        <span className="mt-1 inline-flex min-h-10 items-center justify-center rounded-full bg-sky-600 px-4 text-xs font-semibold text-white sm:justify-self-end">View Details <span className="ml-2" aria-hidden="true">&rarr;</span></span>
      </div>
    </Link>
  );
}

export default function EmployeeTicketsPage() {
  const [tickets, setTickets] = useState<TicketResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  const loadTickets = useCallback(async () => {
    setError(null);
    try {
      setTickets(await getMyTickets());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "My tickets could not be loaded.");
    }
  }, []);

  const categories = Array.from(new Set(tickets.map((ticket) => ticket.ai_predicted_category ?? ticket.category).filter((value): value is string => Boolean(value)))).sort();
  const filteredTickets = tickets.filter((ticket) => {
    const category = ticket.ai_predicted_category ?? ticket.category ?? "";
    const search = `${ticket.id} ${ticket.title} ${ticket.description} ${category} ${ticket.assigned_team_name ?? ticket.assigned_team?.name ?? ""}`.toLowerCase();
    return search.includes(query.trim().toLowerCase()) && (!statusFilter || ticket.status === statusFilter) && (!priorityFilter || ticket.priority === priorityFilter) && (!categoryFilter || category === categoryFilter);
  });

  const refresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await loadTickets();
    } finally {
      setIsRefreshing(false);
    }
  }, [loadTickets]);

  useEffect(() => {
    let active = true;
    async function run() {
      setIsLoading(true);
      try {
        const result = await getMyTickets();
        if (active) setTickets(result);
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "My tickets could not be loaded.");
      } finally {
        if (active) setIsLoading(false);
      }
    }
    void run();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#f6f8fb] text-slate-950">
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-5 py-12 sm:px-8 sm:py-16">
        <div className="mx-auto max-w-5xl">
          <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-sky-600">Employee support</p>
              <h1 className="mt-3 text-4xl font-semibold tracking-[-0.035em] text-slate-950 sm:text-5xl">My Tickets</h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">Review the requests you submitted, open each ticket for the collaboration history, and keep track of the latest status updates.</p>
            </div>
            <div className="flex flex-wrap gap-3"><Link href="/tickets/new" className="inline-flex items-center justify-center rounded-full bg-sky-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-sky-700">Submit Ticket</Link><button type="button" onClick={refresh} disabled={isLoading || isRefreshing} className="inline-flex items-center justify-center rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300">
              {isRefreshing ? "Refreshing..." : "Refresh"}
            </button></div>
          </div>

          {isLoading ? (
            <div className="rounded-3xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500 shadow-xl shadow-slate-900/5">Loading your tickets...</div>
          ) : error ? (
            <div role="alert" className="rounded-3xl border border-rose-200 bg-rose-50 px-5 py-4 text-sm leading-6 text-rose-800">
              <p className="font-semibold">We could not load your tickets.</p>
              <p className="mt-1">{error}</p>
            </div>
          ) : tickets.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center shadow-xl shadow-slate-900/5">
              <p className="text-lg font-semibold text-slate-900">No tickets yet</p>
              <p className="mt-2 text-sm leading-6 text-slate-500">Submit a request and it will show up here once it has been created.</p>
              <Link href="/tickets/new" className="mt-6 inline-flex rounded-full bg-sky-500 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-sky-500/20 transition hover:bg-sky-600">Submit Ticket</Link>
            </div>
          ) : (
            <>
            <section aria-label="Search and filter tickets" className="mb-5 grid gap-3 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-4">
              <label className="text-xs font-semibold text-slate-600">Search tickets<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Title, ID, description, team" className="mt-1.5 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal text-slate-900 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-500/15" /></label>
              <label className="text-xs font-semibold text-slate-600">Status<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="mt-1.5 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal text-slate-900"><option value="">All statuses</option>{STATUSES.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select></label>
              <label className="text-xs font-semibold text-slate-600">Priority<select value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)} className="mt-1.5 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal text-slate-900"><option value="">All priorities</option>{PRIORITIES.map((priority) => <option key={priority} value={priority}>{priority}</option>)}</select></label>
              <label className="text-xs font-semibold text-slate-600">Category<select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)} className="mt-1.5 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal text-slate-900"><option value="">All categories</option>{categories.map((category) => <option key={category} value={category}>{category}</option>)}</select></label>
            </section>
            <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl shadow-slate-900/5">
              <div className="border-b border-slate-200 px-5 py-4 text-sm text-slate-500">Showing {filteredTickets.length} of {tickets.length} ticket{tickets.length === 1 ? "" : "s"}</div>
              {filteredTickets.length === 0 ? <div className="px-5 py-12 text-center"><p className="font-semibold text-slate-900">No matching tickets</p><p className="mt-2 text-sm text-slate-500">Try changing the search or filters.</p><button type="button" onClick={() => { setQuery(""); setStatusFilter(""); setPriorityFilter(""); setCategoryFilter(""); }} className="mt-4 text-sm font-semibold text-sky-700 underline">Clear filters</button></div> :
              <div className="divide-y divide-slate-200">
                {filteredTickets.map((ticket) => <TicketRow key={ticket.id} ticket={ticket} />)}
              </div>}
            </section>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
