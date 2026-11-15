"use client";

import { useEffect, useSyncExternalStore } from "react";

import { UiIcon } from "@/components/ui-icon";

type Theme = "light" | "dark";
const THEME_KEY = "support-dashboard-theme";
const THEME_EVENT = "support-dashboard-theme-change";
let memoryTheme: Theme = "light";

function getTheme(): Theme {
  try {
    const saved = window.localStorage.getItem(THEME_KEY);
    if (saved === "dark" || saved === "light") return saved;
  } catch {
    // Keep the in-memory theme if browser storage is unavailable.
  }
  return memoryTheme;
}

function getServerTheme(): Theme {
  return "light";
}

function subscribe(onChange: () => void) {
  window.addEventListener("storage", onChange);
  window.addEventListener(THEME_EVENT, onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener(THEME_EVENT, onChange);
  };
}

function saveTheme(theme: Theme) {
  memoryTheme = theme;
  document.documentElement.dataset.theme = theme;
  try {
    window.localStorage.setItem(THEME_KEY, theme);
  } catch {
    // The selected theme remains active for this page.
  }
  window.dispatchEvent(new Event(THEME_EVENT));
}

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, getTheme, getServerTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const nextTheme: Theme = theme === "light" ? "dark" : "light";
  return <button type="button" onClick={() => saveTheme(nextTheme)} aria-label={`Switch to ${nextTheme} mode`} aria-pressed={theme === "dark"} title={`Switch to ${nextTheme} mode`} className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50"><UiIcon name={theme === "light" ? "moon" : "sun"} className="h-4 w-4" /><span className="sr-only">{nextTheme === "dark" ? "Dark mode" : "Light mode"}</span></button>;
}
