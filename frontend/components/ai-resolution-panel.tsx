"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  confirmAIResolution,
  escalateAIResolution,
  getAIResolution,
  sendAIResolutionMessage,
  startAIResolution,
  type AIResolutionResponse,
} from "@/lib/api";

type AIResolutionPanelProps = {
  ticketId: number;
  onResolved: () => Promise<void>;
};

export function AIResolutionPanel({ ticketId, onResolved }: AIResolutionPanelProps) {
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
    <section className="rounded-3xl border border-teal-200 bg-white p-6 shadow-xl shadow-slate-900/5 sm:p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-teal-800">Guided resolution</p>
      <h2 className="mt-2 text-xl font-semibold text-slate-950">Work through a verified knowledge article</h2>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        Troubleshooting is based on the approved article for this issue. Do not enter passwords, access tokens, or confidential information.
      </p>

      {error && <p role="alert" className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</p>}
      {isLoading ? (
        <p className="mt-5 text-sm text-slate-500">Loading resolution options...</p>
      ) : resolution ? (
        <>
          {resolution.status === "NOT_STARTED" && resolution.eligible && (
            <div className="mt-5">
              <p className="text-sm text-slate-600">Starting shares the ticket details and replies with the organization-approved AI provider.</p>
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => void runAction(() => startAIResolution(ticketId))}
                className="mt-4 rounded-lg bg-teal-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-900 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubmitting ? "Starting..." : "Start troubleshooting"}
              </button>
            </div>
          )}

          {resolution.status === "NOT_STARTED" && !resolution.eligible && (
            <EscalationNotice reason={resolution.escalation_reason} team={resolution.assigned_team_name} />
          )}

          {resolution.messages.length > 0 && (
            <div aria-live="polite" className="mt-6 space-y-3">
              {resolution.messages.map((entry) => (
                <article
                  key={entry.id}
                  className={`rounded-xl border p-4 ${entry.speaker === "AI" ? "border-teal-100 bg-teal-50" : "border-slate-200 bg-slate-50"}`}
                >
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                    {entry.speaker === "AI" ? "Troubleshooting assistant" : "You"}
                  </p>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-800">{entry.body}</p>
                </article>
              ))}
            </div>
          )}

          {resolution.status === "ACTIVE" && (
            <>
              <form onSubmit={submitMessage} className="mt-5 space-y-3">
                <label htmlFor="ai-resolution-message" className="block text-sm font-semibold text-slate-800">What happened after that step?</label>
                <textarea
                  id="ai-resolution-message"
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  maxLength={4000}
                  rows={3}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-teal-700 focus:ring-2 focus:ring-teal-700/20"
                  placeholder="Describe the result without including secrets or confidential data."
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
              </div>
            </>
          )}

          {resolution.status === "ESCALATED" && <EscalationNotice reason={resolution.escalation_reason} team={resolution.assigned_team_name} />}
          {resolution.status === "RESOLVED" && (
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