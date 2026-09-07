"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { SiteHeader } from "@/components/site-header";
import { getTicket, getTicketComments, getTicketHistory, type TicketComment, type TicketResponse, type TicketStatusHistory } from "@/lib/api";

function formattedDate(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-t border-slate-200 pt-4 first:border-t-0 first:pt-0">
      <dt className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</dt>
      <dd className="mt-1.5 text-sm font-medium text-slate-900">{value}</dd>
    </div>
  );
}

function statusClass(status: TicketResponse["status"]) {
  switch (status) {
    case "RESOLVED":
    case "CLOSED":
      return "bg-emerald-50 text-emerald-700 ring-emerald-100";
    case "IN_PROGRESS":
      return "bg-amber-50 text-amber-700 ring-amber-100";
    case "ASSIGNED":
      return "bg-sky-50 text-sky-700 ring-sky-100";
    case "WAITING_FOR_USER":
      return "bg-violet-50 text-violet-700 ring-violet-100";
    default:
      return "bg-slate-100 text-slate-700 ring-slate-200";
  }
}

function confidenceLabel(confidence: number | null) {
  return confidence === null ? "Not available" : `${Math.round(confidence * 100)}%`;
}

export default function EmployeeTicketDetailPage() {
  const params = useParams<{ id: string }>();
  const ticketId = Number(params.id);
  const [ticket, setTicket] = useState<TicketResponse | null>(null);
  const [comments, setComments] = useState<TicketComment[]>([]);
  const [history, setHistory] = useState<TicketStatusHistory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [commentsError, setCommentsError] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [commentsLoading, setCommentsLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadAll() {
      if (!Number.isInteger(ticketId)) {
        setError("This ticket ID is invalid.");
        setIsLoading(false);
        setCommentsLoading(false);
        setHistoryLoading(false);
        return;
      }

      setIsLoading(true);
      setCommentsLoading(true);
      setHistoryLoading(true);
      setError(null);
      setCommentsError(null);
      setHistoryError(null);

      try {
        const ticketResult = await getTicket(ticketId);
        if (cancelled) return;
        setTicket(ticketResult);

        const [commentsResult, historyResult] = await Promise.allSettled([
          getTicketComments(ticketId),
          getTicketHistory(ticketId),
        ]);

        if (cancelled) return;

        if (commentsResult.status === "fulfilled") {
          setComments(commentsResult.value);
        } else {
          setCommentsError(commentsResult.reason instanceof Error ? commentsResult.reason.message : "Comments could not be loaded.");
        }

        if (historyResult.status === "fulfilled") {
          setHistory(historyResult.value);
        } else {
          setHistoryError(historyResult.reason instanceof Error ? historyResult.reason.message : "Status history could not be loaded.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
          setCommentsLoading(false);
          setHistoryLoading(false);
        }
      }
    }

    void loadAll();
    return () => {
      cancelled = true;
    };
  }, [ticketId]);

  return (
    <div className="min-h-screen bg-[#f6f8fb] text-slate-950">
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-5 py-12 sm:px-8 sm:py-16">
        <div className="mx-auto max-w-5xl">
          <Link href="/tickets" className="text-sm font-semibold text-sky-700 hover:text-sky-900">
            &larr; Back to My Tickets
          </Link>

          {isLoading ? (
            <div className="mt-8 rounded-3xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500 shadow-xl shadow-slate-900/5">Loading ticket details...</div>
          ) : error && !ticket ? (
            <div role="alert" className="mt-8 rounded-3xl border border-rose-200 bg-rose-50 px-5 py-4 text-sm leading-6 text-rose-800">
              {error}
            </div>
          ) : ticket ? (
            <div className="mt-6 space-y-6">
              <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-600">Ticket #{ticket.id}</p>
                  <h1 className="mt-2 text-4xl font-semibold tracking-[-0.04em] text-slate-950">{ticket.title}</h1>
                </div>
                <span className={`rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.14em] ring-1 ring-inset ${statusClass(ticket.status)}`}>
                  {ticket.status.replaceAll("_", " ")}
                </span>
              </div>

              {error && <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>}

              <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-900/5 sm:p-8">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Request</p>
                <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-slate-700">{ticket.description}</p>
                <dl className="mt-8 grid gap-5 sm:grid-cols-2">
                  <Field label="Ticket ID" value={`#${ticket.id}`} />
                  <Field label="Category" value={ticket.category ?? "Not assigned"} />
                  <Field label="Priority" value={ticket.priority} />
                  <Field label="Status" value={ticket.status.replaceAll("_", " ")} />
                  <Field label="Assigned team" value={ticket.assigned_team_name ?? ticket.assigned_team?.name ?? "Unassigned"} />
                  <Field label="Created" value={formattedDate(ticket.created_at)} />
                  <Field label="Updated" value={formattedDate(ticket.updated_at)} />
                </dl>
              </section>

              <section className="rounded-3xl border border-sky-100 bg-sky-50 p-6 shadow-xl shadow-slate-900/5 sm:p-8">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">AI predictions</p>
                <p className="mt-2 text-sm text-slate-600">These values reflect what the triage model predicted when the ticket was created.</p>
                <dl className="mt-6 grid gap-5 sm:grid-cols-2">
                  <Field label="AI predicted category" value={ticket.ai_predicted_category ?? "Not available"} />
                  <Field label="AI predicted priority" value={ticket.ai_predicted_priority ?? "Not available"} />
                  <Field label="AI confidence" value={confidenceLabel(ticket.ai_confidence)} />
                  <Field label="AI model version" value={ticket.ai_model_version ?? "Not available"} />
                </dl>
              </section>

              <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-900/5 sm:p-8">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Comments</p>
                <h2 className="mt-2 text-xl font-semibold text-slate-950">Collaboration thread</h2>
                <div className="mt-5 space-y-3">
                  {commentsLoading ? (
                    <p className="text-sm text-slate-500">Loading comments...</p>
                  ) : commentsError ? (
                    <p role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{commentsError}</p>
                  ) : comments.length === 0 ? (
                    <p className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">No comments yet.</p>
                  ) : (
                    comments.map((comment) => (
                      <article key={comment.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
                          <span className="font-semibold text-slate-700">Author #{comment.author_id}</span>
                          <time dateTime={comment.created_at}>{formattedDate(comment.created_at)}</time>
                        </div>
                        <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">{comment.body}</p>
                      </article>
                    ))
                  )}
                </div>
              </section>

              <section className="rounded-3xl border border-sky-100 bg-sky-50 p-6 shadow-xl shadow-slate-900/5 sm:p-8">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">Status history</p>
                <h2 className="mt-2 text-xl font-semibold text-slate-950">Timeline</h2>
                {historyLoading ? (
                  <p className="mt-5 text-sm text-slate-500">Loading status history...</p>
                ) : historyError ? (
                  <p role="alert" className="mt-5 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{historyError}</p>
                ) : history.length === 0 ? (
                  <p className="mt-5 rounded-2xl border border-dashed border-sky-200 bg-white/60 px-4 py-5 text-sm text-slate-500">No status changes recorded yet.</p>
                ) : (
                  <ol className="mt-6 space-y-4 border-l border-sky-200 pl-5">
                    {history.map((entry) => (
                      <li key={entry.id} className="relative rounded-2xl border border-sky-100 bg-white p-4 shadow-sm before:absolute before:-left-[1.65rem] before:top-5 before:h-3 before:w-3 before:rounded-full before:border-2 before:border-sky-100 before:bg-sky-500">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="text-sm font-semibold text-slate-900">
                            {entry.old_status ? entry.old_status.replaceAll("_", " ") : "Initial"}
                            <span className="px-1 text-sky-600">-&gt;</span>
                            {entry.new_status.replaceAll("_", " ")}
                          </p>
                          <time dateTime={entry.changed_at} className="text-xs text-slate-500">{formattedDate(entry.changed_at)}</time>
                        </div>
                        <p className="mt-2 text-xs text-slate-500">Changed by {entry.changed_by_id === null ? "system" : `user #${entry.changed_by_id}`}</p>
                        {entry.note && <p className="mt-3 text-sm text-slate-600">{entry.note}</p>}
                      </li>
                    ))}
                  </ol>
                )}
              </section>
            </div>
          ) : null}
        </div>
      </main>
    </div>
  );
}
