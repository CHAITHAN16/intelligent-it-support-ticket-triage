import Link from "next/link";

import { SiteHeader } from "@/components/site-header";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#f6f8fb] text-slate-950">
      <SiteHeader />
      <main className="mx-auto grid min-h-[calc(100vh-73px)] max-w-6xl items-center gap-12 px-5 py-16 sm:px-8 lg:grid-cols-[1.15fr_0.85fr] lg:py-24">
        <section>
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-sky-600">A clearer path to support</p>
          <h1 className="mt-5 max-w-3xl text-5xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-6xl">Tell us what is getting in your way.</h1>
          <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">Submit an IT support request and our triage service will identify the right category, priority, and support team.</p>
          <Link href="/tickets/new" className="mt-9 inline-flex items-center rounded-full bg-sky-500 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-sky-500/20 transition hover:bg-sky-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500">Submit a ticket <span className="ml-3 text-lg" aria-hidden="true">&rarr;</span></Link>
        </section>
        <aside className="relative overflow-hidden rounded-[2rem] bg-slate-950 p-7 text-white shadow-2xl shadow-slate-900/15 sm:p-9">
          <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-sky-400/20 blur-2xl" aria-hidden="true" />
          <p className="relative text-xs font-semibold uppercase tracking-[0.2em] text-sky-300">What happens next</p>
          <ol className="relative mt-8 space-y-7">
            {[["01", "Describe the issue", "Give us the context we need to help."], ["02", "AI triage", "Your request is categorized and prioritized."], ["03", "Team routing", "The right support team receives the ticket."]].map(([number, title, description]) => (
              <li key={number} className="flex gap-4"><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-slate-700 text-xs font-semibold text-sky-300">{number}</span><span><span className="block font-semibold">{title}</span><span className="mt-1 block text-sm leading-6 text-slate-400">{description}</span></span></li>
            ))}
          </ol>
        </aside>
      </main>
    </div>
  );
}
