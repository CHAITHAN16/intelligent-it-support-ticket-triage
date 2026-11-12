"use client";

import { useState } from "react";
import { createTicketPredictionReview } from "@/lib/api";

import type {
  Team,
  TicketAssignmentHistory,
  TicketPredictionEvidence,
  TicketPredictionReview,
  TicketPriority,
} from "@/lib/api";

const CATEGORY_TEAM_MAP: Record<string, string> = {
  Network: "Network Infrastructure",
  Security: "Security Operations",
  Software: "Software Support",
  Other: "General IT Support",
};

function dateLabel(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function percent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-lg border border-slate-200 bg-white">
    <h2 className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-900">{title}</h2>
    <div className="p-4">{children}</div>
  </section>;
}

function Distribution({ title, values }: { title: string; values: Record<string, number> }) {
  const sortedValues = Object.entries(values).sort((left, right) => right[1] - left[1]);
  return <div>
    <h3 className="text-xs font-semibold text-slate-700">{title}</h3>
    <ul className="mt-2 space-y-2">
      {sortedValues.map(([label, value]) => <li key={label} className="grid grid-cols-[5.5rem_minmax(0,1fr)_3.5rem] items-center gap-2 text-xs">
        <span className="truncate text-slate-600">{label}</span>
        <span className="h-1.5 overflow-hidden rounded-full bg-slate-100" aria-hidden="true">
          <span className="block h-full rounded-full bg-sky-600" style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }} />
        </span>
        <span className="text-right tabular-nums text-slate-700">{percent(value)}</span>
      </li>)}
    </ul>
  </div>;
}

function FieldReviews({ field, reviews }: { field: "category" | "priority"; reviews: TicketPredictionReview[] }) {
  const fieldReviews = reviews.filter((review) => review.field_name === field);
  const latest = fieldReviews[fieldReviews.length - 1];
  const label = field === "category" ? "Category" : "Priority";
  return <div className="border-t border-slate-100 pt-3 first:border-0 first:pt-0">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h3 className="text-xs font-semibold text-slate-800">{label}</h3>
      <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${!latest ? "bg-slate-100 text-slate-600" : latest.outcome === "ACCEPTED" ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"}`}>
        {!latest ? "Not reviewed" : latest.outcome === "ACCEPTED" ? "Accepted" : "Overridden"}
      </span>
    </div>
    {!latest ? <p className="mt-1 text-xs text-slate-500">No human review recorded for this prediction.</p> : <ul className="mt-2 space-y-2">
      {fieldReviews.map((review) => <li key={review.id} className="rounded-md bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-700">
        <p><span className="font-medium">{review.outcome === "ACCEPTED" ? "Accepted" : "Overridden"}:</span> {review.predicted_value} → {review.confirmed_value}</p>
        <p className="text-slate-500">Reviewer #{review.reviewer_id} · {dateLabel(review.reviewed_at)}</p>
        {review.reason && <p className="mt-1 whitespace-pre-wrap text-slate-600">{review.reason}</p>}
      </li>)}
    </ul>}
  </div>;
}

export function AgentAIEvidencePanel({
  currentCategory,
  currentPriority,
  currentTeamName,
  currentTeamId,
  teams,
  assignments,
  evidence,
  reviews,
  isLoading,
  error,
  onRetry,
  onReviewSubmitted,
  ticketId,
}: {
  currentCategory: string | null;
  currentPriority: TicketPriority;
  currentTeamName: string | null;
  currentTeamId: number | null | undefined;
  teams: Team[];
  assignments: TicketAssignmentHistory[];
  evidence: TicketPredictionEvidence[];
  reviews: TicketPredictionReview[];
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
  onReviewSubmitted: () => Promise<void>;
  ticketId: number;
}) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [reason, setReason] = useState("");
  const [categoryCorrection, setCategoryCorrection] = useState("Network");
  const [priorityCorrection, setPriorityCorrection] = useState<TicketPriority>("MEDIUM");
  const [submittingField, setSubmittingField] = useState<"category" | "priority" | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);
  const latestEvidence = evidence[evidence.length - 1] ?? null;
  const selectedEvidence = evidence.find((item) => item.id === selectedId) ?? latestEvidence;
  const selectedReviews = selectedEvidence
    ? reviews.filter((review) => review.prediction_evidence_id === selectedEvidence.id)
    : [];
  const activeAssignment = [...assignments]
    .filter((assignment) => assignment.unassigned_at === null)
    .sort((left, right) => Date.parse(right.assigned_at) - Date.parse(left.assigned_at))[0];
  const mappedTeam = selectedEvidence ? CATEGORY_TEAM_MAP[selectedEvidence.predicted_category] ?? "General IT Support" : null;
  async function submitReview(field: "category" | "priority", value: string) {
    if (!selectedEvidence) return;
    setSubmittingField(field); setSubmitError(null); setSubmitSuccess(null);
    try {
      await createTicketPredictionReview(ticketId, {
        prediction_evidence_id: selectedEvidence.id,
        ...(field === "category" ? { category: value } : { priority: value as TicketPriority }),
        ...(reason.trim() ? { reason: reason.trim() } : {}),
      });
      await onReviewSubmitted();
      setSubmitSuccess(`${field === "category" ? "Category" : "Priority"} review saved.`);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Review could not be saved.");
    } finally { setSubmittingField(null); }
  }

  return <div className="space-y-4">
    <Section title="Current ticket values">
      <dl className="divide-y divide-slate-100">
        <div className="flex justify-between gap-3 py-2 first:pt-0"><dt className="text-xs text-slate-500">Operational category</dt><dd className="text-right text-xs font-medium text-slate-800">{currentCategory ?? "Not set"}</dd></div>
        <div className="flex justify-between gap-3 py-2 last:pb-0"><dt className="text-xs text-slate-500">Operational priority</dt><dd className="text-right text-xs font-medium text-slate-800">{currentPriority}</dd></div>
      </dl>
    </Section>

    <Section title="Prediction evidence">
      {isLoading ? <p role="status" className="text-sm text-slate-500">Loading prediction evidence…</p>
        : error ? <div role="alert" className="text-sm text-rose-800"><p>{error}</p><button type="button" onClick={onRetry} className="mt-2 font-semibold underline">Retry</button></div>
          : evidence.length === 0 ? <p className="text-sm leading-5 text-slate-600">No immutable prediction snapshot is available for this ticket. Older triage fields do not include the full class probability distributions.</p>
            : <>
              <label className="block text-xs font-medium text-slate-700">Prediction snapshot
                <select value={selectedEvidence?.id ?? ""} onChange={(event) => setSelectedId(Number(event.target.value))} className="mt-1.5 w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-100">
                  {[...evidence].reverse().map((item, index) => <option key={item.id} value={item.id}>{index === 0 ? "Latest · " : ""}{dateLabel(item.predicted_at)} · #{item.id}</option>)}
                </select>
              </label>
              {selectedEvidence && <div className="mt-4 space-y-4">
                <div className="rounded-md border border-sky-100 bg-sky-50/60 p-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-sky-800">{selectedEvidence.id === latestEvidence?.id ? "Latest prediction" : "Historical prediction"}</p>
                  <dl className="mt-2 divide-y divide-sky-100">
                    <div className="flex justify-between gap-3 py-2 first:pt-0"><dt className="text-xs text-slate-600">Predicted category</dt><dd className="text-right text-xs font-semibold text-slate-900">{selectedEvidence.predicted_category}</dd></div>
                    <div className="flex justify-between gap-3 py-2"><dt className="text-xs text-slate-600">Predicted priority</dt><dd className="text-right text-xs font-semibold text-slate-900">{selectedEvidence.predicted_priority}</dd></div>
                    <div className="flex justify-between gap-3 py-2"><dt className="text-xs text-slate-600">Category classification confidence</dt><dd className="text-right text-xs font-semibold text-slate-900">{percent(selectedEvidence.classification_confidence)}</dd></div>
                    <div className="flex justify-between gap-3 py-2 last:pb-0"><dt className="text-xs text-slate-600">Combined triage confidence</dt><dd className="text-right text-xs font-semibold text-slate-900">{percent(selectedEvidence.combined_confidence)}</dd></div>
                  </dl>
                </div>

                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
                  <Distribution title="Category model probability outputs" values={selectedEvidence.category_probabilities} />
                  <Distribution title="Priority model probability outputs" values={selectedEvidence.priority_probabilities} />
                </div>
                <p className="text-[11px] leading-4 text-slate-500">These are model probability outputs. Their calibration has not been established.</p>

                <dl className="border-t border-slate-100 pt-3">
                  <div className="flex justify-between gap-3 py-1.5"><dt className="text-xs text-slate-500">Category model</dt><dd className="text-right text-xs font-medium text-slate-700">{selectedEvidence.category_model_version}</dd></div>
                  <div className="flex justify-between gap-3 py-1.5"><dt className="text-xs text-slate-500">Priority model</dt><dd className="text-right text-xs font-medium text-slate-700">{selectedEvidence.priority_model_version}</dd></div>
                  <div className="flex justify-between gap-3 py-1.5"><dt className="text-xs text-slate-500">Runtime version</dt><dd className="max-w-[60%] break-all text-right text-xs font-medium text-slate-700">{selectedEvidence.runtime_model_version}</dd></div>
                  <div className="flex justify-between gap-3 py-1.5"><dt className="text-xs text-slate-500">Predicted</dt><dd className="text-right text-xs font-medium text-slate-700">{dateLabel(selectedEvidence.predicted_at)}</dd></div>
                </dl>

                <div className="border-t border-slate-100 pt-3">
                  <h3 className="mb-3 text-xs font-semibold text-slate-800">Human review for this prediction</h3>
                  <div className="space-y-3">
                    <FieldReviews field="category" reviews={selectedReviews} />
                    <FieldReviews field="priority" reviews={selectedReviews} />
                  </div>
                  <label className="mt-3 block text-xs font-medium text-slate-700">Optional review reason<textarea value={reason} onChange={(event) => setReason(event.target.value)} maxLength={2000} rows={2} disabled={submittingField !== null} className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm" /></label>
                  {!["category", "priority"].every((field) => selectedReviews.some((review) => review.field_name === field)) && <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    {!selectedReviews.some((review) => review.field_name === "category") && <div className="rounded-md border border-slate-200 p-3">
                      <p className="text-xs font-semibold text-slate-800">Category review</p>
                      <button type="button" disabled={submittingField !== null} onClick={() => void submitReview("category", selectedEvidence.predicted_category)} className="mt-2 w-full rounded bg-sky-700 px-2 py-1.5 text-xs font-semibold text-white disabled:opacity-50">{submittingField === "category" ? "Saving…" : "Accept predicted category"}</button>
                      <label className="mt-2 block text-xs text-slate-600">Correct category<select value={categoryCorrection} onChange={(event) => setCategoryCorrection(event.target.value)} className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-xs">{["Network", "Security", "Software", "Other"].map((value) => <option key={value}>{value}</option>)}</select></label>
                      <button type="button" disabled={submittingField !== null} onClick={() => void submitReview("category", categoryCorrection)} className="mt-2 w-full rounded border border-slate-300 px-2 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-50">Correct category</button>
                    </div>}
                    {!selectedReviews.some((review) => review.field_name === "priority") && <div className="rounded-md border border-slate-200 p-3">
                      <p className="text-xs font-semibold text-slate-800">Priority review</p>
                      <button type="button" disabled={submittingField !== null} onClick={() => void submitReview("priority", selectedEvidence.predicted_priority)} className="mt-2 w-full rounded bg-sky-700 px-2 py-1.5 text-xs font-semibold text-white disabled:opacity-50">{submittingField === "priority" ? "Saving…" : "Accept predicted priority"}</button>
                      <label className="mt-2 block text-xs text-slate-600">Correct priority<select value={priorityCorrection} onChange={(event) => setPriorityCorrection(event.target.value as TicketPriority)} className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-xs">{["LOW", "MEDIUM", "HIGH", "URGENT"].map((value) => <option key={value}>{value}</option>)}</select></label>
                      <button type="button" disabled={submittingField !== null} onClick={() => void submitReview("priority", priorityCorrection)} className="mt-2 w-full rounded border border-slate-300 px-2 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-50">Correct priority</button>
                    </div>}
                  </div>}
                  {submitError && <p role="alert" className="mt-2 text-xs text-rose-700">{submitError}</p>}
                  {submitSuccess && <p role="status" className="mt-2 text-xs text-emerald-700">{submitSuccess}</p>}
                </div>
              </div>}
            </>}
    </Section>

    <Section title="Routing">
      {selectedEvidence ? <div className="rounded-md bg-slate-50 px-3 py-2.5">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Configured category → team mapping</p>
        <p className="mt-1 text-sm font-medium text-slate-800">{selectedEvidence.predicted_category} → {mappedTeam}</p>
        <p className="mt-1 text-[11px] leading-4 text-slate-500">This displays the configured route for the predicted category. It does not explain which ticket text features influenced the classifier.</p>
      </div> : <p className="text-sm text-slate-500">No prediction snapshot is available to show the category route.</p>}
      <dl className="mt-3 divide-y divide-slate-100">
        <div className="flex justify-between gap-3 py-2 first:pt-0"><dt className="text-xs text-slate-500">Currently assigned team</dt><dd className="text-right text-xs font-medium text-slate-800">{currentTeamName ?? (currentTeamId ? `Team #${currentTeamId}` : "Unassigned")}</dd></div>
        <div className="flex justify-between gap-3 py-2 last:pb-0"><dt className="text-xs text-slate-500">Current assignment source</dt><dd className="text-right text-xs font-medium text-slate-800">{activeAssignment?.source ?? "Not recorded"}</dd></div>
      </dl>
      {assignments.length > 0 && <details className="mt-3 border-t border-slate-100 pt-3">
        <summary className="cursor-pointer text-xs font-semibold text-slate-700">Assignment history ({assignments.length})</summary>
        <ol className="mt-3 space-y-3">
          {[...assignments].reverse().map((assignment) => {
            const teamName = teams.find((team) => team.id === assignment.team_id)?.name ?? (assignment.team_id ? `Team #${assignment.team_id}` : "No team");
            return <li key={assignment.id} className="border-l-2 border-slate-200 pl-3 text-xs leading-5 text-slate-700">
              <p className="font-medium">{teamName} · {assignment.source}</p>
              <p className="text-slate-500">{dateLabel(assignment.assigned_at)}{assignment.assigned_by_id ? ` · User #${assignment.assigned_by_id}` : ""}</p>
              {assignment.routing_reason && <p className="mt-1 text-slate-600">{assignment.routing_reason}</p>}
            </li>;
          })}
        </ol>
      </details>}
    </Section>
  </div>;
}
