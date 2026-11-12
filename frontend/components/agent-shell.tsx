"use client";

import Link from "next/link";
import { useEffect, useSyncExternalStore } from "react";

import type { Team } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type AgentSection = "overview" | "team" | "all" | "analytics";

const NAV_ITEMS: Array<{ section: AgentSection; href: string; label: string }> = [
  { section: "overview", href: "/agent", label: "Overview" },
  { section: "team", href: "/agent/team-queue", label: "Team Queue" },
  { section: "all", href: "/agent/tickets", label: "All Tickets" },
  { section: "analytics", href: "/agent/analytics", label: "AI Analytics" },
];

const SIDEBAR_STORAGE_KEY = "agent-sidebar-expanded";
const SIDEBAR_PREFERENCE_EVENT = "agent-sidebar-preference-change";
let memorySidebarPreference: boolean | null = null;

function getSidebarPreference() {
  try {
    const savedPreference = window.localStorage.getItem(SIDEBAR_STORAGE_KEY);
    if (savedPreference === "true") return true;
    if (savedPreference === "false") return false;
  } catch {
    // Fall back to the in-memory preference when browser storage is unavailable.
  }
  return memorySidebarPreference ?? true;
}

function subscribeToSidebarPreference(onChange: () => void) {
  window.addEventListener("storage", onChange);
  window.addEventListener(SIDEBAR_PREFERENCE_EVENT, onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener(SIDEBAR_PREFERENCE_EVENT, onChange);
  };
}

function setSidebarPreference(expanded: boolean) {
  memorySidebarPreference = expanded;
  try {
    window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(expanded));
  } catch {
    // The in-memory value remains available for this session.
  }
  window.dispatchEvent(new Event(SIDEBAR_PREFERENCE_EVENT));
}

function getServerSidebarPreference() {
  return true;
}

function NavigationIcon({ section, className = "" }: { section: AgentSection; className?: string }) {
  const paths: Record<AgentSection, React.ReactNode> = {
    overview: <><rect x="3" y="3" width="8" height="8" rx="1.5" /><rect x="13" y="3" width="8" height="5" rx="1.5" /><rect x="13" y="10" width="8" height="11" rx="1.5" /><rect x="3" y="13" width="8" height="8" rx="1.5" /></>,
    team: <><path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="10" cy="7" r="4" /><path d="M20 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></>,
    all: <><rect x="4" y="4" width="16" height="17" rx="2" /><path d="M8 8h8M8 12h8M8 16h5" /><path d="M8 2v4M16 2v4" /></>,
    analytics: <><path d="M3 3v18h18" /><path d="m19 9-5 5-4-4-5 5" /></>,
  };
  return <svg aria-hidden="true" className={`h-5 w-5 shrink-0 ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[section]}</svg>;
}

function SidebarToggleIcon({ expanded }: { expanded: boolean }) {
  return <svg aria-hidden="true" className="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2.5" y="3" width="15" height="14" rx="2" />
    <path d="M7.5 3v14M11 7l2.5 3-2.5 3" transform={expanded ? undefined : "translate(24 0) scale(-1 1)"} />
  </svg>;
}

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
  const sidebarExpanded = useSyncExternalStore(subscribeToSidebarPreference, getSidebarPreference, getServerSidebarPreference);

  useEffect(() => {
    const htmlOverflow = document.documentElement.style.overflow;
    const bodyOverflow = document.body.style.overflow;
    document.documentElement.style.overflow = "hidden";
    document.body.style.overflow = "hidden";
    return () => {
      document.documentElement.style.overflow = htmlOverflow;
      document.body.style.overflow = bodyOverflow;
    };
  }, []);

  function renderNavigation(mobile = false) {
    return <>
      {navItems.map((item) => {
        const active = activeSection === item.section;
        return <Link key={item.section} href={item.href} aria-label={item.label} aria-current={active ? "page" : undefined} title={sidebarExpanded ? undefined : item.label} className={`flex min-h-10 items-center gap-3 whitespace-nowrap rounded-md py-2.5 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-400 ${mobile ? "px-3" : sidebarExpanded ? "px-3" : "justify-center px-0"} ${active ? "bg-slate-800 text-white" : "text-slate-400 hover:bg-slate-800 hover:text-white"}`}>
          <NavigationIcon section={item.section} />
          <span className={mobile || sidebarExpanded ? "" : "sr-only"}>{item.label}</span>
        </Link>;
      })}
      {mobile && activeSection === "team" && onTeamChange && <label className="sr-only" htmlFor="mobile-team-selector">Select support team</label>}
      {mobile && activeSection === "team" && onTeamChange && <select id="mobile-team-selector" aria-label="Select support team" value={selectedTeamId ?? ""} onChange={(event) => onTeamChange(Number(event.target.value))} disabled={teams.length === 0} className="min-w-36 rounded-md border border-slate-700 bg-slate-900 px-2 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-900 disabled:bg-slate-800">
        {teams.length === 0 ? <option value="">No teams available</option> : teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}
      </select>}
    </>;
  }

  return (
    <div className="fixed inset-0 h-dvh w-full overflow-hidden bg-slate-50 text-slate-950">
      <aside id="agent-sidebar" className={`fixed inset-y-0 left-0 z-30 hidden h-dvh flex-col overflow-y-auto border-r border-slate-800 bg-[#111827] py-6 transition-[width,padding] duration-200 ease-in-out md:flex ${sidebarExpanded ? "w-60 px-4" : "w-[4.5rem] px-2"}`}>
        <div className={`mb-8 flex items-center ${sidebarExpanded ? "justify-between gap-2 px-2" : "flex-col justify-center gap-3"}`}>
          <Link href="/agent" className="flex items-center gap-3" aria-label="Support agent overview" title={sidebarExpanded ? undefined : "IT Support home"}>
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-blue-600 text-xs font-bold text-white">IT</span>
            {sidebarExpanded && <span className="text-sm font-semibold tracking-tight text-white">IT Support</span>}
          </Link>
          <button type="button" onClick={() => setSidebarPreference(!sidebarExpanded)} aria-label={sidebarExpanded ? "Collapse sidebar" : "Expand sidebar"} aria-expanded={sidebarExpanded} aria-controls="agent-sidebar" title={sidebarExpanded ? "Collapse sidebar" : "Expand sidebar"} className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-slate-400 transition-colors hover:bg-slate-800 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-400">
            <SidebarToggleIcon expanded={sidebarExpanded} />
          </button>
        </div>
        {sidebarExpanded && <p className="px-3 pb-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">Workspace</p>}
        <nav aria-label="Agent workspace navigation" className="flex flex-col gap-1">
          {renderNavigation()}
        </nav>
        {activeSection === "team" && <div className={`mt-5 border-t border-slate-800 pt-4 ${sidebarExpanded ? "" : "flex justify-center"}`}>
          {sidebarExpanded && <p className="px-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">Selected team</p>}
          {onTeamChange ? <>
            <label htmlFor="team-selector" className="sr-only">Select support team</label>
            {sidebarExpanded ? <select id="team-selector" value={selectedTeamId ?? ""} onChange={(event) => onTeamChange(Number(event.target.value))} disabled={teams.length === 0} className="mt-2 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-900 disabled:bg-slate-800">
              {teams.length === 0 ? <option value="">No teams available</option> : teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}
            </select> : <div className="relative flex h-10 w-10 items-center justify-center rounded-md text-slate-400 hover:bg-slate-800 hover:text-white focus-within:outline-2 focus-within:outline-blue-400" title={selectedTeamName}>
              <NavigationIcon section="team" />
              <select id="team-selector" aria-label={`Select support team. Current team: ${selectedTeamName}`} value={selectedTeamId ?? ""} onChange={(event) => onTeamChange(Number(event.target.value))} disabled={teams.length === 0} className="absolute inset-0 h-full w-full cursor-pointer opacity-0 disabled:cursor-not-allowed">
                {teams.length === 0 ? <option value="">No teams available</option> : teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}
              </select>
            </div>}
          </> : <p className={`mt-2 text-sm font-medium text-slate-300 ${sidebarExpanded ? "px-3" : "sr-only"}`} title={selectedTeamName}>{sidebarExpanded ? selectedTeamName : "Selected team"}</p>}
        </div>}
        <div className={`mt-auto border-t border-slate-800 pt-4 text-xs text-slate-500 ${sidebarExpanded ? "px-3" : "flex justify-center"}`}>
          {sidebarExpanded ? <><span className="block truncate text-slate-300">{user?.name ?? "Support user"}</span><span className="mt-1 block">{user?.role === "ADMIN" ? "Administrator" : "Support agent"}</span></> : <span aria-label={`${user?.name ?? "Support user"}, ${user?.role === "ADMIN" ? "Administrator" : "Support agent"}`} title={`${user?.name ?? "Support user"} · ${user?.role === "ADMIN" ? "Administrator" : "Support agent"}`} className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-800 text-xs font-semibold text-slate-200">{(user?.name ?? "S").trim().charAt(0).toUpperCase()}</span>}
        </div>
      </aside>

      <header className={`fixed inset-x-0 top-0 z-20 h-16 border-b border-slate-800 bg-[#111827] text-white transition-[left] duration-200 ease-in-out ${sidebarExpanded ? "md:left-60" : "md:left-[4.5rem]"}`}>
        <div className="flex h-full min-w-0 items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/agent" className="flex min-w-0 items-center gap-3" aria-label="Support agent overview">
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-blue-600 text-xs font-bold text-white">IT</span>
            <span className="min-w-0 truncate text-sm font-semibold tracking-tight">IT Support <span className="font-normal text-slate-400">/ Agent workspace</span></span>
          </Link>
          <div className="flex items-center gap-3"><div className="hidden text-right sm:block"><p className="text-xs font-medium">{user?.name ?? "Support user"}</p><p className="text-[11px] text-slate-400">{user?.role === "ADMIN" ? "Administrator" : "Support agent"}</p></div><button type="button" onClick={logout} className="rounded-md border border-slate-600 px-3 py-2 text-sm font-medium text-slate-100 hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-400">Log out</button></div>
        </div>
      </header>

      <nav aria-label="Agent workspace navigation" className="fixed inset-x-0 top-16 z-20 flex h-12 items-center gap-1 overflow-x-auto border-b border-slate-800 bg-[#111827] px-3 md:hidden">
        {renderNavigation(true)}
      </nav>
      <main id="agent-main" aria-label="Agent workspace content" className={`fixed inset-x-0 bottom-0 top-28 overflow-x-hidden overflow-y-auto overscroll-contain px-4 py-6 focus:outline-none sm:px-6 sm:py-8 md:top-16 md:px-8 transition-[left] duration-200 ease-in-out ${sidebarExpanded ? "md:left-60" : "md:left-[4.5rem]"}`} tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
