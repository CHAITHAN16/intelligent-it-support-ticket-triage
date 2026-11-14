"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AgentShell } from "@/components/agent-shell";
import { AgentAIEvidencePanel } from "@/components/agent-ai-evidence-panel";
import { TicketSLAPanel } from "@/components/agent-sla";
import {
  createTicketComment,
  getTeams,
  getTeamAgents,
  getTicket,
  getTicketAssignmentHistory,
  getTicketComments,
  getTicketFieldHistory,
  getTicketHistory,
  getTicketPredictionEvidence,
  getTicketPredictionReviews,
  getTicketSLA,
  updateTicket,
  type Team,
  type TeamAgent,
  type TicketAssignmentHistory,
  type TicketComment,
  type TicketFieldHistory,
  type TicketPriority,
  type TicketPredictionEvidence,
  type TicketPredictionReview,
  type TicketResponse,
  type TicketStatus,
  type TicketStatusHistory,
  type TicketSLA,
} from "@/lib/api";

const ACTION_STATUSES: TicketStatus[] = ["NEW", "ASSIGNED", "IN_PROGRESS", "WAITING_FOR_USER", "RESOLVED", "CLOSED"];
const PRIORITIES: TicketPriority[] = ["LOW", "MEDIUM", "HIGH", "URGENT"];
const CATEGORIES = ["Network", "Security", "Software", "Other"];
const SECTION_LINKS = [
  { id: "overview", label: "Overview" },
  { id: "conversation", label: "Conversation" },
  { id: "assignment", label: "Assignment" },
  { id: "sla", label: "SLA" },
  { id: "ai-insights", label: "AI Insights" },
  { id: "activity", label: "Activity" },
];

type TicketActivityEvent = {
  key: string;
  date: string;
  kind: "status" | "assignment" | "field" | "comment";
  title: string;
  detail: string;
  note?: string | null;
  commentId?: number;
};

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

function Section({ title, description, children, className = "", id }: { title: string; description?: string; children: React.ReactNode; className?: string; id?: string }) {
  return <section id={id} className={`scroll-mt-28 rounded-lg border border-slate-200 bg-white shadow-sm shadow-slate-200/30 ${className}`}>
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
  const [activeTicketSection, setActiveTicketSection] = useState("overview");
  const [category, setCategory] = useState("");
  const [subcategory, setSubcategory] = useState("");
  const [priority, setPriority] = useState<TicketPriority>("MEDIUM");
  const [status, setStatus] = useState<TicketStatus>("NEW");
  const [assignedTeamId, setAssignedTeamId] = useState("");
  const [eligibleAgents, setEligibleAgents] = useState<TeamAgent[]>([]);
  const [eligibleAgentsTeamId, setEligibleAgentsTeamId] = useState<number | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [assignmentReason, setAssignmentReason] = useState("");
  const [isAgentListLoading, setIsAgentListLoading] = useState(false);
  const [isAssignmentSaving, setIsAssignmentSaving] = useState(false);
  const [assignmentError, setAssignmentError] = useState<string | null>(null);
  const [assignmentMessage, setAssignmentMessage] = useState<string | null>(null);
  const [sla, setSla] = useState<TicketSLA | null>(null);
  const [isSlaLoading, setIsSlaLoading] = useState(true);
  const [slaError, setSlaError] = useState<string | null>(null);
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
  const [predictionEvidence, setPredictionEvidence] = useState<TicketPredictionEvidence[]>([]);
  const [predictionReviews, setPredictionReviews] = useState<TicketPredictionReview[]>([]);
  const [isCommentsLoading, setIsCommentsLoading] = useState(true);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);
  const [commentsError, setCommentsError] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [isAuditLoading, setIsAuditLoading] = useState(true);
  const [isEvidenceLoading, setIsEvidenceLoading] = useState(true);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
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
    setSelectedAgentId(result.assigned_agent_id?.toString() ?? "");
    setResolutionNote("");
  }, [ticketId]);

  const refreshSLA = useCallback(async () => {
    setIsSlaLoading(true);
    setSlaError(null);
    try { setSla(await getTicketSLA(ticketId)); }
    catch (reason) { setSlaError(reason instanceof Error ? reason.message : "SLA status could not be loaded."); }
    finally { setIsSlaLoading(false); }
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

  const refreshPredictionEvidence = useCallback(async () => {
    setIsEvidenceLoading(true);
    setEvidenceError(null);
    try {
      const [evidence, reviews] = await Promise.all([
        getTicketPredictionEvidence(ticketId),
        getTicketPredictionReviews(ticketId),
      ]);
      setPredictionEvidence(evidence);
      setPredictionReviews(reviews);
    } catch (reason) {
      setEvidenceError(reason instanceof Error ? reason.message : "AI prediction evidence could not be loaded.");
    } finally {
      setIsEvidenceLoading(false);
    }
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
      void refreshPredictionEvidence();
      void refreshSLA();
    }
    void load();
    return () => { cancelled = true; };
  }, [ticketId, retryCount, refreshAuditHistory, refreshPredictionEvidence, refreshSLA, refreshTicket]);

  useEffect(() => {
    const teamId = Number(assignedTeamId);
    if (!Number.isInteger(teamId) || teamId < 1) return;
    let cancelled = false;
    Promise.resolve().then(() => {
      if (cancelled) return;
      setIsAgentListLoading(true);
      return getTeamAgents(teamId);
    }).then((agents) => { if (!cancelled && agents) { setEligibleAgents(agents); setEligibleAgentsTeamId(teamId); } })
      .catch((reason) => { if (!cancelled) { setEligibleAgents([]); setEligibleAgentsTeamId(null); setAssignmentError(reason instanceof Error ? reason.message : "Eligible agents could not be loaded."); } })
      .finally(() => { if (!cancelled) setIsAgentListLoading(false); });
    return () => { cancelled = true; };
  }, [assignedTeamId]);

  useEffect(() => {
    if (!ticket) return;
    const scrollRoot = document.getElementById("agent-main");
    if (!scrollRoot) return;
    const sections = SECTION_LINKS.map((item) => document.getElementById(item.id)).filter((item): item is HTMLElement => item !== null);
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting).sort((left, right) => left.boundingClientRect.top - right.boundingClientRect.top);
      if (visible[0]) setActiveTicketSection(visible[0].target.id);
    }, { root: scrollRoot, rootMargin: "-112px 0px -68% 0px", threshold: 0 });
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, [Boolean(ticket)]);

  async function saveChanges() {
    if (!ticket) return;
    const resolving = status === "RESOLVED" && ticket.status !== "RESOLVED";
    if (resolving && resolutionNote.trim().length < 10) {
      setError("Add a meaningful resolution note of at least 10 characters before resolving.");
      return;
    }
    setIsSaving(true); setError(null); setSaveMessage(null);
    try {
      await updateTicket(ticket.id, {
        ...(category.trim() ? { category: category.trim(), subcategory: subcategory.trim() || null } : {}),
        priority, status,
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

  async function saveAgentAssignment() {
    const teamId = Number(assignedTeamId);
    if (!ticket || !Number.isInteger(teamId) || teamId < 1) { setAssignmentError("Choose a team before assigning an agent."); return; }
    if (eligibleAgentsTeamId !== teamId) { setAssignmentError("Load the selected team’s eligible agents before saving."); return; }
    setIsAssignmentSaving(true); setAssignmentError(null); setAssignmentMessage(null);
    try {
      await updateTicket(ticket.id, {
        assigned_team_id: teamId,
        assigned_agent_id: selectedAgentId ? Number(selectedAgentId) : null,
        ...(assignmentReason.trim() ? { assignment_reason: assignmentReason.trim() } : {}),
      });
      setAssignmentReason("");
      await Promise.all([refreshTicket(), refreshAuditHistory(), refreshSLA()]);
      setAssignmentMessage(selectedAgentId ? "Agent assignment updated." : "Agent unassigned.");
    } catch (reason) { setAssignmentError(reason instanceof Error ? reason.message : "Agent assignment could not be updated."); }
    finally { setIsAssignmentSaving(false); }
  }

  const latestResolution = [...history].reverse().find((entry) => entry.new_status === "RESOLVED");
  const agentName = (id: number | null | undefined) => id == null ? "Unassigned" : eligibleAgents.find((agent) => agent.id === id)?.name ?? `Agent #${id}`;
  const activityEvents = useMemo<TicketActivityEvent[]>(() => [
    ...history.map((entry) => ({
      key: `status-${entry.id}`, date: entry.changed_at, kind: "status" as const,
      title: `${entry.old_status?.replaceAll("_", " ") ?? "Created"} → ${entry.new_status.replaceAll("_", " ")}`,
      detail: `Changed by ${entry.changed_by_id === null ? "system" : `User #${entry.changed_by_id}`}`,
      note: entry.note,
    })),
    ...assignmentHistory.map((entry) => ({
      key: `assignment-${entry.id}`, date: entry.assigned_at, kind: "assignment" as const,
      title: entry.source === "AI" ? "AI team routing" : entry.source === "HUMAN" ? "Human assignment change" : "System assignment",
      detail: `Team #${entry.team_id ?? "—"} · ${agentName(entry.previous_agent_id)} → ${agentName(entry.agent_id)} · ${entry.assigned_by_id == null ? "System" : `User #${entry.assigned_by_id}`}`,
      note: entry.reason ?? entry.routing_reason,
    })),
    ...fieldHistory.map((entry) => ({
      key: `field-${entry.id}`, date: entry.changed_at, kind: "field" as const,
      title: `${entry.field_name} updated`,
      detail: `${entry.old_value ?? "Not set"} → ${entry.new_value ?? "Not set"} · User #${entry.changed_by_id}`,
      note: entry.note,
    })),
    ...comments.map((entry) => ({
      key: `comment-${entry.id}`, date: entry.created_at, kind: "comment" as const,
      title: "Team comment added", detail: `User #${entry.author_id}`, commentId: entry.id,
    })),
  ].sort((left, right) => Date.parse(right.date) - Date.parse(left.date)), [assignmentHistory, comments, eligibleAgents, fieldHistory, history]);

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
          <header id="overview" className="mt-5 scroll-mt-28 border-b border-slate-200 pb-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-semibold text-slate-500">#{ticket.id}</span>
                  <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ring-1 ring-inset ${statusTone(ticket.status)}`}>{ticket.status.replaceAll("_", " ")}</span>
                  <span className={`text-xs font-semibold ${priorityTone(ticket.priority)}`}>{ticket.priority} priority</span>
                </div>
                <h1 className="mt-2 break-words text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">{ticket.title}</h1>
                <p className="mt-2 text-xs text-slate-600">{ticket.assigned_team_name ?? "No team assigned"} <span className="px-1 text-slate-300">·</span> {agentName(ticket.assigned_agent_id)}</p>
              </div>
              <Link href={returnTo} className="hidden shrink-0 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 sm:inline-flex">Return to queue</Link>
            </div>
            {(error || saveMessage) && <div className={`mt-4 rounded-md border px-3 py-2 text-sm ${error ? "border-rose-200 bg-rose-50 text-rose-800" : "border-emerald-200 bg-emerald-50 text-emerald-800"}`} role={error ? "alert" : "status"}>{error ?? saveMessage}</div>}
          </header>

          <nav aria-label="Ticket sections" className="sticky top-0 z-20 -mx-4 mt-3 border-b border-slate-200 bg-slate-50/95 px-4 backdrop-blur sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
            <div className="flex min-w-0 gap-1 overflow-x-auto py-2">{SECTION_LINKS.map((item) => <a key={item.id} href={`#${item.id}`} aria-current={activeTicketSection === item.id ? "location" : undefined} onClick={() => setActiveTicketSection(item.id)} className={`shrink-0 rounded-md px-3 py-2 text-xs font-semibold ${activeTicketSection === item.id ? "bg-white text-sky-800 shadow-sm ring-1 ring-slate-200" : "text-slate-600 hover:bg-white hover:text-slate-900"}`}>{item.label}</a>)}</div>
          </nav>

          <div className="mt-4 min-w-0 space-y-5">
            <Section title="Overview" description="Request summary, current ownership and ticket classification." className="scroll-mt-28">
              <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.8fr)]">
                <div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Employee request · User #{ticket.creator_id}</p><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{ticket.description}</p></div>
                <dl className="grid gap-x-6 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2"><Detail label="Category" value={ticket.category ?? "Not assigned"} /><Detail label="Subcategory" value={ticket.subcategory ?? "Not assigned"} /><Detail label="Priority" value={ticket.priority} valueClass={priorityTone(ticket.priority)} /><Detail label="Status" value={ticket.status.replaceAll("_", " ")} /><Detail label="Assigned team" value={ticket.assigned_team_name ?? "Unassigned"} /><Detail label="Assigned agent" value={agentName(ticket.assigned_agent_id)} /><Detail label="Created" value={formattedDate(ticket.created_at)} /><Detail label="Last updated" value={formattedDate(ticket.updated_at)} /></dl>
              </div>
            </Section>

            <Section id="conversation" title="Conversation" description="Employee request, team discussion, and first-response comments." className="scroll-mt-28">
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

            <div className="grid min-w-0 gap-5 xl:grid-cols-2">

              <Section title="Update ticket" description="Changes are saved to the ticket audit history.">
                <div className="space-y-3">
                  <label className="block text-xs font-medium text-slate-700">Category<select value={category} onChange={(event) => setCategory(event.target.value)} className="mt-1.5 w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-100"><option value="">Select category</option>{CATEGORIES.map((item) => <option key={item}>{item}</option>)}</select></label>
                  <label className="block text-xs font-medium text-slate-700">Subcategory<input value={subcategory} onChange={(event) => setSubcategory(event.target.value)} maxLength={100} placeholder="Optional" className="mt-1.5 w-full rounded-md border border-slate-300 px-2.5 py-2 text-sm text-slate-900 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-100" /></label>
                  <label className="block text-xs font-medium text-slate-700">Priority<select value={priority} onChange={(event) => setPriority(event.target.value as TicketPriority)} className="mt-1.5 w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-100">{PRIORITIES.map((item) => <option key={item}>{item}</option>)}</select></label>
                  <label className="block text-xs font-medium text-slate-700">Status<select value={status} disabled={ticket.status === "CLOSED" || isSaving} onChange={(event) => setStatus(event.target.value as TicketStatus)} className="mt-1.5 w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-100 disabled:bg-slate-100">{ACTION_STATUSES.map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}</select></label>
                  {status === "RESOLVED" && ticket.status !== "RESOLVED" && <label className="block text-xs font-medium text-slate-700">Resolution note<textarea value={resolutionNote} onChange={(event) => setResolutionNote(event.target.value)} minLength={10} maxLength={5000} rows={3} placeholder="Describe the fix and how it was verified (at least 10 characters)." disabled={isSaving} className="mt-1.5 w-full resize-y rounded-md border border-slate-300 px-2.5 py-2 text-sm text-slate-900 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-100 disabled:bg-slate-50" /></label>}
                  <button type="button" onClick={() => void saveChanges()} disabled={isSaving} className="w-full rounded-md bg-sky-700 px-3 py-2.5 text-sm font-semibold text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-50">{isSaving ? "Saving changes…" : "Save changes"}</button>
                </div>
              </Section>

              <Section id="assignment" title="Assignment" description="Manage team ownership and individual agent assignment. AI routing remains recorded separately from human changes." className="scroll-mt-28">
                <div className="space-y-3">
                  <label className="block text-xs font-medium text-slate-700">Assigned team<select value={assignedTeamId} onChange={(event) => { setAssignedTeamId(event.target.value); setSelectedAgentId(""); setAssignmentError(null); }} disabled={isAssignmentSaving} className="mt-1.5 w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-100 disabled:bg-slate-100">
                    {!assignedTeamId && <option value="">Select a team to assign</option>}{assignedTeamId && !teams.some((team) => team.id.toString() === assignedTeamId) && <option value={assignedTeamId} disabled>{ticket.assigned_team_name ?? `Team #${assignedTeamId}`} (current assignment)</option>}{teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}
                  </select></label>
                  {Number(assignedTeamId) !== ticket.assigned_team_id && <p className="rounded-md bg-sky-50 px-3 py-2 text-xs text-sky-900">Saving a team change clears the previous agent until an eligible member is selected.</p>}
                  <label className="block text-xs font-medium text-slate-700">Assigned agent
                    <select value={selectedAgentId} disabled={!ticket.assigned_team_id || eligibleAgentsTeamId !== ticket.assigned_team_id || isAgentListLoading || isAssignmentSaving} onChange={(event) => setSelectedAgentId(event.target.value)} className="mt-1.5 w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-100 disabled:bg-slate-100">
                      <option value="">Unassigned</option>
                      {selectedAgentId && !eligibleAgents.some((agent) => agent.id.toString() === selectedAgentId) && <option value={selectedAgentId}>Current agent #{selectedAgentId}</option>}
                      {eligibleAgents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}
                    </select>
                  </label>
                  <label className="block text-xs font-medium text-slate-700">Reason (optional)<input value={assignmentReason} maxLength={1000} onChange={(event) => setAssignmentReason(event.target.value)} placeholder="Add context for the assignment" disabled={isAssignmentSaving} className="mt-1.5 w-full rounded-md border border-slate-300 px-2.5 py-2 text-sm text-slate-900 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-100 disabled:bg-slate-50" /></label>
                  {isAgentListLoading && <p role="status" className="text-xs text-slate-500">Loading eligible agents…</p>}
                  {assignmentError && <p role="alert" className="text-xs text-rose-700">{assignmentError}</p>}
                  {assignmentMessage && <p role="status" className="text-xs text-emerald-700">{assignmentMessage}</p>}
                  <button type="button" onClick={() => void saveAgentAssignment()} disabled={isAssignmentSaving || isAgentListLoading || !Number(assignedTeamId) || eligibleAgentsTeamId !== Number(assignedTeamId) || (selectedAgentId === (ticket.assigned_agent_id?.toString() ?? "") && Number(assignedTeamId) === ticket.assigned_team_id)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50">{isAssignmentSaving ? "Updating assignment…" : selectedAgentId ? "Save assignment" : "Save team / unassign agent"}</button>
                </div>
              </Section>

              <div id="sla" className="scroll-mt-28"><TicketSLAPanel sla={sla} loading={isSlaLoading} error={slaError} onRetry={() => void refreshSLA()} /></div>

              <AgentAIEvidencePanel
                currentCategory={ticket.category}
                currentPriority={ticket.priority}
                currentTeamName={ticket.assigned_team_name ?? null}
                currentTeamId={ticket.assigned_team_id}
                teams={teams}
                assignments={assignmentHistory}
                evidence={predictionEvidence}
                reviews={predictionReviews}
                isLoading={isEvidenceLoading}
                error={evidenceError}
                onRetry={() => void refreshPredictionEvidence()}
                onReviewSubmitted={async () => {
                  await Promise.all([refreshPredictionEvidence(), refreshTicket(), refreshAuditHistory()]);
                }}
                ticketId={ticketId}
              />

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
            </div>
          </div>

          <Section id="activity" title="Activity" description="Unified chronological status, assignment, comment and audit events." className="scroll-mt-28">
            {isAuditLoading || isHistoryLoading || isCommentsLoading ? <p role="status" className="text-sm text-slate-500">Loading activity…</p>
              : auditError || historyError || commentsError ? <div role="alert" className="space-y-1 text-sm text-rose-800"><p>{auditError ?? historyError ?? commentsError}</p><button type="button" onClick={() => { void refreshAuditHistory(); void refreshHistory(); void refreshComments(); }} className="font-semibold underline">Retry activity</button></div>
                : activityEvents.length === 0 ? <p className="text-sm text-slate-500">No activity recorded yet.</p>
                  : <ol className="space-y-4 border-l border-slate-200 pl-4">{activityEvents.map((event) => <li key={event.key} className="relative before:absolute before:-left-[1.32rem] before:top-1 before:h-2.5 before:w-2.5 before:rounded-full before:bg-sky-600 before:ring-4 before:ring-white">
                    <div className="flex flex-wrap items-start justify-between gap-2"><p className="text-sm font-medium text-slate-800">{event.title}</p><time dateTime={event.date} className="text-xs text-slate-500">{formattedDate(event.date)}</time></div>
                    <p className="mt-1 text-xs text-slate-500">{event.detail}</p>{event.note && <p className="mt-1 whitespace-pre-wrap text-sm leading-5 text-slate-600">{event.note}</p>}
                    {event.commentId != null && <p className="mt-2 whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-sm leading-5 text-slate-700">{comments.find((comment) => comment.id === event.commentId)?.body}</p>}
                  </li>)}</ol>}
          </Section>
        </>}
    </div>
  </AgentShell>;
}
