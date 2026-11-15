import type { TicketPriority, TicketStatus } from "@/lib/api";
import { UiIcon } from "@/components/ui-icon";

const priorityTones: Record<TicketPriority, string> = {
  LOW: "bg-slate-100 text-slate-700 ring-slate-200",
  MEDIUM: "bg-blue-50 text-blue-700 ring-blue-200",
  HIGH: "bg-amber-50 text-amber-800 ring-amber-200",
  URGENT: "bg-red-50 text-red-700 ring-red-200",
};

const statusTones: Record<TicketStatus, string> = {
  NEW: "bg-blue-50 text-blue-700 ring-blue-200",
  ASSIGNED: "bg-blue-50 text-blue-700 ring-blue-200",
  IN_PROGRESS: "bg-violet-50 text-violet-700 ring-violet-200",
  WAITING_FOR_USER: "bg-amber-50 text-amber-800 ring-amber-200",
  RESOLVED: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  CLOSED: "bg-slate-100 text-slate-600 ring-slate-200",
};

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  return <span className={`inline-flex w-fit items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${priorityTones[priority]}`}>{priority}</span>;
}

export function StatusBadge({ status, compact = false }: { status: TicketStatus; compact?: boolean }) {
  return <span className={`inline-flex w-fit items-center rounded-full ring-1 ring-inset ${compact ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs"} font-semibold ${statusTones[status]}`}>{status.replaceAll("_", " ")}</span>;
}

export function ConfidenceBar({ label, value }: { label: string; value: number | null }) {
  if (value === null) return <div className="flex items-center justify-between gap-3 text-xs"><span className="text-slate-600">{label}</span><span className="text-slate-500">Not available</span></div>;
  const width = Math.max(0, Math.min(100, value * 100));
  return <div>
    <div className="flex justify-between gap-3 text-xs"><span className="text-slate-600">{label}</span><span className="font-medium tabular-nums text-violet-800">{Math.round(width)}%</span></div>
    <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-violet-100" role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(width)}><div className="h-full rounded-full bg-violet-600" style={{ width: `${width}%` }} /></div>
  </div>;
}

export function ReviewOutcome({ outcome }: { outcome: "ACCEPTED" | "OVERRIDDEN" }) {
  const accepted = outcome === "ACCEPTED";
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${accepted ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"}`}><UiIcon name={accepted ? "check-circle" : "arrow-right"} className="h-3.5 w-3.5" />{accepted ? "Accepted" : "Overridden"}</span>;
}
