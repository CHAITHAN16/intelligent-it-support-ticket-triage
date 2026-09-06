export type CreateTicketInput = {
  title: string;
  description: string;
  creator_id: number;
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

type ApiErrorPayload = {
  detail?: string | Array<{ msg?: string }>;
};

const API_PROXY_PATH = "/api/backend";

function getErrorMessage(payload: ApiErrorPayload): string {
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((item) => item.msg ?? "Invalid request").join(" ");
  }

  return payload.detail ?? "The request could not be completed.";
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_PROXY_PATH}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
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
    throw new Error(getErrorMessage(payload as ApiErrorPayload));
  }

  return payload as T;
}

export async function createTicket(input: CreateTicketInput): Promise<TicketResponse> {
  return request<TicketResponse>("/tickets", {
    method: "POST",
    body: JSON.stringify(input),
  });
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
