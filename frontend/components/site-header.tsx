import Link from "next/link";

export function SiteHeader() {
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

        <nav aria-label="Primary navigation">
          <Link
            href="/tickets/new"
            className="rounded-full px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 hover:text-sky-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500"
          >
            Submit Ticket
          </Link>
        </nav>
      </div>
    </header>
  );
}
