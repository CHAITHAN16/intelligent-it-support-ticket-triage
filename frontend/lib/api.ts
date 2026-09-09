export type CreateTicketInput = {
  title: string;
  description: string;
};

export type AuthRole = "EMPLOYEE" | "AGENT" | "ADMIN";

export type AuthUser = {
  id: number;
  name: string;
  email: string;
  role: AuthRole;
  active: boolean;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

export type TicketStatus = "NEW" | "ASSIGNED" | "IN_PROGRESS" | "WAITING_FOR_USER" | "RESOLVED" | "CLOSED";
export type TicketPriority = "LOW" | "MEDIUM" | "HIGH" | "URGENT";

export type TicketUpdateInput = {
  category?: string;
  priority?: TicketPriority;
  status?: TicketStatus;
};

export type Team = {
  id: number;
  name: string;
};

export type TeamTicketFilters = {
  status?: TicketStatus;
  priority?: TicketPriority;
  category?: string;
  sort?: "newest" | "oldest" | "priority";
};

export type TicketResponse = {
  id: number;
  title: string;
  description: string;
  category: string | null;
  subcategory: string | null;
  priority: TicketPriority;
  status: TicketStatus;
  creator_id: number;
  created_at: string;
  updated_at: string;
  ai_predicted_category: string | null;
  ai_predicted_subcategory: string | null;
  ai_predicted_priority: "LOW" | "MEDIUM" | "HIGH" | "URGENT" | null;
  ai_confidence: number | null;
  ai_model_version: string | null;
  ai_triaged_at: string | null;
  assigned_team_id?: number | null;
  assigned_team_name?: string | null;
  assigned_team?: { name?: string | null } | null;
};

export function isTicketProcessingComplete(ticket: TicketResponse): boolean {
  return Boolean(
    ticket.ai_predicted_category &&
      ticket.ai_predicted_priority &&
      (ticket.assigned_team_name || ticket.assigned_team_id !== null && ticket.assigned_team_id !== undefined),
  );
}

export type TicketComment = {
  id: number;
  ticket_id: number;
  author_id: number;
  body: string;
  created_at: string;
  updated_at: string;
};

export type TicketStatusHistory = {
  id: number;
  ticket_id: number;
  old_status: TicketStatus | null;
  new_status: TicketStatus;
  changed_by_id: number | null;
  changed_at: string;
  note: string | null;
};

type ApiErrorPayload = {
  detail?: string | Array<{ msg?: string }>;
};

const API_PROXY_PATH = "/api/backend";
const ACCESS_TOKEN_STORAGE_KEY = "it-support-access-token";

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
}

export function storeAccessToken(token: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
}

export function clearAccessToken(): void {
  if (typeof window !== "undefined") window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
}

function getErrorMessage(payload: ApiErrorPayload): string {
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((item) => item.msg ?? "Invalid request").join(" ");
  }

  return payload.detail ?? "The request could not be completed.";
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  const headers = new Headers(options?.headers);
  headers.set("Content-Type", "application/json");
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  try {
    response = await fetch(`${API_PROXY_PATH}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw new Error("The support service is unavailable. Check that the backend is running.");
  }

  let payload: TicketResponse | ApiErrorPayload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`The support service returned an invalid response (${response.status}).`);
  }

  if (!response.ok) {
    if (response.status === 401 && token && typeof window !== "undefined") {
      window.dispatchEvent(new Event("auth:unauthorized"));
    }
    throw new ApiError(getErrorMessage(payload as ApiErrorPayload), response.status);
  }

  return payload as T;
}

export async function createTicket(input: CreateTicketInput): Promise<TicketResponse> {
  return request<TicketResponse>("/tickets", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function getTickets(creatorId?: number): Promise<TicketResponse[]> {
  const query = creatorId === undefined ? "" : `?creator_id=${encodeURIComponent(creatorId)}`;
  return request<TicketResponse[]>(`/tickets${query}`);
}

export async function getMyTickets(): Promise<TicketResponse[]> {
  return getTickets();
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getCurrentUser(): Promise<AuthUser> {
  return request<AuthUser>("/auth/me");
}

export async function getTeams(): Promise<Team[]> {
  return request<Team[]>("/teams");
}

export async function getTeamTickets(teamId: number, filters: TeamTicketFilters = {}): Promise<TicketResponse[]> {
  const query = new URLSearchParams();
  if (filters.status) query.set("status", filters.status);
  if (filters.priority) query.set("priority", filters.priority);
  if (filters.category) query.set("category", filters.category);
  if (filters.sort) query.set("sort", filters.sort);

  const queryString = query.toString();
  return request<TicketResponse[]>(`/teams/${teamId}/tickets${queryString ? `?${queryString}` : ""}`);
}

export async function getTicket(ticketId: number): Promise<TicketResponse> {
  return request<TicketResponse>(`/tickets/${ticketId}`);
}

export async function updateTicket(ticketId: number, input: TicketUpdateInput): Promise<TicketResponse> {
  return request<TicketResponse>(`/tickets/${ticketId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export async function createTicketComment(ticketId: number, body: string): Promise<TicketComment> {
  return request<TicketComment>(`/tickets/${ticketId}/comments`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
}

export async function getTicketComments(ticketId: number): Promise<TicketComment[]> {
  return request<TicketComment[]>(`/tickets/${ticketId}/comments`);
}

export async function getTicketHistory(ticketId: number): Promise<TicketStatusHistory[]> {
  return request<TicketStatusHistory[]>(`/tickets/${ticketId}/history`);
}
