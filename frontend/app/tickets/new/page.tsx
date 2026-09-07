"use client";

import { FormEvent, useState } from "react";

import { SiteHeader } from "@/components/site-header";
import { TicketResultCard } from "@/components/ticket-result-card";
import { createTicket, TEMPORARY_EMPLOYEE_ID, type TicketResponse } from "@/lib/api";

const TITLE_MAX_LENGTH = 255;
const DESCRIPTION_MAX_LENGTH = 5000;

type FormErrors = { title?: string; description?: string };

function validate(title: string, description: string): FormErrors {
  const errors: FormErrors = {};
  if (!title.trim()) errors.title = "Add a short title for the issue.";
  if (title.trim().length > TITLE_MAX_LENGTH) errors.title = `Keep the title under ${TITLE_MAX_LENGTH} characters.`;
  if (!description.trim()) errors.description = "Tell us what is happening so we can help.";
  if (description.trim().length > DESCRIPTION_MAX_LENGTH) errors.description = `Keep the description under ${DESCRIPTION_MAX_LENGTH} characters.`;
  return errors;
}

export default function NewTicketPage() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [ticket, setTicket] = useState<TicketResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors = validate(title, description);
    setErrors(nextErrors);
    setSubmitError(null);
    if (Object.keys(nextErrors).length > 0) return;

    setIsSubmitting(true);
    try {
      const createdTicket = await createTicket({ title: title.trim(), description: description.trim(), creator_id: TEMPORARY_EMPLOYEE_ID });
      setTicket(createdTicket);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "We could not submit your ticket.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function startAnotherTicket() {
    setTicket(null);
    setTitle("");
    setDescription("");
    setErrors({});
    setSubmitError(null);
  }

  return (
    <div className="min-h-screen bg-[#f6f8fb] text-slate-950">
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-5 py-12 sm:px-8 sm:py-16">
        <div className="mx-auto max-w-3xl">
          {ticket ? (
            <>
              <div className="mb-8">
                <p className="text-sm font-semibold uppercase tracking-[0.22em] text-sky-600">Request received</p>
                <h1 className="mt-3 text-4xl font-semibold tracking-[-0.035em] text-slate-950">Your support ticket</h1>
              </div>
              <TicketResultCard ticket={ticket} />
              <button type="button" onClick={startAnotherTicket} className="mt-6 text-sm font-semibold text-sky-700 underline decoration-sky-300 underline-offset-4 hover:text-sky-900">Submit another ticket</button>
            </>
          ) : (
            <>
              <div className="mb-9">
                <p className="text-sm font-semibold uppercase tracking-[0.22em] text-sky-600">Employee support</p>
                <h1 className="mt-3 text-4xl font-semibold tracking-[-0.035em] text-slate-950 sm:text-5xl">Submit a ticket</h1>
                <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">Describe the problem in your own words. The support team will use your details to investigate and respond.</p>
              </div>

              <form onSubmit={handleSubmit} noValidate className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-900/5 sm:p-9">
                <div className="space-y-7">
                  <div>
                    <label htmlFor="title" className="text-sm font-semibold text-slate-900">Title</label>
                    <p className="mt-1 text-sm text-slate-500">A concise summary helps us understand the request quickly.</p>
                    <input id="title" name="title" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={TITLE_MAX_LENGTH} aria-invalid={Boolean(errors.title)} aria-describedby={errors.title ? "title-error" : "title-help"} className="mt-3 w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:bg-white focus:ring-4 focus:ring-sky-500/10 aria-[invalid=true]:border-rose-400" placeholder="For example: VPN connection keeps dropping" />
                    <div className="mt-2 flex justify-between gap-3 text-xs text-slate-400">
                      {errors.title ? <span id="title-error" className="font-medium text-rose-600">{errors.title}</span> : <span id="title-help">Required</span>}
                      <span>{title.length}/{TITLE_MAX_LENGTH}</span>
                    </div>
                  </div>

                  <div>
                    <label htmlFor="description" className="text-sm font-semibold text-slate-900">Description</label>
                    <p className="mt-1 text-sm text-slate-500">Include what you were doing, what you expected, and what happened instead.</p>
                    <textarea id="description" name="description" value={description} onChange={(event) => setDescription(event.target.value)} maxLength={DESCRIPTION_MAX_LENGTH} rows={8} aria-invalid={Boolean(errors.description)} aria-describedby={errors.description ? "description-error" : "description-help"} className="mt-3 w-full resize-y rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:bg-white focus:ring-4 focus:ring-sky-500/10 aria-[invalid=true]:border-rose-400" placeholder="Share the details that might help the support team investigate..." />
                    <div className="mt-2 flex justify-between gap-3 text-xs text-slate-400">
                      {errors.description ? <span id="description-error" className="font-medium text-rose-600">{errors.description}</span> : <span id="description-help">Required</span>}
                      <span>{description.length}/{DESCRIPTION_MAX_LENGTH}</span>
                    </div>
                  </div>
                </div>

                {submitError && <div role="alert" className="mt-7 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-800">{submitError}</div>}

                <div className="mt-8 flex flex-col-reverse items-stretch justify-between gap-4 border-t border-slate-200 pt-6 sm:flex-row sm:items-center">
                  <p className="text-xs leading-5 text-slate-500">Your request will be automatically triaged for the right support team.</p>
                  <button type="submit" disabled={isSubmitting} className="inline-flex min-w-36 items-center justify-center rounded-full bg-sky-500 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-sky-500/20 transition hover:bg-sky-600 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:shadow-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500">
                    {isSubmitting ? <><span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" aria-hidden="true" />Submitting...</> : "Submit ticket"}
                  </button>
                </div>
              </form>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
