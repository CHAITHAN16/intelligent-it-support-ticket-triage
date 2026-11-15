import type { SVGProps } from "react";

type IconName = "layout-dashboard" | "users" | "tickets" | "clock" | "chart" | "chevron-left" | "ticket" | "user-check" | "users-round" | "arrow-right" | "history" | "brain-circuit" | "message-circle" | "activity" | "check-circle" | "alert-circle" | "alert-triangle" | "calendar-clock" | "sparkles" | "check" | "user" | "sun" | "moon" | "flame" | "inbox" | "layers";

const paths: Record<IconName, React.ReactNode> = {
  "layout-dashboard": <><rect x="3" y="3" width="7" height="9" rx="1" /><rect x="14" y="3" width="7" height="5" rx="1" /><rect x="14" y="12" width="7" height="9" rx="1" /><rect x="3" y="16" width="7" height="5" rx="1" /></>,
  users: <><path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="10" cy="7" r="4" /><path d="M20 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></>,
  tickets: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v18H6.5A2.5 2.5 0 0 1 4 18.5z" /><path d="M4 6h16M8 10h8M8 14h8M8 18h5" /></>,
  clock: <><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></>,
  chart: <><path d="M3 3v18h18" /><path d="m19 9-5 5-4-4-5 5" /></>,
  "chevron-left": <><rect x="2.5" y="3" width="15" height="14" rx="2" /><path d="M7.5 3v14M13 7l-3 3 3 3" /></>,
  ticket: <><path d="M2 9a3 3 0 0 0 0 6v4h20v-4a3 3 0 0 1 0-6V5H2z" /><path d="M13 5v2M13 11v2M13 17v2" /></>,
  "user-check": <><path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="10" cy="7" r="4" /><path d="m16 11 2 2 4-4" /></>,
  "users-round": <><path d="M18 21a8 8 0 0 0-16 0" /><circle cx="10" cy="8" r="5" /><path d="M22 20c0-4-2-6-5-7M16 3.1a5 5 0 0 1 0 9.8" /></>,
  "arrow-right": <><path d="M5 12h14M12 5l7 7-7 7" /></>,
  history: <><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5M12 7v5l4 2" /></>,
  "brain-circuit": <><path d="M12 18V5M15 13a4.17 4.17 0 0 1-3-4 4.17 4.17 0 0 1-3 4M17.6 6.5a3 3 0 0 0-5.6-1.5 3 3 0 0 0-5.6 1.5A3 3 0 0 0 5 12a3 3 0 0 0 3 5.8 3 3 0 0 0 4 1.2 3 3 0 0 0 4-1.2A3 3 0 0 0 19 12a3 3 0 0 0-1.4-5.5Z" /><path d="M12 9h4M12 15H8" /></>,
  "message-circle": <><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22z" /><path d="M8 10h8M8 14h5" /></>,
  activity: <><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></>,
  "check-circle": <><circle cx="12" cy="12" r="10" /><path d="m9 12 2 2 4-4" /></>,
  "alert-circle": <><circle cx="12" cy="12" r="10" /><path d="M12 8v4M12 16h.01" /></>,
  "alert-triangle": <><path d="m10.3 3.9-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3.1l-8-14a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4M12 17h.01" /></>,
  "calendar-clock": <><path d="M8 2v4M16 2v4M3 10h12M5 4h14a2 2 0 0 1 2 2v7" /><rect x="3" y="4" width="18" height="17" rx="2" /><circle cx="18" cy="18" r="4" /><path d="M18 16v2l1 1" /></>,
  sparkles: <><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2zM19 14l1.2 2.8L23 18l-2.8 1.2L19 22l-1.2-2.8L15 18l2.8-1.2z" /></>,
  check: <path d="m5 12 4 4L19 6" />,
  user: <><circle cx="12" cy="8" r="5" /><path d="M20 21a8 8 0 0 0-16 0" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" /></>,
  moon: <path d="M20.9 13A9 9 0 0 1 11 3.1 9 9 0 1 0 20.9 13Z" />,
  flame: <path d="M8.5 14.5A2.5 2.5 0 0 0 11 17c1.4 0 2.5-1.1 2.5-2.5 0-2-2-3-1.5-6.5 3 2 7 5 7 10a7 7 0 0 1-14 0c0-3 1.5-5.5 4-8-.2 2-.3 3.5-.5 4.5Z" />,
  inbox: <><path d="M4 4h16l2 10v5H2v-5z" /><path d="M2 14h5l2 3h6l2-3h5" /></>,
  layers: <><path d="m12 2 9 5-9 5-9-5z" /><path d="m3 12 9 5 9-5M3 17l9 5 9-5" /></>,
};

export function UiIcon({ name, className = "h-4 w-4", ...props }: SVGProps<SVGSVGElement> & { name: IconName }) {
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={`shrink-0 ${className}`} {...props}>{paths[name]}</svg>;
}
