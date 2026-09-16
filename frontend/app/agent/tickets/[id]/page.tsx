"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AgentShell } from "@/components/agent-shell";
import { createTicketComment, getTeams, getTicket, getTicketAssignmentHistory, getTicketComments, getTicketFieldHistory, getTicketHistory, updateTicket, type Team, type TicketAssignmentHistory, type TicketComment, type TicketFieldHistory, type TicketPriority, type TicketResponse, type TicketStatus, type TicketStatusHistory } from "@/lib/api";

const ACTION_STATUSES: TicketStatus[] = ["NEW", "IN_PROGRESS", "RESOLVED", "CLOSED"];
const PRIORITIES: TicketPriority[] = ["LOW", "MEDIUM", "HIGH", "URGENT"];
const CATEGORIES = ["Network", "Security", "Software", "Other"];

function Field({ label, value }: { label: string; value: string }) {
  return <div className="border-t border-slate-200 pt-4 first:border-t-0 first:pt-0"><dt className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</dt><dd className="mt-1.5 text-sm font-medium text-slate-900">{value}</dd></div>;
}

function formattedDate(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function differsFromPrediction(currentValue: string | null, prediction: string | null) {
  return prediction !== null && currentValue !== prediction;
}

export default function AgentTicketDetailPage() {
  const params = useParams<{ id: string }>();
  const ticketId = Number(params.id);
  const [ticket, setTicket] = useState<TicketResponse | null>(null);
  const [category, setCategory] = useState("");
  const [subcategory, setSubcategory] = useState("");
  const [priority, setPriority] = useState<TicketPriority>("MEDIUM");
  const [status, setStatus] = useState<TicketStatus>("NEW");
  const [assignedTeamId, setAssignedTeamId] = useState("");
  const [teams, setTeams] = useState<Team[]>([]);
  const [isLoading, setIsLoading] = useState(true);
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

  const refreshTicket = useCallback(async () => {
    const result = await getTicket(ticketId);
    setTicket(result);
    setCategory(result.category ?? "");
    setSubcategory(result.subcategory ?? "");
    setPriority(result.priority);
    setStatus(result.status);
    setAssignedTeamId(result.assigned_team_id?.toString() ?? "");
  }, [ticketId]);

  const refreshComments = useCallback(async () => {
    setIsCommentsLoading(true);
    setCommentsError(null);
    try {
      setComments(await getTicketComments(ticketId));
    } catch (reason) {
      setCommentsError(reason instanceof Error ? reason.message : "Comments could not be loaded.");
    } finally {
      setIsCommentsLoading(false);
    }
  }, [ticketId]);

  const refreshHistory = useCallback(async () => {
    setIsHistoryLoading(true);
    setHistoryError(null);
    try {
      setHistory(await getTicketHistory(ticketId));
    } catch (reason) {
      setHistoryError(reason instanceof Error ? reason.message : "Status history could not be loaded.");
    } finally {
      setIsHistoryLoading(false);
    }
  }, [ticketId]);

  const refreshAuditHistory = useCallback(async () => {
    setIsAuditLoading(true);
    setAuditError(null);
    try {
      const [fields, assignments] = await Promise.all([getTicketFieldHistory(ticketId), getTicketAssignmentHistory(ticketId)]);
      setFieldHistory(fields);
      setAssignmentHistory(assignments);
    } catch (reason) {
      setAuditError(reason instanceof Error ? reason.message : "Override history could not be loaded.");
    } finally {
      setIsAuditLoading(false);
    }
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
    async function loadCollaboration() {
      const [commentsResult, historyResult, teamsResult] = await Promise.allSettled([getTicketComments(ticketId), getTicketHistory(ticketId), getTeams()]);
      if (cancelled) return;

      if (commentsResult.status === "fulfilled") {
        setComments(commentsResult.value);
      } else {
        setCommentsError(commentsResult.reason instanceof Error ? commentsResult.reason.message : "Comments could not be loaded.");
      }
      setIsCommentsLoading(false);

      if (historyResult.status === "fulfilled") {
        setHistory(historyResult.value);
      } else {
        setHistoryError(historyResult.reason instanceof Error ? historyResult.reason.message : "Status history could not be loaded.");
      }
      setIsHistoryLoading(false);

      if (teamsResult.status === "fulfilled") setTeams(teamsResult.value);
    }

    if (Number.isInteger(ticketId)) {
      void loadCollaboration();
      void refreshAuditHistory();
    }
    return () => { cancelled = true; };
  }, [ticketId, refreshAuditHistory, refreshTicket]);

  async function saveChanges() {
    if (!ticket || !category.trim()) { setError("Category is required."); return; }
    setIsSaving(true); setError(null); setSaveMessage(null);
    try {
      const teamId = Number(assignedTeamId);
      await updateTicket(ticket.id, { category: category.trim(), subcategory: subcategory.trim() || null, priority, status, ...(teamId ? { assigned_team_id: teamId } : {}) });
      await Promise.all([refreshTicket(), refreshHistory(), refreshAuditHistory()]);
      setSaveMessage("Ticket updated.");
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Ticket update failed."); }
    finally { setIsSaving(false); }
  }

  async function submitComment() {
    const trimmedBody = commentBody.trim();
    if (!ticket || !trimmedBody) {
      setCommentSubmitError("Enter a comment before submitting.");
      return;
    }

    setIsCommentPosting(true);
    setCommentSubmitError(null);
    try {
      await createTicketComment(ticket.id, trimmedBody);
      setCommentBody("");
      await refreshComments();
    } catch (reason) {
      setCommentSubmitError(reason instanceof Error ? reason.message : "Comment could not be added.");
    } finally {
      setIsCommentPosting(false);
    }
  }

  return <AgentShell selectedTeamName={ticket?.assigned_team_name ?? "General IT Support"}>
    <div className="mx-auto max-w-5xl">
      <Link href="/agent" className="text-sm font-semibold text-sky-700 hover:text-sky-900">&larr; Back to queue</Link>
      {isLoading ? <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">Loading ticket...</div> : error && !ticket ? <div role="alert" className="mt-8 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div> : ticket ? <div className="mt-6 space-y-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start"><div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-600">Ticket #{ticket.id}</p><h1 className="mt-2 text-4xl font-semibold tracking-[-0.04em] text-slate-950">{ticket.title}</h1></div><span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700">{ticket.status.replaceAll("_", " ")}</span></div>
        {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>}
        {saveMessage && <div role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{saveMessage}</div>}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Request</p><p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-slate-700">{ticket.description}</p><dl className="mt-8 grid gap-5 sm:grid-cols-2"><Field label="Category" value={ticket.category ?? "Not assigned"} /><Field label="Priority" value={ticket.priority} /><Field label="Status" value={ticket.status.replaceAll("_", " ")} /><Field label="Assigned team" value={ticket.assigned_team_name ?? "Unassigned"} /><Field label="Created" value={formattedDate(ticket.created_at)} /><Field label="Updated" value={formattedDate(ticket.updated_at)} /></dl></section>
        <section className="rounded-2xl border border-sky-100 bg-sky-50 p-6 sm:p-8"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">AI Triage Explanation</p><p className="mt-2 text-sm text-slate-600">AI predictions are shown beside the current ticket values so agent changes remain clear.</p><dl className="mt-6 grid gap-5 sm:grid-cols-2"><Field label="AI predicted category" value={ticket.ai_predicted_category ?? "AI processing in progress"} /><Field label="Current category" value={ticket.category ?? "Not assigned"} />{differsFromPrediction(ticket.category, ticket.ai_predicted_category) && <p className="-mt-2 text-sm font-semibold text-amber-800 sm:col-span-2">Category: Differs from AI prediction</p>}<Field label="AI predicted priority" value={ticket.ai_predicted_priority ?? "AI processing in progress"} /><Field label="Current priority" value={ticket.priority} />{differsFromPrediction(ticket.priority, ticket.ai_predicted_priority) && <p className="-mt-2 text-sm font-semibold text-amber-800 sm:col-span-2">Priority: Differs from AI prediction</p>}<Field label="AI subcategory" value={ticket.ai_predicted_subcategory ?? "Not available"} /><Field label="Combined / average confidence" value={ticket.ai_confidence === null ? "Not available" : `${Math.round(ticket.ai_confidence * 100)}%`} /><Field label="Assigned team" value={ticket.assigned_team_name ?? "Unassigned"} /><Field label="Routing reason" value={ticket.routing_reason ?? "AI processing in progress"} /><Field label="AI model version" value={ticket.ai_model_version ?? "Not available"} /><Field label="AI triaged at" value={ticket.ai_triaged_at ? formattedDate(ticket.ai_triaged_at) : "AI processing in progress"} /></dl></section>
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Agent actions</p><h2 className="mt-2 text-xl font-semibold text-slate-950">Update ticket</h2></div><span className="text-xs text-slate-500">Changes are recorded in the audit history.</span></div><div className="mt-6 grid gap-4 sm:grid-cols-2"><label className="text-sm font-semibold text-slate-700">Category<select value={category} onChange={(event) => setCategory(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm font-normal text-slate-900"><option value="">Select category</option>{CATEGORIES.map((item) => <option key={item}>{item}</option>)}</select></label><label className="text-sm font-semibold text-slate-700">Subcategory<input value={subcategory} onChange={(event) => setSubcategory(event.target.value)} maxLength={100} placeholder="Optional subcategory" className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm font-normal text-slate-900" /></label><label className="text-sm font-semibold text-slate-700">Priority<select value={priority} onChange={(event) => setPriority(event.target.value as TicketPriority)} className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm font-normal text-slate-900">{PRIORITIES.map((item) => <option key={item}>{item}</option>)}</select></label><label className="text-sm font-semibold text-slate-700">Assigned team<select value={assignedTeamId} onChange={(event) => setAssignedTeamId(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm font-normal text-slate-900"><option value="">Select team</option>{teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}</select></label><label className="text-sm font-semibold text-slate-700">Status<select value={ACTION_STATUSES.includes(status) ? status : "NEW"} onChange={(event) => setStatus(event.target.value as TicketStatus)} className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm font-normal text-slate-900">{ACTION_STATUSES.map((item) => <option key={item}>{item.replaceAll("_", " ")}</option>)}</select></label></div><button type="button" onClick={saveChanges} disabled={isSaving} className="mt-6 rounded-full bg-sky-500 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-sky-500/20 transition hover:bg-sky-600 disabled:cursor-not-allowed disabled:bg-slate-300">{isSaving ? "Saving..." : "Save changes"}</button></section>
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Comments</p><h2 className="mt-2 text-xl font-semibold text-slate-950">Internal discussion</h2><div className="mt-5 space-y-3">{isCommentsLoading ? <p className="text-sm text-slate-500">Loading comments...</p> : commentsError ? <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{commentsError}</p> : comments.length === 0 ? <p className="rounded-xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">No comments yet.</p> : comments.map((comment) => <article key={comment.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4"><div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500"><span className="font-semibold text-slate-700">Author #{comment.author_id}</span><time dateTime={comment.created_at}>{formattedDate(comment.created_at)}</time></div><p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">{comment.body}</p></article>)}</div><div className="mt-6 border-t border-slate-200 pt-6"><label htmlFor="new-comment" className="text-sm font-semibold text-slate-700">Add a comment</label><textarea id="new-comment" rows={4} value={commentBody} onChange={(event) => { setCommentBody(event.target.value); setCommentSubmitError(null); }} placeholder="Share an update with the support team" disabled={isCommentPosting} className="mt-2 w-full resize-y rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none ring-sky-200 focus:ring-4 disabled:bg-slate-100" />{commentSubmitError && <p role="alert" className="mt-2 text-sm text-rose-700">{commentSubmitError}</p>}<button type="button" onClick={submitComment} disabled={isCommentPosting || !commentBody.trim()} className="mt-3 rounded-full bg-sky-500 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-sky-500/20 transition hover:bg-sky-600 disabled:cursor-not-allowed disabled:bg-slate-300">{isCommentPosting ? "Adding..." : "Add comment"}</button></div></section>
        <section className="rounded-2xl border border-sky-100 bg-sky-50 p-6 sm:p-8"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">Status history</p><h2 className="mt-2 text-xl font-semibold text-slate-950">Ticket timeline</h2>{isHistoryLoading ? <p className="mt-5 text-sm text-slate-500">Loading status history...</p> : historyError ? <p role="alert" className="mt-5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{historyError}</p> : history.length === 0 ? <p className="mt-5 rounded-xl border border-dashed border-sky-200 bg-white/60 px-4 py-5 text-sm text-slate-500">No status changes recorded yet.</p> : <ol className="mt-6 space-y-4 border-l border-sky-200 pl-5">{history.map((entry) => <li key={entry.id} className="relative rounded-xl border border-sky-100 bg-white p-4 shadow-sm before:absolute before:-left-[1.65rem] before:top-5 before:h-3 before:w-3 before:rounded-full before:border-2 before:border-sky-100 before:bg-sky-500"><div className="flex flex-wrap items-center justify-between gap-2"><p className="text-sm font-semibold text-slate-900">{entry.old_status ? entry.old_status.replaceAll("_", " ") : "Initial"} <span className="px-1 text-sky-600">-&gt;</span> {entry.new_status.replaceAll("_", " ")}</p><time dateTime={entry.changed_at} className="text-xs text-slate-500">{formattedDate(entry.changed_at)}</time></div><p className="mt-2 text-xs text-slate-500">Changed by {entry.changed_by_id === null ? "system" : `user #${entry.changed_by_id}`}</p>{entry.note && <p className="mt-3 text-sm text-slate-600">{entry.note}</p>}</li>)}</ol>}</section>
        <section className="rounded-2xl border border-amber-100 bg-amber-50 p-6 sm:p-8"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">Agent Overrides / Audit History</p><h2 className="mt-2 text-xl font-semibold text-slate-950">Human changes and assignments</h2>{isAuditLoading ? <p className="mt-5 text-sm text-slate-500">Loading override history...</p> : auditError ? <p role="alert" className="mt-5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{auditError}</p> : fieldHistory.length === 0 && assignmentHistory.filter((entry) => entry.source === "HUMAN").length === 0 ? <p className="mt-5 rounded-xl border border-dashed border-amber-200 bg-white/60 px-4 py-5 text-sm text-slate-500">No agent overrides recorded yet.</p> : <ol className="mt-6 space-y-3">{fieldHistory.map((entry) => <li key={`field-${entry.id}`} className="rounded-xl border border-amber-100 bg-white p-4 text-sm text-slate-700"><p className="font-semibold text-slate-900">{entry.field_name}: {entry.old_value ?? "Not set"} &rarr; {entry.new_value ?? "Not set"}</p><p className="mt-1 text-xs text-slate-500">Changed by user #{entry.changed_by_id} · {formattedDate(entry.changed_at)}</p>{entry.note && <p className="mt-2">{entry.note}</p>}</li>)}{assignmentHistory.filter((entry) => entry.source === "HUMAN").map((entry) => <li key={`assignment-${entry.id}`} className="rounded-xl border border-amber-100 bg-white p-4 text-sm text-slate-700"><p className="font-semibold text-slate-900">Team reassigned to {teams.find((team) => team.id === entry.team_id)?.name ?? `team #${entry.team_id}`}</p><p className="mt-1 text-xs text-slate-500">Assigned by user #{entry.assigned_by_id} · {formattedDate(entry.assigned_at)}</p>{entry.routing_reason && <p className="mt-2">{entry.routing_reason}</p>}</li>)}</ol>}</section>
      </div> : null}
    </div>
  </AgentShell>;
}
