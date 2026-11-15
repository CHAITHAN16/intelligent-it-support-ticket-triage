import type { SLAClock, SLAState, TicketSLA } from "@/lib/api";
import { UiIcon } from "@/components/ui-icon";

function dateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function formatDuration(seconds: number | null) {
  if (seconds === null) return "—";
  const minutes = Math.max(0, Math.floor(seconds / 60));
  const days = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  const remainingMinutes = minutes % 60;
  if (days) return `${days}d ${hours}h`;
  if (hours) return `${hours}h ${remainingMinutes}m`;
  return `${remainingMinutes}m`;
}

const tones: Record<SLAState, string> = {
  ON_TRACK: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  APPROACHING: "bg-amber-50 text-amber-900 ring-amber-200",
  BREACHED: "bg-red-50 text-red-800 ring-red-200",
  MET: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  NOT_APPLICABLE: "bg-slate-100 text-slate-600 ring-slate-200",
};

export function SLAStateBadge({ clock, compact = false }: { clock: SLAClock; compact?: boolean }) {
  const label = clock.state === "ON_TRACK" ? "Within SLA"
    : clock.state === "APPROACHING" ? "Approaching deadline"
      : clock.state === "BREACHED" ? (clock.completed_at ? "Completed after deadline" : "Breached")
        : clock.state === "MET" ? "Completed"
          : "Not applicable";
  const icon = clock.state === "ON_TRACK" || clock.state === "MET" ? "check-circle" : clock.state === "APPROACHING" ? "alert-circle" : clock.state === "BREACHED" ? "alert-triangle" : "clock";
  const completed = clock.completed_at !== null;
  const stateTone = clock.state === "BREACHED" && completed ? "bg-red-50 text-red-800 ring-red-200" : tones[clock.state];
  return <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold ring-1 ring-inset ${stateTone} ${compact ? "px-2 py-0.5" : ""}`}><UiIcon name={icon} className="h-3.5 w-3.5" />{label === "Completed" ? "Completed on time" : label}</span>;
}

function ClockCard({ title, clock }: { title: string; clock: SLAClock }) {
  const timeSummary = clock.completed_at
    ? clock.state === "BREACHED" ? `Completed ${formatDuration(clock.overdue_seconds)} after deadline` : "Completed within target"
    : clock.actively_overdue ? `Overdue by ${formatDuration(clock.overdue_seconds)}`
      : clock.remaining_seconds !== null ? `${formatDuration(clock.remaining_seconds)} remaining`
        : "No active timer";
  const accent = clock.state === "BREACHED" ? "border-l-red-500" : clock.state === "APPROACHING" ? "border-l-amber-500" : clock.state === "ON_TRACK" || clock.state === "MET" ? "border-l-emerald-500" : "border-l-slate-300";
  return <section className={`rounded-md border border-l-4 border-slate-200 bg-slate-50 p-3.5 ${accent}`}>
    <div className="flex flex-wrap items-start justify-between gap-2"><h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-900"><UiIcon name="calendar-clock" className="h-4 w-4 text-slate-500" />{title}</h3><SLAStateBadge clock={clock} /></div>
    <dl className="mt-3 space-y-2 text-xs">
      <div className="flex justify-between gap-3"><dt className="text-slate-500">Target</dt><dd className="text-right font-medium text-slate-800">{formatDuration(clock.target_minutes * 60)}</dd></div>
      <div className="flex justify-between gap-3"><dt className="text-slate-500">Deadline</dt><dd className="text-right font-medium text-slate-800">{dateTime(clock.deadline)}</dd></div>
      {clock.completed_at && <div className="flex justify-between gap-3"><dt className="text-slate-500">Completed</dt><dd className="text-right font-medium text-slate-800">{dateTime(clock.completed_at)}</dd></div>}
    </dl>
    <p className={`mt-3 border-t border-slate-200 pt-2.5 text-xs font-semibold ${clock.actively_overdue ? "text-rose-700" : clock.state === "APPROACHING" ? "text-amber-800" : "text-slate-700"}`}>{timeSummary}</p>
    {clock.actively_overdue && <p className="mt-1 text-[11px] text-rose-700">This ticket is currently overdue.</p>}
  </section>;
}

export function TicketSLAPanel({ sla, loading, error, onRetry }: { sla: TicketSLA | null; loading: boolean; error: string | null; onRetry: () => void }) {
  return <section className="rounded-lg border border-slate-200 bg-white">
    <div className="border-b border-slate-100 px-4 py-3 sm:px-5"><h2 className="text-sm font-semibold text-slate-900">Service level targets</h2><p className="mt-1 text-xs leading-5 text-slate-500">Response and resolution clocks are tracked independently.</p></div>
    <div className="grid grid-cols-1 gap-3 p-4 sm:p-5 md:grid-cols-2">
      {loading ? <p role="status" className="text-sm text-slate-500 md:col-span-2">Loading SLA status…</p>
        : error ? <p role="alert" className="text-sm text-rose-800 md:col-span-2">{error}<button type="button" onClick={onRetry} className="ml-2 font-semibold underline">Retry</button></p>
          : sla ? <><ClockCard title="First response" clock={sla.response} /><ClockCard title="Resolution" clock={sla.resolution} /></>
            : <p className="text-sm text-slate-500 md:col-span-2">SLA data is not available.</p>}
    </div>
  </section>;
}
