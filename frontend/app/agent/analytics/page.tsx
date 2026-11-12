"use client";

import { useEffect, useState } from "react";

import { AgentShell } from "@/components/agent-shell";
import { getAIAnalytics, type AIAnalyticsResponse } from "@/lib/api";

function defaultDate(offsetDays: number) {
  const value = new Date();
  value.setDate(value.getDate() + offsetDays);
  return value.toISOString().slice(0, 10);
}

function Metric({ title, value, note }: { title: string; value: string; note: string }) {
  return <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm shadow-slate-200/40"><p className="text-xs font-medium text-slate-500">{title}</p><p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{value}</p><p className="mt-1 text-xs text-slate-500">{note}</p></article>;
}

function rate(value: number | null) { return value === null ? "—" : `${(value * 100).toFixed(1)}%`; }

function BarRows({ rows, labelKey, countKey }: { rows: Array<Record<string, string | number>>; labelKey: string; countKey: string }) {
  const max = Math.max(1, ...rows.map((row) => Number(row[countKey])));
  if (!rows.length) return <p className="text-sm text-slate-500">No records in this date range.</p>;
  return <ul className="space-y-3">{rows.map((row, index) => <li key={`${row[labelKey]}-${index}`}>
    <div className="mb-1 flex justify-between gap-3 text-xs"><span className="truncate text-slate-700">{row[labelKey]}</span><span className="font-medium tabular-nums text-slate-600">{row[countKey]}</span></div>
    <div className="h-2 overflow-hidden rounded bg-slate-100"><div className="h-full rounded bg-blue-600" style={{ width: `${Math.max(3, Number(row[countKey]) / max * 100)}%` }} /></div>
  </li>)}</ul>;
}

function ReviewBreakdown({ title, data }: { title: string; data: NonNullable<AIAnalyticsResponse>["category"] }) {
  return <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
    <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
    <p className="mt-1 text-xs text-slate-500">{data.reviewed} reviewed field decisions</p>
    <div className="mt-4 grid grid-cols-2 gap-3">
      <div className="rounded-md bg-slate-50 p-3"><p className="text-xs text-slate-500">Accepted</p><p className="mt-1 text-lg font-semibold text-emerald-700">{data.accepted}</p><p className="text-xs text-slate-500">{rate(data.acceptance_rate)} of reviews</p></div>
      <div className="rounded-md bg-slate-50 p-3"><p className="text-xs text-slate-500">Overridden</p><p className="mt-1 text-lg font-semibold text-amber-700">{data.overridden}</p><p className="text-xs text-slate-500">{rate(data.override_rate)} of reviews</p></div>
    </div>
  </section>;
}

export default function AIAnalyticsPage() {
  const [from, setFrom] = useState(defaultDate(-89));
  const [to, setTo] = useState(defaultDate(0));
  const [modelVersion, setModelVersion] = useState("");
  const [result, setResult] = useState<{ key: string; data: AIAnalyticsResponse } | null>(null);
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null);
  const [refresh, setRefresh] = useState(0);

  const requestKey = `${from}|${to}|${modelVersion}`;
  useEffect(() => {
    let active = true;
    getAIAnalytics(from, to, modelVersion || undefined)
      .then((data) => { if (active) { setResult({ key: requestKey, data }); setFailure(null); } })
      .catch((reason: unknown) => { if (active) setFailure({ key: requestKey, message: reason instanceof Error ? reason.message : "AI analytics could not be loaded." }); });
    return () => { active = false; };
  }, [from, to, modelVersion, refresh, requestKey]);

  const data = result?.key === requestKey ? result.data : null;
  const error = failure?.key === requestKey ? failure.message : null;
  const loading = !data && !error;
  const versions = [...new Set([...(data?.category_model_versions.map((item) => item.model_version) ?? []), ...(data?.priority_model_versions.map((item) => item.model_version) ?? [])])].sort();
  const commonVersions = data ? [...new Set([...data.category_model_versions.map((item) => item.model_version), ...data.priority_model_versions.map((item) => item.model_version)])].sort() : [];
  const versionsToFilter = versions.length ? versions : commonVersions;

  return <AgentShell activeSection="analytics" selectedTeamName="AI Analytics">
    <div className="mx-auto max-w-[1320px] space-y-6">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">Quality operations</p><h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">AI analytics</h1><p className="mt-1.5 text-sm text-slate-600">Human review outcomes and routing activity for predictions visible to your account.</p></div>
        <div className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-white p-3 shadow-sm shadow-slate-200/40">
          <label className="text-xs font-medium text-slate-600">From<input type="date" value={from} max={to} onChange={(event) => setFrom(event.target.value)} className="mt-1 block rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-800 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100" /></label>
          <label className="text-xs font-medium text-slate-600">To<input type="date" value={to} min={from} max={defaultDate(0)} onChange={(event) => setTo(event.target.value)} className="mt-1 block rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-800 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100" /></label>
          <label className="text-xs font-medium text-slate-600">Model version<select value={modelVersion} onChange={(event) => setModelVersion(event.target.value)} className="mt-1 block max-w-44 rounded-md border border-slate-300 bg-white px-2 py-2 text-sm text-slate-800 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100"><option value="">All versions</option>{versionsToFilter.map((version) => <option key={version}>{version}</option>)}</select></label>
        </div>
      </header>
      {error ? <div role="alert" className="rounded-lg border border-red-200 bg-white p-5 text-sm text-red-700"><p className="font-semibold">Analytics could not be loaded</p><p className="mt-1">{error}</p><button type="button" onClick={() => setRefresh((value) => value + 1)} className="mt-3 rounded-md bg-blue-600 px-3 py-2 font-medium text-white hover:bg-blue-700">Retry</button></div>
        : loading && !data ? <div role="status" className="rounded-lg border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">Loading AI analytics…</div>
          : data && data.total_prediction_tickets === 0 ? <section className="rounded-lg border border-dashed border-slate-300 bg-white px-6 py-14 text-center"><h2 className="text-base font-semibold text-slate-900">No prediction records in this range</h2><p className="mx-auto mt-2 max-w-lg text-sm text-slate-500">Choose a wider date range or check back after ticket predictions have been recorded. Analytics never fills missing records with estimates.</p></section>
            : data && <>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <Metric title="Prediction tickets" value={String(data.total_prediction_tickets)} note="Latest in-range snapshot per ticket" />
                <Metric title="Reviewed tickets" value={String(data.reviewed_prediction_tickets)} note={`${data.unreviewed_prediction_tickets} without a recorded review`} />
                <Metric title="Review coverage" value={rate(data.review_coverage)} note={`${data.reviewed_prediction_tickets} / ${data.total_prediction_tickets} tickets`} />
                <Metric title="Category / priority decisions" value={`${data.category.reviewed} / ${data.priority.reviewed}`} note="Separate field-level denominators" />
              </div>
              <div className="grid gap-4 lg:grid-cols-2"><ReviewBreakdown title="Category review outcomes" data={data.category} /><ReviewBreakdown title="Priority review outcomes" data={data.priority} /></div>
              <div className="grid gap-4 lg:grid-cols-2">
                <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40"><h2 className="text-sm font-semibold text-slate-900">Review activity over time</h2><p className="mb-4 mt-1 text-xs text-slate-500">Reviews by day, limited to the selected prediction cohort and date range.</p><BarRows rows={data.review_activity.map((item) => ({ date: item.date, reviews: item.reviews }))} labelKey="date" countKey="reviews" /></section>
                <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40"><h2 className="text-sm font-semibold text-slate-900">AI team-routing distribution</h2><p className="mb-4 mt-1 text-xs text-slate-500">Distinct tickets with AI assignment events in this date range.</p><BarRows rows={data.ai_routing_distribution.map((item) => ({ team: item.team, tickets: item.tickets }))} labelKey="team" countKey="tickets" /></section>
              </div>
              <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40"><h2 className="text-sm font-semibold text-slate-900">Model-version review comparison</h2><p className="mb-4 mt-1 text-xs text-slate-500">Observed agent decisions grouped by model version. Counts are field-level review records.</p><div className="grid gap-5 md:grid-cols-2">
                <div><h3 className="mb-2 text-xs font-semibold text-slate-700">Category models</h3>{data.category_model_versions.length ? <ul className="divide-y divide-slate-100">{data.category_model_versions.map((item) => <li key={item.model_version} className="flex justify-between gap-4 py-2 text-xs"><span className="break-all font-medium text-slate-700">{item.model_version}</span><span className="shrink-0 text-right text-slate-600">{item.accepted} accepted / {item.overridden} overridden<br />{item.reviewed_tickets} reviewed tickets</span></li>)}</ul> : <p className="text-sm text-slate-500">Insufficient records.</p>}</div>
                <div><h3 className="mb-2 text-xs font-semibold text-slate-700">Priority models</h3>{data.priority_model_versions.length ? <ul className="divide-y divide-slate-100">{data.priority_model_versions.map((item) => <li key={item.model_version} className="flex justify-between gap-4 py-2 text-xs"><span className="break-all font-medium text-slate-700">{item.model_version}</span><span className="shrink-0 text-right text-slate-600">{item.accepted} accepted / {item.overridden} overridden<br />{item.reviewed_tickets} reviewed tickets</span></li>)}</ul> : <p className="text-sm text-slate-500">Insufficient records.</p>}</div>
              </div></section>
              <p className="rounded-md bg-slate-100 px-4 py-3 text-xs leading-5 text-slate-600">{data.limitations} These rates do not measure accuracy or probability calibration.</p>
            </>}
    </div>
  </AgentShell>;
}
