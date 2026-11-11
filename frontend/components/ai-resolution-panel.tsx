"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  confirmAIResolution,
  escalateAIResolution,
  getAIResolution,
  sendAIResolutionMessage,
  startAIResolution,
  type AIResolutionResponse,
  type TicketResponse,
} from "@/lib/api";

type AIResolutionPanelProps = {
  ticket: TicketResponse;
  resolutionSummary?: string | null;
  onResolved: () => Promise<void>;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function AIResolutionPanel({ ticket, resolutionSummary, onResolved }: AIResolutionPanelProps) {
  const ticketId = ticket.id;
  const [resolution, setResolution] = useState<AIResolutionResponse | null>(null);
  const [message, setMessage] = useState("");
  const [loadedTicketId, setLoadedTicketId] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isLoading = loadedTicketId !== ticketId;

  useEffect(() => {
    let cancelled = false;
    void getAIResolution(ticketId)
      .then((result) => {
        if (!cancelled) {
          setResolution(result);
          setLoadedTicketId(ticketId);
        }
      })
      .catch((cause: unknown) => {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : "AI resolution could not be loaded.");
          setLoadedTicketId(ticketId);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [ticketId]);

  async function runAction(action: () => Promise<AIResolutionResponse>): Promise<boolean> {
    setIsSubmitting(true);
    setError(null);
    try {
      const result = await action();
      setResolution(result);
      if (result.status === "RESOLVED") await onResolved();
      return true;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The request could not be completed.");
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }

  async function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body = message.trim();
    if (!body) return;
    if (await runAction(() => sendAIResolutionMessage(ticketId, body))) setMessage("");
  }

  return (
    <section className="rounded-3xl border border-teal-200 bg-white p-5 shadow-xl shadow-slate-900/5 sm:p-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-teal-800">Employee AI support</p><h2 className="mt-2 text-xl font-semibold text-slate-950">How can I help with this ticket?</h2></div>
        {!isLoading && resolution && <span className={`inline-flex w-fit rounded-full px-3 py-1.5 text-xs font-semibold ${resolution.mode === "GUIDED" ? "bg-teal-100 text-teal-900" : "bg-sky-100 text-sky-900"}`}>{ticket.status === "RESOLVED" || ticket.status === "CLOSED" ? "Ticket resolved" : resolution.mode === "GUIDED" ? "Guided resolution" : "Basic assistance"}</span>}
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-600">I can explain the ticket details, ask for useful context, and share approved knowledge guidance. Never share passwords, one-time codes, API keys, or access tokens.</p>
      <dl className="mt-4 grid gap-3 rounded-2xl bg-slate-50 p-4 text-sm sm:grid-cols-3"><div><dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Current status</dt><dd className="mt-1 font-semibold text-slate-900">{ticket.status.replaceAll("_", " ")}</dd></div><div><dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Predicted category</dt><dd className="mt-1 font-semibold text-slate-900">{ticket.ai_predicted_category ?? "Not available yet"}</dd></div><div><dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Predicted priority</dt><dd className="mt-1 font-semibold text-slate-900">{ticket.ai_predicted_priority ?? "Not available yet"}</dd></div></dl>

      {error && <p role="alert" className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</p>}
      {isLoading ? (
        <p role="status" className="mt-5 text-sm text-slate-500">Loading your assistant...</p>
      ) : resolution ? (
        <>
          {ticket.status === "RESOLVED" || ticket.status === "CLOSED" ? (
            <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 p-4"><p className="text-sm font-semibold text-emerald-900">This ticket is resolved. Troubleshooting is closed.</p><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-emerald-950">{resolutionSummary || "Review the status history above for the resolution details recorded by IT."}</p>{ticket.resolved_at && <time dateTime={ticket.resolved_at} className="mt-3 block text-xs text-emerald-800">Resolved {formatDate(ticket.resolved_at)}</time>}</div>
          ) : resolution.status === "NOT_STARTED" ? (
            <div className="mt-5">
              <p className="text-sm text-slate-600">{resolution.mode === "GUIDED" ? "This ticket meets the existing checks for guided troubleshooting using its approved knowledge article." : "Basic assistance is available while your ticket remains with the support team."}</p>
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => void runAction(() => startAIResolution(ticketId))}
                className="mt-4 inline-flex min-h-11 items-center justify-center rounded-full bg-teal-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-teal-900 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubmitting ? "Starting assistant..." : resolution.mode === "GUIDED" ? "Start Guided Resolution" : "Start Basic Assistance"}
              </button>
            </div>
          ) : null}

          {resolution.messages.length > 0 && (
            <div aria-live="polite" aria-label="Assistant conversation" className="mt-6 max-h-[32rem] space-y-3 overflow-y-auto rounded-2xl border border-slate-200 bg-slate-50 p-3 sm:p-4">
              {resolution.messages.map((entry) => (
                <article
                  key={entry.id}
                  className={`max-w-[95%] rounded-2xl border p-4 sm:max-w-[85%] ${entry.speaker === "AI" ? "border-teal-100 bg-white" : "ml-auto border-sky-100 bg-sky-50"}`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{entry.speaker === "AI" ? "IT support assistant" : "You"}</p><time dateTime={entry.created_at} className="text-[11px] text-slate-400">{formatDate(entry.created_at)}</time></div>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-800">{entry.body}</p>
                </article>
              ))}
            </div>
          )}

          {resolution.status === "ACTIVE" && ticket.status !== "RESOLVED" && ticket.status !== "CLOSED" && (
            <>
              <form onSubmit={submitMessage} className="mt-5 space-y-3">
                <label htmlFor="ai-resolution-message" className="block text-sm font-semibold text-slate-800">{resolution.mode === "GUIDED" ? "What happened after that step?" : "Ask a question or share more context"}</label>
                <textarea
                  id="ai-resolution-message"
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  maxLength={4000}
                  rows={3}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-teal-700 focus:ring-2 focus:ring-teal-700/20"
                  placeholder="Share the error, timing, and impact. Do not include passwords or codes."
                />
                <button
                  type="submit"
                  disabled={isSubmitting || !message.trim()}
                  className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isSubmitting ? "Sending..." : "Send reply"}
                </button>
              </form>
              <div className="mt-5 flex flex-wrap gap-3 border-t border-slate-200 pt-5">
                {resolution.mode === "GUIDED" && <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => void runAction(() => escalateAIResolution(ticketId))}
                  className="rounded-full border border-amber-300 bg-amber-50 px-4 py-2.5 text-sm font-semibold text-amber-900 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
                >Contact IT Support</button>}
                {resolution.mode === "GUIDED" && <span className="basis-full text-xs text-slate-500">Contacting IT hands the issue back to {resolution.assigned_team_name ?? "your assigned support team"}.</span>}
                {resolution.mode === "BASIC" && <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => void runAction(() => escalateAIResolution(ticketId))}
                  className="rounded-full border border-amber-300 bg-amber-50 px-4 py-2.5 text-sm font-semibold text-amber-900 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
                >Contact IT Support</button>}
                {resolution.mode === "GUIDED" && <>
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => void runAction(() => confirmAIResolution(ticketId))}
                  className="rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  This fixed my issue
                </button>
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => void runAction(() => escalateAIResolution(ticketId))}
                  className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Still not fixed; contact IT
                </button>
                </>}
              </div>
            </>
          )}

          {resolution.status === "ESCALATED" && <EscalationNotice reason={resolution.escalation_reason} team={resolution.assigned_team_name} />}
          {resolution.status === "ESCALATED" && <EscalationNotice reason={resolution.escalation_reason} team={resolution.assigned_team_name} />}
          {resolution.status === "RESOLVED" && ticket.status !== "RESOLVED" && ticket.status !== "CLOSED" && (
            <p role="status" className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm leading-6 text-emerald-900">
              You confirmed that the issue is fixed. The ticket is marked resolved.
            </p>
          )}
        </>
      ) : null}
    </section>
  );
}

function EscalationNotice({ reason, team }: { reason: string | null; team: string | null }) {
  const message = reason === "SECURITY_SENSITIVE"
    ? "This issue needs a support specialist and will not be handled by automated troubleshooting."
    : reason === "HARDWARE_REPAIR"
      ? "Hardware repair requires a support specialist."
      : reason === "LOW_CLASSIFICATION_CONFIDENCE"
        ? "The issue classification is uncertain, so a support specialist should review it."
        : reason === "NO_SUFFICIENT_KNOWLEDGE"
          ? "There is no sufficiently relevant approved article for automated troubleshooting."
          : reason === "AI_PROVIDER_UNAVAILABLE"
            ? "The AI service is unavailable. Your ticket remains with the support team."
            : reason === "AI_CONFIGURATION_INVALID"
              ? "Automated troubleshooting is not configured correctly. Your ticket remains with the support team."
            : reason === "EMPLOYEE_REQUESTED_HUMAN_SUPPORT"
              ? "Your request has been handed back to the support team."
              : "This issue should be handled by your support team.";

  return (
    <p role="status" className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-950">
      {message} {team ? `Assigned team: ${team}.` : "Your assigned IT team can help."}
    </p>
  );
}
