import Link from "next/link";

import type { Team } from "@/lib/api";

export function AgentShell({
  selectedTeamName,
  selectedTeamId,
  teams = [],
  onTeamChange,
  children,
}: {
  selectedTeamName: string;
  selectedTeamId?: number | null;
  teams?: Team[];
  onTeamChange?: (teamId: number) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-[#f6f8fb] text-slate-950">
      <header className="border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between px-5 py-4 sm:px-8">
          <Link href="/agent" className="flex items-center gap-3" aria-label="Support agent dashboard">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-950 text-sm font-bold text-white">IT</span>
            <span>
              <span className="block text-sm font-semibold tracking-tight text-slate-950">IT Support Portal</span>
              <span className="block text-[11px] font-medium uppercase tracking-[0.18em] text-slate-500">Support Agent</span>
            </span>
          </Link>
          <Link href="/tickets/new" className="rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-sky-200 hover:bg-sky-50 hover:text-sky-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500">
            Employee Portal
          </Link>
        </div>
      </header>

      <div className="mx-auto flex max-w-[1440px] flex-col lg:flex-row">
        <aside className="border-b border-slate-200 px-5 py-6 lg:min-h-[calc(100vh-73px)] lg:w-72 lg:shrink-0 lg:border-b-0 lg:border-r lg:px-6 lg:py-9">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Team queue</p>
          <p className="mt-2 text-sm leading-6 text-slate-600">Select a simulated team view while agent roles are not yet enabled.</p>
          {onTeamChange ? (
            <>
              <label htmlFor="team-selector" className="sr-only">Select support team</label>
              <select
                id="team-selector"
                value={selectedTeamId ?? ""}
                onChange={(event) => onTeamChange(Number(event.target.value))}
                className="mt-5 w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm font-semibold text-slate-800 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-500/10"
              >
                <option value="" disabled>Select a team</option>
                {teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}
              </select>
            </>
          ) : (
            <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm font-semibold text-slate-700">{selectedTeamName}</div>
          )}
        </aside>
        <main className="min-w-0 flex-1 px-5 py-8 sm:px-8 lg:px-10 lg:py-10">{children}</main>
      </div>
    </div>
  );
}
