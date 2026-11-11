"use client";

import { useEffect, useState } from "react";

import { AgentShell } from "@/components/agent-shell";
import { AgentTicketTable } from "@/components/agent-ticket-table";
import { getTeamTickets, getTeams, type Team, type TicketResponse } from "@/lib/api";

export default function AgentTeamQueuePage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);
  const [tickets, setTickets] = useState<TicketResponse[]>([]);
  const [isLoadingTeams, setIsLoadingTeams] = useState(true);
  const [isLoadingTickets, setIsLoadingTickets] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [teamRefreshKey, setTeamRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getTeams().then((result) => {
      if (cancelled) return;
      setTeams(result);
      if (result.length > 0) setIsLoadingTickets(true);
      setSelectedTeamId((current) => current !== null && result.some((team) => team.id === current) ? current : result[0]?.id ?? null);
    }).catch((reason: unknown) => {
      if (!cancelled) setError(reason instanceof Error ? reason.message : "Teams could not be loaded.");
    }).finally(() => { if (!cancelled) setIsLoadingTeams(false); });
    return () => { cancelled = true; };
  }, [teamRefreshKey]);

  useEffect(() => {
    if (selectedTeamId === null) return;
    let cancelled = false;
    getTeamTickets(selectedTeamId, { sort: "newest" }).then((result) => {
      if (!cancelled) setTickets(result);
    }).catch((reason: unknown) => {
      if (!cancelled) setError(reason instanceof Error ? reason.message : "Team tickets could not be loaded.");
    }).finally(() => { if (!cancelled) setIsLoadingTickets(false); });
    return () => { cancelled = true; };
  }, [selectedTeamId, refreshKey]);

  const selectedTeam = teams.find((team) => team.id === selectedTeamId);

  function refreshQueue() {
    setError(null);
    if (teams.length === 0) {
      setIsLoadingTeams(true);
      setTeamRefreshKey((key) => key + 1);
    } else {
      setIsLoadingTickets(true);
      setRefreshKey((key) => key + 1);
    }
  }

  return <AgentShell activeSection="team" selectedTeamName={selectedTeam?.name ?? "No team selected"} selectedTeamId={selectedTeamId} teams={teams} onTeamChange={(teamId) => { setError(null); setIsLoadingTickets(true); setSelectedTeamId(teamId); }}>
    <div className="mx-auto max-w-[1320px] space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-sky-700">Team operations</p><h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">{selectedTeam?.name ?? "Team Queue"}</h1><p className="mt-1.5 text-sm text-slate-600">Review tickets assigned to the selected support team.</p></div><button type="button" onClick={refreshQueue} disabled={isLoadingTeams || isLoadingTickets} className="rounded-md border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50">{isLoadingTickets || isLoadingTeams ? "Refreshing..." : "Refresh"}</button></div>
      {error ? <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"><p className="font-medium">Team queue could not be loaded</p><p className="mt-1">{error}</p><button type="button" onClick={refreshQueue} className="mt-3 rounded-md bg-rose-800 px-3 py-2 font-medium text-white hover:bg-rose-900">Retry</button></div> : isLoadingTeams || isLoadingTickets ? <div role="status" className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">Loading team queue...</div> : selectedTeamId === null ? <div className="rounded-lg border border-dashed border-slate-300 bg-white px-5 py-12 text-center"><p className="text-sm font-semibold text-slate-800">No teams available</p><p className="mt-1 text-sm text-slate-500">Your account is not currently associated with a support team.</p></div> : <AgentTicketTable tickets={tickets} source="team" emptyTitle="No tickets in this team queue" emptyDescription="Try another team or change your search and filters." />}
    </div>
  </AgentShell>;
}
