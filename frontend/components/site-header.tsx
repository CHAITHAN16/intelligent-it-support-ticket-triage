"use client";

import Link from "next/link";

import { useAuth } from "@/lib/auth";

export function SiteHeader() {
  const { user, isLoading, logout } = useAuth();

  return (
    <header className="border-b border-slate-200/80 bg-white/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8">
        <Link href="/" className="group flex items-center gap-3" aria-label="IT Support Portal home">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-500 text-sm font-bold text-white shadow-sm shadow-sky-500/25 transition-transform group-hover:-rotate-3">
            IT
          </span>
          <span>
            <span className="block text-sm font-semibold tracking-tight text-slate-950">IT Support Portal</span>
            <span className="block text-[11px] font-medium uppercase tracking-[0.18em] text-slate-500">Employee help desk</span>
          </span>
        </Link>

        <nav aria-label="Primary navigation" className="flex items-center gap-1">
          {isLoading ? <span className="px-4 py-2 text-sm text-slate-400">Loading...</span> : !user ? <Link href="/login" className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800">Sign in</Link> : user.role === "EMPLOYEE" ? <>
            <Link href="/tickets/new" className="rounded-full px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 hover:text-sky-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500">Submit Ticket</Link>
            <Link href="/tickets" className="rounded-full px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 hover:text-sky-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500">My Tickets</Link>
          </> : user.role === "AGENT" ? <Link href="/agent" className="rounded-full px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 hover:text-sky-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500">Agent Dashboard</Link> : null}
          {user && <button type="button" onClick={logout} className="ml-1 rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500">Log out</button>}
        </nav>
      </div>
    </header>
  );
}
