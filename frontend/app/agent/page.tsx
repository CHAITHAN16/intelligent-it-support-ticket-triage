"use client";

import { useEffect, useMemo, useState } from "react";

import { AgentShell } from "@/components/agent-shell";
import { AgentTicketTable } from "@/components/agent-ticket-table";
import { getTeamTickets, getTeams, type Team, type TicketPriority, type TicketResponse, type TicketStatus } from "@/lib/api";

const STATUS_OPTIONS: Array<"ALL" | TicketStatus> = ["ALL", "NEW", "ASSIGNED", "IN_PROGRESS", "WAITING_FOR_USER", "RESOLVED", "CLOSED"];
const PRIORITY_OPTIONS: Array<"ALL" | TicketPriority> = ["ALL", "LOW", "MEDIUM", "HIGH", "URGENT"];
const CATEGORY_OPTIONS = ["ALL", "Network", "Security", "Software", "Other"];

type SortMode = "newest" | "oldest" | "priority";

function Stat({ label, value, accent }: { label: string; value: number; accent: string }) {
  return <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p><p className={`mt-3 text-3xl font-semibold tracking-tight ${accent}`}>{value}</p></div>;
}

export default function AgentDashboardPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);
  const [statsTickets, setStatsTickets] = useState<TicketResponse[]>([]);
  const [queueTickets, setQueueTickets] = useState<TicketResponse[]>([]);
  const [status, setStatus] = useState<"ALL" | TicketStatus>("ALL");
  const [priority, setPriority] = useState<"ALL" | TicketPriority>("ALL");
  const [category, setCategory] = useState("ALL");
  const [sort, setSort] = useState<SortMode>("newest");
  const [isTeamsLoading, setIsTeamsLoading] = useState(true);
  const [isQueueLoading, setIsQueueLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getTeams()
      .then((result) => {
        setTeams(result);
        setSelectedTeamId((current) => current ?? result[0]?.id ?? null);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Teams could not be loaded."))
      .finally(() => setIsTeamsLoading(false));
  }, []);

  const selectedTeam = useMemo(() => teams.find((team) => team.id === selectedTeamId), [teams, selectedTeamId]);

  useEffect(() => {
    if (selectedTeamId === null) return;
    const teamId: number = selectedTeamId;

    async function loadQueue() {
      const filters = {
        ...(status !== "ALL" ? { status } : {}),
        ...(priority !== "ALL" ? { priority } : {}),
        ...(category !== "ALL" ? { category } : {}),
        sort,
      };
      setIsQueueLoading(true);
      setError(null);
      try {
        const [allTeamTickets, filteredTeamTickets] = await Promise.all([
          getTeamTickets(teamId, { sort: "newest" }),
          getTeamTickets(teamId, filters),
        ]);
        setStatsTickets(allTeamTickets);
        setQueueTickets(filteredTeamTickets);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Tickets could not be loaded.");
      } finally {
        setIsQueueLoading(false);
      }
    }

    void loadQueue();
  }, [selectedTeamId, status, priority, category, sort]);

  const openCount = statsTickets.filter((ticket) => !["IN_PROGRESS", "RESOLVED", "CLOSED"].includes(ticket.status)).length;
  const inProgressCount = statsTickets.filter((ticket) => ticket.status === "IN_PROGRESS").length;
  const resolvedCount = statsTickets.filter((ticket) => ticket.status === "RESOLVED").length;

  return <AgentShell selectedTeamName={selectedTeam?.name ?? (isTeamsLoading ? "Loading teams..." : "No teams available")} selectedTeamId={selectedTeamId} teams={teams} onTeamChange={setSelectedTeamId}>
    <div className="flex flex-col gap-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-600">Operations overview</p><h1 className="mt-2 text-4xl font-semibold tracking-[-0.04em] text-slate-950">{selectedTeam?.name ?? "Team queue"}</h1><p className="mt-2 text-sm text-slate-600">Live queue from the support ticket service.</p></div><span className="w-fit rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">Temporary team view</span></div>
      {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Stat label="Open tickets" value={openCount} accent="text-sky-700" /><Stat label="In progress" value={inProgressCount} accent="text-amber-600" /><Stat label="Resolved" value={resolvedCount} accent="text-emerald-600" /><Stat label="Total tickets" value={statsTickets.length} accent="text-slate-950" /></div>
      <section><div className="mb-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div><h2 className="text-xl font-semibold text-slate-950">Ticket queue</h2><p className="mt-1 text-sm text-slate-500">{queueTickets.length} matching ticket{queueTickets.length === 1 ? "" : "s"}</p></div><div className="flex flex-wrap gap-2"><select aria-label="Filter by status" value={status} onChange={(event) => setStatus(event.target.value as "ALL" | TicketStatus)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700"><option value="ALL">All statuses</option>{STATUS_OPTIONS.slice(1).map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}</select><select aria-label="Filter by priority" value={priority} onChange={(event) => setPriority(event.target.value as "ALL" | TicketPriority)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700"><option value="ALL">All priorities</option>{PRIORITY_OPTIONS.slice(1).map((item) => <option key={item} value={item}>{item}</option>)}</select><select aria-label="Filter by category" value={category} onChange={(event) => setCategory(event.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700">{CATEGORY_OPTIONS.map((item) => <option key={item} value={item}>{item === "ALL" ? "All categories" : item}</option>)}</select><select aria-label="Sort tickets" value={sort} onChange={(event) => setSort(event.target.value as SortMode)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700"><option value="newest">Newest</option><option value="oldest">Oldest</option><option value="priority">Priority</option></select></div></div>{isTeamsLoading || isQueueLoading ? <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">Loading ticket queue...</div> : queueTickets.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center"><p className="font-semibold text-slate-800">No tickets match this view</p><p className="mt-1 text-sm text-slate-500">Try another team or filter.</p></div> : <AgentTicketTable tickets={queueTickets} />}</section>
    </div>
  </AgentShell>;
}
