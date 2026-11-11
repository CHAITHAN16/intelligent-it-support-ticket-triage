"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AgentShell } from "@/components/agent-shell";
import {
  createTicketComment,
  getTeams,
  getTicket,
  getTicketAssignmentHistory,
  getTicketComments,
  getTicketFieldHistory,
  getTicketHistory,
  updateTicket,
  type Team,
  type TicketAssignmentHistory,
  type TicketComment,
  type TicketFieldHistory,
  type TicketPriority,
  type TicketResponse,
  type TicketStatus,
  type TicketStatusHistory,
} from "@/lib/api";

const ACTION_STATUSES: TicketStatus[] = ["NEW", "ASSIGNED", "IN_PROGRESS", "WAITING_FOR_USER", "RESOLVED", "CLOSED"];
const PRIORITIES: TicketPriority[] = ["LOW", "MEDIUM", "HIGH", "URGENT"];
const CATEGORIES = ["Network", "Security", "Software", "Other"];

function formattedDate(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function confidenceLabel(value: number | null) {
  return value === null ? "Not available" : `${Math.round(value * 100)}%`;
}

function statusTone(status: TicketStatus) {
  if (status === "RESOLVED" || status === "CLOSED") return "bg-emerald-50 text-emerald-800 ring-emerald-200";
  if (status === "WAITING_FOR_USER") return "bg-violet-50 text-violet-800 ring-violet-200";
  if (status === "IN_PROGRESS") return "bg-amber-50 text-amber-800 ring-amber-200";
  if (status === "ASSIGNED") return "bg-blue-50 text-blue-800 ring-blue-200";
  return "bg-slate-100 text-slate-700 ring-slate-200";
}

function priorityTone(priority: TicketPriority) {
  if (priority === "URGENT") return "text-rose-700";
  if (priority === "HIGH") return "text-orange-700";
  if (priority === "MEDIUM") return "text-amber-700";
  return "text-slate-600";
}

function Section({ title, description, children, className = "" }: { title: string; description?: string; children: React.ReactNode; className?: string }) {
  return <section className={`rounded-lg border border-slate-200 bg-white ${className}`}>
    <div className="border-b border-slate-100 px-4 py-3 sm:px-5">
      <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
      {description && <p className="mt-1 text-xs leading-5 text-slate-500">{description}</p>}
    </div>
    <div className="p-4 sm:p-5">{children}</div>
  </section>;
}

function Detail({ label, value, valueClass = "" }: { label: string; value: string; valueClass?: string }) {
  return <div className="flex items-start justify-between gap-3 border-b border-slate-100 py-2.5 last:border-0 last:pb-0 first:pt-0">
    <dt className="text-xs text-slate-500">{label}</dt>
    <dd className={`max-w-[65%] text-right text-xs font-medium text-slate-800 ${valueClass}`}>{value}</dd>
  </div>;
}

export default function AgentTicketDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const origin = searchParams.get("from");
  const originatingTeamId = Number(searchParams.get("teamId"));
  const returnTo = origin === "all" ? "/agent/tickets" : origin === "overview" ? "/agent" : origin === "team" && Number.isInteger(originatingTeamId) && originatingTeamId > 0 ? `/agent/team-queue?teamId=${originatingTeamId}` : "/agent/team-queue";
  const returnLabel = origin === "all" ? "All tickets" : origin === "overview" ? "Overview" : "Team queue";
  const activeSection = origin === "all" ? "all" : origin === "overview" ? "overview" : "team";
  const ticketId = Number(params.id);
  const [ticket, setTicket] = useState<TicketResponse | null>(null);
  const [category, setCategory] = useState("");
  const [subcategory, setSubcategory] = useState("");
  const [priority, setPriority] = useState<TicketPriority>("MEDIUM");
  const [status, setStatus] = useState<TicketStatus>("NEW");
  const [assignedTeamId, setAssignedTeamId] = useState("");
  const [teams, setTeams] = useState<Team[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [retryCount, setRetryCount] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [comments, setComments] = useState<TicketComment[]>([]);
  const [history, setHistory] = useState<TicketStatusHistory[]>([]);
  const [fieldHistory, setFieldHistory] = useState<TicketFieldHistory[]>([]);
  const [assignmentHistory, setAssignmentHistory] = useState<TicketAssignmentHistory[]>([]);
  const [isCommentsLoading, setIsCommentsLoading] = useState(true);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);
  const [commentsError, setCommentsError] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [isAuditLoading, setIsAuditLoading] = useState(true);
  const [commentBody, setCommentBody] = useState("");
  const [isCommentPosting, setIsCommentPosting] = useState(false);
  const [commentSubmitError, setCommentSubmitError] = useState<string | null>(null);
  const [commentSuccess, setCommentSuccess] = useState<string | null>(null);
  const [resolutionNote, setResolutionNote] = useState("");

  const refreshTicket = useCallback(async () => {
    const result = await getTicket(ticketId);
    setTicket(result);
    setCategory(result.category ?? "");
    setSubcategory(result.subcategory ?? "");
    setPriority(result.priority);
    setStatus(result.status);
    setAssignedTeamId(result.assigned_team_id?.toString() ?? "");
    setResolutionNote("");
  }, [ticketId]);

  const refreshComments = useCallback(async () => {
    setIsCommentsLoading(true);
    setCommentsError(null);
    try { setComments(await getTicketComments(ticketId)); }
    catch (reason) { setCommentsError(reason instanceof Error ? reason.message : "Comments could not be loaded."); }
    finally { setIsCommentsLoading(false); }
  }, [ticketId]);

  const refreshHistory = useCallback(async () => {
    setIsHistoryLoading(true);
    setHistoryError(null);
    try { setHistory(await getTicketHistory(ticketId)); }
    catch (reason) { setHistoryError(reason instanceof Error ? reason.message : "Status history could not be loaded."); }
    finally { setIsHistoryLoading(false); }
  }, [ticketId]);

  const refreshAuditHistory = useCallback(async () => {
    setIsAuditLoading(true);
    setAuditError(null);
    try {
      const [fields, assignments] = await Promise.all([getTicketFieldHistory(ticketId), getTicketAssignmentHistory(ticketId)]);
      setFieldHistory(fields);
      setAssignmentHistory(assignments);
    } catch (reason) { setAuditError(reason instanceof Error ? reason.message : "Override history could not be loaded."); }
    finally { setIsAuditLoading(false); }
  }, [ticketId]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      setError(null);
      if (!Number.isInteger(ticketId) || ticketId < 1) {
        setError("This ticket ID is invalid.");
        setIsLoading(false);
        return;
      }
      try { await refreshTicket(); }
      catch (reason) { if (!cancelled) setError(reason instanceof Error ? reason.message : "Ticket could not be loaded."); }
      finally { if (!cancelled) setIsLoading(false); }

      const [commentsResult, historyResult, teamsResult] = await Promise.allSettled([
        getTicketComments(ticketId), getTicketHistory(ticketId), getTeams(),
      ]);
      if (cancelled) return;
      if (commentsResult.status === "fulfilled") setComments(commentsResult.value);
      else setCommentsError(commentsResult.reason instanceof Error ? commentsResult.reason.message : "Comments could not be loaded.");
      setIsCommentsLoading(false);
      if (historyResult.status === "fulfilled") setHistory(historyResult.value);
      else setHistoryError(historyResult.reason instanceof Error ? historyResult.reason.message : "Status history could not be loaded.");
      setIsHistoryLoading(false);
      if (teamsResult.status === "fulfilled") setTeams(teamsResult.value);
      void refreshAuditHistory();
    }
    void load();
    return () => { cancelled = true; };
  }, [ticketId, retryCount, refreshAuditHistory, refreshTicket]);

  async function saveChanges() {
    if (!ticket) return;
    const resolving = status === "RESOLVED" && ticket.status !== "RESOLVED";
    if (resolving && resolutionNote.trim().length < 10) {
      setError("Add a meaningful resolution note of at least 10 characters before resolving.");
      return;
    }
    setIsSaving(true); setError(null); setSaveMessage(null);
    try {
      const teamId = Number(assignedTeamId);
      await updateTicket(ticket.id, {
        ...(category.trim() ? { category: category.trim(), subcategory: subcategory.trim() || null } : {}),
        priority, status, ...(teamId ? { assigned_team_id: teamId } : {}),
        ...(resolving ? { resolution_note: resolutionNote.trim() } : {}),
      });
      await Promise.all([refreshTicket(), refreshHistory(), refreshAuditHistory()]);
      setSaveMessage(resolving ? "Ticket resolved." : status === "CLOSED" && ticket.status !== "CLOSED" ? "Ticket closed." : "Ticket updated.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Ticket update failed."); }
    finally { setIsSaving(false); }
  }

  async function submitComment() {
    const body = commentBody.trim();
    if (!ticket || !body) { setCommentSubmitError("Enter a comment before submitting."); return; }
    setIsCommentPosting(true); setCommentSubmitError(null); setCommentSuccess(null);
    try {
      await createTicketComment(ticket.id, body);
      setCommentBody("");
      await refreshComments();
      setCommentSuccess("Comment added.");
    } catch (reason) { setCommentSubmitError(reason instanceof Error ? reason.message : "Comment could not be added."); }
    finally { setIsCommentPosting(false); }
  }

  const latestResolution = [...history].reverse().find((entry) => entry.new_status === "RESOLVED");
  const humanAssignments = assignmentHistory.filter((entry) => entry.source === "HUMAN");

  return <AgentShell activeSection={activeSection} selectedTeamName={ticket?.assigned_team_name ?? "Agent workspace"}>
    <div className="mx-auto max-w-[1440px]">
      <Link href={returnTo} className="inline-flex items-center gap-2 text-sm font-medium text-sky-800 hover:text-sky-950 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sky-700">
        <span aria-hidden="true">←</span> Back to {returnLabel}
      </Link>

      {isLoading ? <div role="status" className="mt-5 rounded-lg border border-slate-200 bg-white px-5 py-12 text-center text-sm text-slate-500">Loading ticket workspace…</div>
        : error && !ticket ? <div role="alert" className="mt-5 rounded-lg border border-rose-200 bg-white p-5">
          <p className="text-sm font-semibold text-rose-900">Ticket could not be loaded</p><p className="mt-1 text-sm text-rose-800">{error}</p>
          <button type="button" onClick={() => setRetryCount((value) => value + 1)} className="mt-4 rounded-md bg-slate-900 px-3.5 py-2 text-sm font-medium text-white hover:bg-slate-700">Retry</button>
        </div>
        : ticket && <>
          <header className="mt-5 border-b border-slate-200 pb-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-semibold text-slate-500">#{ticket.id}</span>
                  <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ring-1 ring-inset ${statusTone(ticket.status)}`}>{ticket.status.replaceAll("_", " ")}</span>
                  <span className={`text-xs font-semibold ${priorityTone(ticket.priority)}`}>{ticket.priority} priority</span>
                </div>
                <h1 className="mt-2 break-words text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">{ticket.title}</h1>
              </div>
              <Link href={returnTo} className="hidden shrink-0 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 sm:inline-flex">Return to queue</Link>
            </div>
            {(error || saveMessage) && <div className={`mt-4 rounded-md border px-3 py-2 text-sm ${error ? "border-rose-200 bg-rose-50 text-rose-800" : "border-emerald-200 bg-emerald-50 text-emerald-800"}`} role={error ? "alert" : "status"}>{error ?? saveMessage}</div>}
          </header>

          <div className="mt-5 grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
            <main className="min-w-0 space-y-5">
              <Section title="Conversation" description="Ticket request and team discussion, in chronological order.">
                <article className="border-b border-slate-100 pb-5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div><p className="text-sm font-semibold text-slate-900">Employee request</p><p className="mt-0.5 text-xs text-slate-500">Ticket creator · User #{ticket.creator_id}</p></div>
                    <time dateTime={ticket.created_at} className="text-xs text-slate-500">{formattedDate(ticket.created_at)}</time>
                  </div>
                  <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-slate-700">{ticket.description}</p>
                </article>

                <div className="pt-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Team discussion</h3>
                  <div className="mt-3 space-y-3">
                    {isCommentsLoading ? <p role="status" className="text-sm text-slate-500">Loading discussion…</p>
                      : commentsError ? <div role="alert" className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{commentsError}<button type="button" onClick={() => void refreshComments()} className="ml-2 font-semibold underline">Retry</button></div>
                        : comments.length === 0 ? <p className="rounded-md border border-dashed border-slate-200 px-3 py-5 text-center text-sm text-slate-500">No team comments yet.</p>
                          : comments.map((comment) => <article key={comment.id} className="rounded-md border border-slate-200 bg-slate-50/70 p-3.5">
                            <div className="flex flex-wrap items-center justify-between gap-2"><p className="text-xs font-semibold text-slate-700">Team comment · User #{comment.author_id}</p><time dateTime={comment.created_at} className="text-xs text-slate-500">{formattedDate(comment.created_at)}</time></div>
                            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{comment.body}</p>
                          </article>)}
                  </div>
                </div>

                <form onSubmit={(event) => { event.preventDefault(); void submitComment(); }} className="mt-5 border-t border-slate-100 pt-4">
                  <label htmlFor="new-comment" className="text-sm font-semibold text-slate-800">Add team comment</label>
                  <textarea id="new-comment" rows={3} maxLength={5000} value={commentBody} onChange={(event) => { setCommentBody(event.target.value); setCommentSubmitError(null); setCommentSuccess(null); }} placeholder="Share an update with the support team" disabled={isCommentPosting} className="mt-2 w-full resize-y rounded-md border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-sky-600 focus:ring-2 focus:ring-sky-100 disabled:bg-slate-50" />
                  <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                    <div aria-live="polite" className="text-xs">{commentSubmitError && <span role="alert" className="text-rose-700">{commentSubmitError}</span>}{commentSuccess && <span role="status" className="text-emerald-700">{commentSuccess}</span>}</div>
                    <button type="submit" disabled={isCommentPosting || !commentBody.trim()} className="rounded-md bg-slate-900 px-3.5 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50">{isCommentPosting ? "Adding…" : "Add comment"}</button>
                  </div>
                </form>
              </Section>

              <Section title="Status history" description="Recorded ticket status transitions.">
                {isHistoryLoading ? <p role="status" className="text-sm text-slate-500">Loading timeline…</p>
                  : historyError ? <p role="alert" className="text-sm text-rose-800">{historyError}<button type="button" onClick={() => void refreshHistory()} className="ml-2 font-semibold underline">Retry</button></p>
                    : history.length === 0 ? <p className="text-sm text-slate-500">No status changes recorded yet.</p>
                      : <ol className="space-y-4 border-l border-slate-200 pl-4">{history.map((entry) => <li key={entry.id} className="relative before:absolute before:-left-[1.32rem] before:top-1 before:h-2.5 before:w-2.5 before:rounded-full before:bg-sky-600 before:ring-4 before:ring-white">
                        <div className="flex flex-wrap justify-between gap-2"><p className="text-sm font-medium text-slate-800">{entry.old_status?.replaceAll("_", " ") ?? "Created"} <span className="px-1 text-slate-400">→</span> {entry.new_status.replaceAll("_", " ")}</p><time dateTime={entry.changed_at} className="text-xs text-slate-500">{formattedDate(entry.changed_at)}</time></div>
                        <p className="mt-1 text-xs text-slate-500">Changed by {entry.changed_by_id === null ? "system" : `user #${entry.changed_by_id}`}</p>{entry.note && <p className="mt-2 text-sm leading-5 text-slate-600">{entry.note}</p>}
                      </li>)}</ol>}
              </Section>
            </main>

            <aside className="min-w-0 space-y-4">
              <Section title="Ticket details">
                <dl>
                  <Detail label="Status" value={ticket.status.replaceAll("_", " ")} />
                  <Detail label="Priority" value={ticket.priority} valueClass={priorityTone(ticket.priority)} />
                  <Detail label="Category" value={ticket.category ?? "Not assigned"} />
                  <Detail label="Subcategory" value={ticket.subcategory ?? "Not assigned"} />
                  <Detail label="Assigned team" value={ticket.assigned_team_name ?? "Unassigned"} />
                  <Detail label="Assigned agent" value={ticket.assigned_agent_id == null ? "Unassigned" : `User #${ticket.assigned_agent_id}`} />
                  <Detail label="Created" value={formattedDate(ticket.created_at)} />
                  <Detail label="Last updated" value={formattedDate(ticket.updated_at)} />
                </dl>
              </Section>

              <Section title="Update ticket" description="Changes are saved to the ticket audit history.">
                <div className="space-y-3">
                  <label className="block text-xs font-medium text-slate-700">Category<select value={category} onChange={(event) => setCategory(event.target.value)} className="mt-1.5 w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-100"><option value="">Select category</option>{CATEGORIES.map((item) => <option key={item}>{item}</option>)}</select></label>
                  <label className="block text-xs font-medium text-slate-700">Subcategory<input value={subcategory} onChange={(event) => setSubcategory(event.target.value)} maxLength={100} placeholder="Optional" className="mt-1.5 w-full rounded-md border border-slate-300 px-2.5 py-2 text-sm text-slate-900 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-100" /></label>
                  <label className="block text-xs font-medium text-slate-700">Priority<select value={priority} onChange={(event) => setPriority(event.target.value as TicketPriority)} className="mt-1.5 w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-100">{PRIORITIES.map((item) => <option key={item}>{item}</option>)}</select></label>
                  <label className="block text-xs font-medium text-slate-700">Assigned team<select value={assignedTeamId} onChange={(event) => setAssignedTeamId(event.target.value)} className="mt-1.5 w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-100">
                    {!assignedTeamId && <option value="">Select a team to assign</option>}{assignedTeamId && !teams.some((team) => team.id.toString() === assignedTeamId) && <option value={assignedTeamId} disabled>{ticket.assigned_team_name ?? `Team #${assignedTeamId}`} (current assignment)</option>}{teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}
                  </select></label>
                  <label className="block text-xs font-medium text-slate-700">Status<select value={status} disabled={ticket.status === "CLOSED" || isSaving} onChange={(event) => setStatus(event.target.value as TicketStatus)} className="mt-1.5 w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-100 disabled:bg-slate-100">{ACTION_STATUSES.map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}</select></label>
                  {status === "RESOLVED" && ticket.status !== "RESOLVED" && <label className="block text-xs font-medium text-slate-700">Resolution note<textarea value={resolutionNote} onChange={(event) => setResolutionNote(event.target.value)} minLength={10} maxLength={5000} rows={3} placeholder="Describe the fix and how it was verified (at least 10 characters)." disabled={isSaving} className="mt-1.5 w-full resize-y rounded-md border border-slate-300 px-2.5 py-2 text-sm text-slate-900 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-100 disabled:bg-slate-50" /></label>}
                  <button type="button" onClick={() => void saveChanges()} disabled={isSaving} className="w-full rounded-md bg-sky-700 px-3 py-2.5 text-sm font-semibold text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-50">{isSaving ? "Saving changes…" : "Save changes"}</button>
                </div>
              </Section>

              <Section title="AI triage" description="Model predictions are shown separately from current ticket values.">
                <dl>
                  <Detail label="Predicted category" value={ticket.ai_predicted_category ?? "Not available"} />
                  <Detail label="Predicted priority" value={ticket.ai_predicted_priority ?? "Not available"} />
                  <Detail label="Classification confidence" value={confidenceLabel(ticket.ai_classification_confidence)} />
                  <Detail label="Combined triage score" value={confidenceLabel(ticket.ai_confidence)} />
                  <Detail label="Model version" value={ticket.ai_model_version ?? "Not available"} />
                  <Detail label="Routing explanation" value={ticket.routing_reason ?? "Not available"} />
                  <Detail label="AI assigned team" value={ticket.assigned_team_name ?? "Not assigned"} />
                </dl>
              </Section>

              <Section title="Suggested resolution" description="Knowledge-base recommendation for agent review.">
                <p className="mb-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">Guided-resolution eligibility and the employee AI conversation are not exposed to the agent API. This view shows only ticket triage and knowledge-match data.</p>
                {ticket.solution_status === "MATCHED" && ticket.suggested_solution ? <>
                  <p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{ticket.suggested_solution}</p>
                  <dl className="mt-3 border-t border-slate-100 pt-2">
                    <Detail label="Article" value={ticket.knowledge_article_title ?? "Available article"} />
                    <Detail label="Match confidence" value={confidenceLabel(ticket.solution_confidence ?? null)} />
                    <Detail label="Guided resolution" value="Eligibility not available in agent view" />
                  </dl>
                </> : ticket.solution_status === "NO_MATCH" ? <p className="text-sm leading-5 text-amber-800">No sufficiently relevant knowledge-base solution was found. Continue with the assigned support team.</p>
                  : <p className="text-sm text-slate-500">No recommendation is available yet.</p>}
              </Section>

              {ticket.resolved_at && <Section title="Resolution record">
                <Detail label="Resolved" value={formattedDate(ticket.resolved_at)} />
                {ticket.closed_at && <div className="mt-2"><Detail label="Closed" value={formattedDate(ticket.closed_at)} /></div>}
                <p className="mt-3 whitespace-pre-wrap border-t border-slate-100 pt-3 text-sm leading-5 text-slate-700">{latestResolution?.note ?? "No resolution note is available."}</p>
              </Section>}
            </aside>
          </div>

          <details className="mt-5 rounded-lg border border-slate-200 bg-white">
            <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-slate-800">Audit history</summary>
            <div className="border-t border-slate-100 p-4 sm:p-5">
              {isAuditLoading ? <p role="status" className="text-sm text-slate-500">Loading audit history…</p>
                : auditError ? <p role="alert" className="text-sm text-rose-800">{auditError}<button type="button" onClick={() => void refreshAuditHistory()} className="ml-2 font-semibold underline">Retry</button></p>
                  : fieldHistory.length === 0 && humanAssignments.length === 0 ? <p className="text-sm text-slate-500">No human field overrides or team reassignments recorded.</p>
                    : <ul className="space-y-2">{fieldHistory.map((entry) => <li key={`field-${entry.id}`} className="text-sm text-slate-700"><span className="font-medium">{entry.field_name}:</span> {entry.old_value ?? "Not set"} → {entry.new_value ?? "Not set"} <span className="text-xs text-slate-500">· User #{entry.changed_by_id} · {formattedDate(entry.changed_at)}</span>{entry.note && <p className="mt-1 text-xs text-slate-500">{entry.note}</p>}</li>)}{humanAssignments.map((entry) => <li key={`assignment-${entry.id}`} className="text-sm text-slate-700"><span className="font-medium">Team reassigned:</span> {teams.find((team) => team.id === entry.team_id)?.name ?? (entry.team_id ? `Team #${entry.team_id}` : "Unassigned")} <span className="text-xs text-slate-500">· User #{entry.assigned_by_id ?? "unknown"} · {formattedDate(entry.assigned_at)}</span>{entry.routing_reason && <p className="mt-1 text-xs text-slate-500">{entry.routing_reason}</p>}</li>)}</ul>}
            </div>
          </details>
        </>}
    </div>
  </AgentShell>;
}
