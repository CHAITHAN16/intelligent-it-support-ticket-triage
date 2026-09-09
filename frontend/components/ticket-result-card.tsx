import { isTicketProcessingComplete, type TicketResponse } from "@/lib/api";

function displayTeam(ticket: TicketResponse): string {
  return ticket.assigned_team_name ?? ticket.assigned_team?.name ?? "Not available";
}

function confidenceLabel(confidence: number | null): string {
  return confidence === null ? "Not available" : `${Math.round(confidence * 100)}%`;
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-t border-slate-200 pt-4 first:border-t-0 first:pt-0 sm:first:border-t sm:first:pt-4">
      <dt className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</dt>
      <dd className="mt-1.5 text-sm font-medium text-slate-900">{value}</dd>
    </div>
  );
}

export function TicketResultCard({ ticket }: { ticket: TicketResponse }) {
  const processingComplete = isTicketProcessingComplete(ticket);

  return (
    <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl shadow-slate-900/5" aria-live="polite">
      <div className="border-b border-slate-200 bg-slate-950 px-6 py-7 text-white sm:px-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-300">Ticket submitted</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">We have your request</h2>
            <p className="mt-2 text-sm text-slate-300">Reference #{ticket.id}</p>
          </div>
          <span className="rounded-full bg-emerald-400/15 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-emerald-300">
            {ticket.status}
          </span>
        </div>
      </div>

      <div className="space-y-8 p-6 sm:p-8">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Your request</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">{ticket.title}</h3>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-600">{ticket.description}</p>
        </div>

        <div className="rounded-2xl bg-sky-50 p-5 ring-1 ring-inset ring-sky-100">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">AI triage</p>
              <p className="mt-1 text-sm font-semibold text-slate-800">
                {processingComplete ? "AI triage completed" : "AI triage is processing..."}
              </p>
            </div>
            <span className="hidden h-10 w-10 items-center justify-center rounded-full bg-white text-sky-700 shadow-sm sm:flex" aria-hidden="true">&rarr;</span>
          </div>
          {processingComplete ? (
            <dl className="mt-6 grid gap-5 sm:grid-cols-2">
              <Detail label="Predicted category" value={ticket.ai_predicted_category!} />
              <Detail label="Predicted priority" value={ticket.ai_predicted_priority!} />
              <Detail label="Assigned team" value={displayTeam(ticket)} />
              <Detail label="AI confidence" value={confidenceLabel(ticket.ai_confidence)} />
              <Detail label="AI model version" value={ticket.ai_model_version ?? "Not available"} />
            </dl>
          ) : (
            <p className="mt-6 text-sm text-slate-600">AI triage is processing. Results will appear here automatically.</p>
          )}
        </div>
      </div>
    </section>
  );
}
