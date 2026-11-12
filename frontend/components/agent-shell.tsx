"use client";

import Link from "next/link";

import type { Team } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type AgentSection = "overview" | "team" | "all" | "analytics";

const NAV_ITEMS: Array<{ section: AgentSection; href: string; label: string }> = [
  { section: "overview", href: "/agent", label: "Overview" },
  { section: "team", href: "/agent/team-queue", label: "Team Queue" },
  { section: "all", href: "/agent/tickets", label: "All Tickets" },
  { section: "analytics", href: "/agent/analytics", label: "AI Analytics" },
];

export function AgentShell({
  activeSection,
  selectedTeamName,
  selectedTeamId,
  teams = [],
  onTeamChange,
  children,
}: {
  activeSection?: AgentSection;
  selectedTeamName: string;
  selectedTeamId?: number | null;
  teams?: Team[];
  onTeamChange?: (teamId: number) => void;
  children: React.ReactNode;
}) {
  const { logout, user } = useAuth();
  const navItems = NAV_ITEMS.filter((item) => item.section !== "analytics" || user?.role === "AGENT" || user?.role === "ADMIN");

  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <header className="border-b border-slate-800 bg-[#111827] text-white">
        <div className="mx-auto flex h-16 max-w-[1600px] items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/agent" className="flex items-center gap-3" aria-label="Support agent overview">
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-blue-600 text-xs font-bold text-white">IT</span>
            <span className="text-sm font-semibold tracking-tight">IT Support <span className="font-normal text-slate-400">/ Agent workspace</span></span>
          </Link>
          <div className="flex items-center gap-3"><div className="hidden text-right sm:block"><p className="text-xs font-medium">{user?.name ?? "Support user"}</p><p className="text-[11px] text-slate-400">{user?.role === "ADMIN" ? "Administrator" : "Support agent"}</p></div><button type="button" onClick={logout} className="rounded-md border border-slate-600 px-3 py-2 text-sm font-medium text-slate-100 hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-400">Log out</button></div>
        </div>
      </header>

      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-[1600px] flex-col md:flex-row">
        <aside className="border-b border-slate-800 bg-[#111827] px-3 py-3 md:w-60 md:shrink-0 md:border-b-0 md:px-4 md:py-6">
          <p className="hidden px-3 pb-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500 md:block">Workspace</p>
          <nav aria-label="Agent workspace navigation" className="flex gap-1 overflow-x-auto md:flex-col">
            {navItems.map((item) => {
              const active = activeSection === item.section;
              return <Link key={item.section} href={item.href} aria-current={active ? "page" : undefined} className={`whitespace-nowrap rounded-md px-3 py-2.5 text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-400 ${active ? "bg-slate-800 text-white" : "text-slate-400 hover:bg-slate-800 hover:text-white"}`}>{item.label}</Link>;
            })}
          </nav>
          {activeSection === "team" && <div className="mt-5 border-t border-slate-800 pt-4 md:mt-6">
            <p className="px-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">Selected team</p>
            {onTeamChange ? <>
              <label htmlFor="team-selector" className="sr-only">Select support team</label>
              <select id="team-selector" value={selectedTeamId ?? ""} onChange={(event) => onTeamChange(Number(event.target.value))} disabled={teams.length === 0} className="mt-2 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-900 disabled:bg-slate-800">
                {teams.length === 0 ? <option value="">No teams available</option> : teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}
              </select>
            </> : <p className="mt-2 px-3 text-sm font-medium text-slate-300">{selectedTeamName}</p>}
          </div>}
        </aside>
        <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
