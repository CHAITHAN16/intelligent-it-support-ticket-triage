"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AgentShell } from "@/components/agent-shell";
import { getTicket, updateTicket, type TicketPriority, type TicketResponse, type TicketStatus } from "@/lib/api";

const ACTION_STATUSES: TicketStatus[] = ["NEW", "IN_PROGRESS", "RESOLVED", "CLOSED"];
const PRIORITIES: TicketPriority[] = ["LOW", "MEDIUM", "HIGH", "URGENT"];
const CATEGORIES = ["Network", "Security", "Software", "Other"];

function Field({ label, value }: { label: string; value: string }) {
  return <div className="border-t border-slate-200 pt-4 first:border-t-0 first:pt-0"><dt className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</dt><dd className="mt-1.5 text-sm font-medium text-slate-900">{value}</dd></div>;
}

function formattedDate(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function AgentTicketDetailPage() {
  const params = useParams<{ id: string }>();
  const ticketId = Number(params.id);
  const [ticket, setTicket] = useState<TicketResponse | null>(null);
  const [category, setCategory] = useState("");
  const [priority, setPriority] = useState<TicketPriority>("MEDIUM");
  const [status, setStatus] = useState<TicketStatus>("NEW");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const refreshTicket = useCallback(async () => {
    const result = await getTicket(ticketId);
    setTicket(result);
    setCategory(result.category ?? "");
    setPriority(result.priority);
    setStatus(result.status);
  }, [ticketId]);

  useEffect(() => {
    let cancelled = false;
    async function loadTicket() {
      if (!Number.isInteger(ticketId)) {
        if (!cancelled) {
          setError("This ticket ID is invalid.");
          setIsLoading(false);
        }
        return;
      }

      try {
        await refreshTicket();
      } catch (reason) {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "Ticket could not be loaded.");
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void loadTicket();
    return () => { cancelled = true; };
  }, [ticketId, refreshTicket]);

  async function saveChanges() {
    if (!ticket || !category.trim()) { setError("Category is required."); return; }
    setIsSaving(true); setError(null); setSaveMessage(null);
    try { await updateTicket(ticket.id, { category: category.trim(), priority, status }); await refreshTicket(); setSaveMessage("Ticket updated."); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Ticket update failed."); }
    finally { setIsSaving(false); }
  }

  return <AgentShell selectedTeamName={ticket?.assigned_team_name ?? "General IT Support"}>
    <div className="mx-auto max-w-5xl">
      <Link href="/agent" className="text-sm font-semibold text-sky-700 hover:text-sky-900">&larr; Back to queue</Link>
      {isLoading ? <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">Loading ticket...</div> : error && !ticket ? <div role="alert" className="mt-8 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div> : ticket ? <div className="mt-6 space-y-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start"><div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-600">Ticket #{ticket.id}</p><h1 className="mt-2 text-4xl font-semibold tracking-[-0.04em] text-slate-950">{ticket.title}</h1></div><span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700">{ticket.status.replaceAll("_", " ")}</span></div>
        {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>}
        {saveMessage && <div role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{saveMessage}</div>}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Request</p><p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-slate-700">{ticket.description}</p><dl className="mt-8 grid gap-5 sm:grid-cols-2"><Field label="Category" value={ticket.category ?? "Not assigned"} /><Field label="Priority" value={ticket.priority} /><Field label="Status" value={ticket.status.replaceAll("_", " ")} /><Field label="Assigned team" value={ticket.assigned_team_name ?? "Unassigned"} /><Field label="Created" value={formattedDate(ticket.created_at)} /><Field label="Updated" value={formattedDate(ticket.updated_at)} /></dl></section>
        <section className="rounded-2xl border border-sky-100 bg-sky-50 p-6 sm:p-8"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">AI predictions</p><p className="mt-2 text-sm text-slate-600">These values support the workflow but are distinct from the current ticket fields above.</p><dl className="mt-6 grid gap-5 sm:grid-cols-2"><Field label="AI predicted category" value={ticket.ai_predicted_category ?? "Not available"} /><Field label="AI predicted priority" value={ticket.ai_predicted_priority ?? "Not available"} /><Field label="AI confidence" value={ticket.ai_confidence === null ? "Not available" : `${Math.round(ticket.ai_confidence * 100)}%`} /><Field label="AI model version" value={ticket.ai_model_version ?? "Not available"} /></dl></section>
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Agent actions</p><h2 className="mt-2 text-xl font-semibold text-slate-950">Update ticket</h2></div><span className="text-xs text-slate-500">Changes use PATCH /api/tickets/{ticket.id}</span></div><div className="mt-6 grid gap-4 sm:grid-cols-3"><label className="text-sm font-semibold text-slate-700">Category<select value={category} onChange={(event) => setCategory(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm font-normal text-slate-900"><option value="">Select category</option>{CATEGORIES.map((item) => <option key={item}>{item}</option>)}</select></label><label className="text-sm font-semibold text-slate-700">Priority<select value={priority} onChange={(event) => setPriority(event.target.value as TicketPriority)} className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm font-normal text-slate-900">{PRIORITIES.map((item) => <option key={item}>{item}</option>)}</select></label><label className="text-sm font-semibold text-slate-700">Status<select value={ACTION_STATUSES.includes(status) ? status : "NEW"} onChange={(event) => setStatus(event.target.value as TicketStatus)} className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm font-normal text-slate-900">{ACTION_STATUSES.map((item) => <option key={item}>{item.replaceAll("_", " ")}</option>)}</select></label></div><button type="button" onClick={saveChanges} disabled={isSaving} className="mt-6 rounded-full bg-sky-500 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-sky-500/20 transition hover:bg-sky-600 disabled:cursor-not-allowed disabled:bg-slate-300">{isSaving ? "Saving..." : "Save changes"}</button></section>
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Comments</p><h2 className="mt-2 text-xl font-semibold text-slate-950">Internal discussion</h2><p className="mt-2 text-sm text-slate-600">Comment submission will be enabled when a backend comments endpoint is available.</p><textarea disabled rows={4} placeholder="Comments are not available yet" className="mt-5 w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500" /><button type="button" disabled className="mt-3 rounded-full bg-slate-200 px-4 py-2 text-sm font-semibold text-slate-400">Add comment</button></section>
      </div> : null}
    </div>
  </AgentShell>;
}
