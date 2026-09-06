export type CreateTicketInput = {
  title: string;
  description: string;
  creator_id: number;
};

export type TicketResponse = {
  id: number;
  title: string;
  description: string;
  category: string | null;
  subcategory: string | null;
  priority: "LOW" | "MEDIUM" | "HIGH" | "URGENT";
  status: string;
  creator_id: number;
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

export async function createTicket(input: CreateTicketInput): Promise<TicketResponse> {
  let response: Response;

  try {
    response = await fetch(`${API_PROXY_PATH}/tickets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
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

  return payload as TicketResponse;
}
