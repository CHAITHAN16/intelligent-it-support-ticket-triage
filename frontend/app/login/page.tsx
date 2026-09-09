"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { SiteHeader } from "@/components/site-header";
import { useAuth } from "@/lib/auth";

function homeForRole(role: "EMPLOYEE" | "AGENT" | "ADMIN"): string {
  if (role === "AGENT") return "/agent";
  if (role === "EMPLOYEE") return "/tickets";
  return "/";
}

export default function LoginPage() {
  const router = useRouter();
  const { user, isLoading, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isLoading && user) router.replace(homeForRole(user.role));
  }, [isLoading, router, user]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedEmail = email.trim();
    if (!normalizedEmail || !password) {
      setError("Enter your email and password.");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const authenticatedUser = await login(normalizedEmail, password);
      router.replace(homeForRole(authenticatedUser.role));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Login failed. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f6f8fb] text-slate-950">
      <SiteHeader />
      <main className="mx-auto flex max-w-6xl justify-center px-5 py-16 sm:px-8 sm:py-24">
        <section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-7 shadow-xl shadow-slate-900/5 sm:p-9">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-sky-600">Welcome back</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.04em] text-slate-950">Sign in</h1>
          <p className="mt-4 text-sm leading-6 text-slate-600">Use your support portal account to continue.</p>
          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            <label className="block text-sm font-semibold text-slate-700">Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-500/10" /></label>
            <label className="block text-sm font-semibold text-slate-700">Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-500/10" /></label>
            {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-800">{error}</p>}
            <button type="submit" disabled={isSubmitting} className="w-full rounded-full bg-sky-500 px-5 py-3.5 text-sm font-semibold text-white shadow-lg shadow-sky-500/20 transition hover:bg-sky-600 disabled:cursor-not-allowed disabled:bg-slate-300">{isSubmitting ? "Signing in..." : "Sign in"}</button>
          </form>
        </section>
      </main>
    </div>
  );
}
