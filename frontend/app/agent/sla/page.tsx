"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AgentShell } from "@/components/agent-shell";
import { formatDuration, SLAStateBadge } from "@/components/agent-sla";
import { useAuth } from "@/lib/auth";
import { getSLAOverview, getTeamAgents, getTeams, type SLAOverview, type SLAOverviewFilters, type SLAState, type Team, type TicketPriority, type TicketSLA } from "@/lib/api";

const PRIORITIES: TicketPriority[] = ["LOW", "MEDIUM", "HIGH", "URGENT"];
const STATES: SLAState[] = ["ON_TRACK", "APPROACHING", "BREACHED", "MET", "NOT_APPLICABLE"];

function dateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function TicketList({ title, items, empty }: { title: string; items: TicketSLA[]; empty: string }) {
  return <section className="overflow-hidden rounded-lg border border-slate-200 bg-white">
    <div className="border-b border-slate-100 px-4 py-3"><h2 className="text-sm font-semibold text-slate-900">{title}</h2><p className="mt-1 text-xs text-slate-500">{items.length} ticket{items.length === 1 ? "" : "s"}</p></div>
    {items.length === 0 ? <p className="px-4 py-6 text-center text-sm text-slate-500">{empty}</p>
      : <ul className="divide-y divide-slate-100">{items.map((item) => {
        const isResponse = title.toLowerCase().includes("response");
        const clock = isResponse ? item.response : item.resolution;
        return <li key={`${title}-${item.ticket_id}`} className="px-4 py-3 hover:bg-slate-50">
          <Link href={`/agent/tickets/${item.ticket_id}?from=all`} className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0"><p className="text-sm font-semibold text-sky-800">Ticket #{item.ticket_id}</p><p className="mt-1 text-xs text-slate-500">{item.priority} · {item.status.replaceAll("_", " ")} · Team {item.team_id == null ? "unassigned" : `#${item.team_id}`}</p></div>
            <div className="flex flex-wrap items-center gap-2"><span className="text-xs text-slate-500">{clock.completed_at ? `Completed ${dateTime(clock.completed_at)}` : clock.actively_overdue ? `Overdue ${formatDuration(clock.overdue_seconds)}` : `Due ${dateTime(clock.deadline)}`}</span><SLAStateBadge clock={clock} compact /></div>
          </Link>
        </li>;
      })}</ul>}
  </section>;
}

export default function AgentSLAPage() {
  const { user, isLoading: authLoading } = useAuth();
  const [teams, setTeams] = useState<Team[]>([]);
  const [filters, setFilters] = useState<SLAOverviewFilters>({ approaching_within_minutes: 60 });
  const [windowText, setWindowText] = useState("60");
  const [overview, setOverview] = useState<SLAOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [teamsLoading, setTeamsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [teamsError, setTeamsError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !user) return;
    const currentUser = user;
    let cancelled = false;
    async function loadTeams() {
      setTeamsLoading(true); setTeamsError(null);
      try {
        const allTeams = await getTeams();
        if (currentUser.role === "ADMIN") { if (!cancelled) setTeams(allTeams); return; }
        const membershipResults = await Promise.all(allTeams.map(async (team) => {
          try {
            const agents = await getTeamAgents(team.id);
            return agents.some((agent) => agent.id === currentUser.id) ? team : null;
          } catch { return null; }
        }));
        if (!cancelled) setTeams(membershipResults.filter((team): team is Team => team !== null));
      } catch (reason) { if (!cancelled) setTeamsError(reason instanceof Error ? reason.message : "Teams could not be loaded."); }
      finally { if (!cancelled) setTeamsLoading(false); }
    }
    void loadTeams();
    return () => { cancelled = true; };
  }, [authLoading, user]);

  const loadOverview = useCallback(async () => {
    setLoading(true); setError(null);
    try { setOverview(await getSLAOverview(filters)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "SLA overview could not be loaded."); }
    finally { setLoading(false); }
  }, [filters]);

  useEffect(() => {
    if (authLoading || !user) return;
    let cancelled = false;
    Promise.resolve().then(() => {
      if (cancelled) return null;
      setLoading(true);
      return getSLAOverview(filters);
    }).then((result) => { if (!cancelled && result) { setOverview(result); setError(null); } })
      .catch((reason) => { if (!cancelled) setError(reason instanceof Error ? reason.message : "SLA overview could not be loaded."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [authLoading, user, filters]);

  function setFilter<K extends keyof SLAOverviewFilters>(key: K, value: SLAOverviewFilters[K] | undefined) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  const approachingResponse = overview?.approaching_response ?? [];
  const approachingResolution = overview?.approaching_resolution ?? [];
  const breachedResponse = overview?.breached_response ?? [];
  const breachedResolution = overview?.breached_resolution ?? [];
  const responseActiveOverdue = breachedResponse.filter((item) => item.response.actively_overdue).length;
  const resolutionActiveOverdue = breachedResolution.filter((item) => item.resolution.actively_overdue).length;

  return <AgentShell activeSection="sla" selectedTeamName="SLA overview">
    <div className="mx-auto max-w-[1440px] space-y-5">
      <header className="flex flex-col gap-3 border-b border-slate-200 pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div><p className="text-xs font-semibold uppercase tracking-wider text-blue-700">Operations</p><h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">SLA Overview</h1><p className="mt-1 text-sm text-slate-600">Monitor response and resolution targets for tickets you can access.</p></div>
        <button type="button" onClick={() => void loadOverview()} disabled={loading} className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50">{loading ? "Refreshing…" : "Refresh"}</button>
      </header>

      <section aria-label="SLA filters" className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm shadow-slate-200/40 sm:grid-cols-2 xl:grid-cols-4">
        <label className="text-xs font-medium text-slate-600">Team<select value={filters.team_id ?? ""} disabled={teamsLoading} onChange={(event) => setFilter("team_id", event.target.value ? Number(event.target.value) : undefined)} className="mt-1.5 w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"> <option value="">All accessible teams</option>{teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}</select>{teamsError && <span className="mt-1 block text-[11px] text-rose-700">{teamsError}</span>}</label>
        <label className="text-xs font-medium text-slate-600">Priority<select value={filters.priority ?? ""} onChange={(event) => setFilter("priority", (event.target.value || undefined) as TicketPriority | undefined)} className="mt-1.5 w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"><option value="">All priorities</option>{PRIORITIES.map((priority) => <option key={priority}>{priority}</option>)}</select></label>
        <label className="text-xs font-medium text-slate-600">SLA state<select value={filters.state ?? ""} onChange={(event) => setFilter("state", (event.target.value || undefined) as SLAState | undefined)} className="mt-1.5 w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"><option value="">All states</option>{STATES.map((state) => <option key={state} value={state}>{state.replaceAll("_", " ")}</option>)}</select></label>
        <label className="text-xs font-medium text-slate-600">Approaching within minutes<input type="number" min={1} max={10080} value={windowText} onChange={(event) => setWindowText(event.target.value)} onBlur={() => { const value = Math.min(10080, Math.max(1, Number(windowText) || 60)); setWindowText(String(value)); setFilter("approaching_within_minutes", value); }} onKeyDown={(event) => { if (event.key === "Enter") { event.currentTarget.blur(); } }} className="mt-1.5 w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100" /></label>
      </section>

      {loading && !overview ? <div role="status" className="rounded-lg border border-slate-200 bg-white px-5 py-12 text-center text-sm text-slate-500">Loading SLA overview…</div>
        : error && !overview ? <div role="alert" className="rounded-lg border border-rose-200 bg-white p-5 text-sm text-rose-700">{error}<button type="button" onClick={() => void loadOverview()} className="ml-2 font-semibold underline">Retry</button></div>
          : overview && <>
            {error && <div role="alert" className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">Refresh failed: {error}</div>}
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {[
                { title: "Approaching response", value: approachingResponse.length, detail: `Next ${overview.approaching_within_minutes} minutes`, tone: "text-amber-700", accent: "border-t-amber-400" },
                { title: "Approaching resolution", value: approachingResolution.length, detail: `Next ${overview.approaching_within_minutes} minutes`, tone: "text-amber-700", accent: "border-t-amber-400" },
                { title: "Breached response", value: breachedResponse.length, detail: `${responseActiveOverdue} currently overdue`, tone: "text-rose-700", accent: "border-t-rose-400" },
                { title: "Breached resolution", value: breachedResolution.length, detail: `${resolutionActiveOverdue} currently overdue`, tone: "text-rose-700", accent: "border-t-rose-400" },
              ].map((card) => <article key={card.title} className={`rounded-lg border border-slate-200 border-t-2 ${card.accent} bg-white p-4 shadow-sm shadow-slate-200/40`}><p className="text-xs font-medium text-slate-500">{card.title}</p><p className={`mt-2 text-3xl font-semibold ${card.tone}`}>{card.value}</p><p className="mt-1 text-xs text-slate-500">{card.detail}</p></article>)}
            </div>

            <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm shadow-slate-200/40">
              <div className="border-b border-slate-100 px-4 py-3"><h2 className="text-sm font-semibold text-slate-900">Priority breakdown</h2><p className="mt-1 text-xs text-slate-500">{overview.total_tickets} tickets in the current scope</p></div>
              <div className="overflow-x-auto"><table className="w-full min-w-[700px] text-left text-xs"><thead className="bg-slate-50 text-slate-500"><tr>{["Priority", "Tickets", "Approaching response", "Approaching resolution", "Breached response", "Breached resolution", "Active overdue"].map((heading) => <th key={heading} className="px-3 py-2.5 font-medium">{heading}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{overview.priority_counts.map((row) => <tr key={row.priority} className="text-slate-700"><th className="px-3 py-3 font-semibold text-slate-900">{row.priority}</th><td className="px-3 py-3 tabular-nums">{row.tickets}</td><td className="px-3 py-3 tabular-nums">{row.approaching_response}</td><td className="px-3 py-3 tabular-nums">{row.approaching_resolution}</td><td className="px-3 py-3 tabular-nums">{row.breached_response}</td><td className="px-3 py-3 tabular-nums">{row.breached_resolution}</td><td className="px-3 py-3 tabular-nums">{row.actively_overdue}</td></tr>)}</tbody></table></div>
            </section>

            <div className="grid gap-4 xl:grid-cols-2">
              <TicketList title="Approaching response deadlines" items={approachingResponse} empty="No active response deadlines are approaching in this window." />
              <TicketList title="Approaching resolution deadlines" items={approachingResolution} empty="No active resolution deadlines are approaching in this window." />
              <TicketList title="Breached response SLAs" items={breachedResponse} empty="No response SLAs have been breached in this scope." />
              <TicketList title="Breached resolution SLAs" items={breachedResolution} empty="No resolution SLAs have been breached in this scope." />
            </div>
            <p className="text-right text-[11px] text-slate-500">Updated {dateTime(overview.generated_at)} · Historical breaches remain visible; active overdue counts exclude completed timers.</p>
          </>}
    </div>
  </AgentShell>;
}
