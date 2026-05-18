import { API_BASE_URL, ApiClientError, NetworkError, requestJson } from "./client";
import { getStoredAdminToken } from "../state/adminAuth";
import type {
  AdminAuditLogItem,
  AdminCardReviewItem,
  AdminCompletionCodeRedeemResponse,
  AdminCompletionCodeResponse,
  AdminDashboardResponse,
  AdminKeywordItem,
  AdminKeywordJobItem,
  AdminManualCardCreateRequest,
  AdminManualContentStatusRequest,
  AdminManualKeywordCreateRequest,
  AdminManualKeywordStatusRequest,
  AdminManualReplyCreateRequest,
  AdminKeywordUpdateRequest,
  AdminListResponse,
  AdminLoginResponse,
  AdminMeResponse,
  AdminReplyReviewItem,
  AdminReviewRequest,
  AdminResponsesColumnsResponse,
  AdminResponsesExportRequest,
  AdminResponsesListFilters,
  AdminResponsesListResponse,
} from "../types/admin";

type QueryFilters = Record<string, string | number | boolean | null | undefined>;

type ListFilters = QueryFilters & {
  status?: string;
  category?: string;
  origin?: string;
  action?: string;
  targetType?: string;
  limit?: number;
  offset?: number;
};

function encoded(value: string): string {
  return encodeURIComponent(value);
}

function queryString(filters: QueryFilters = {}): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

function adminToken(): string | null {
  return getStoredAdminToken();
}

function adminUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

function filenameFromContentDisposition(value: string | null): string | null {
  if (!value) {
    return null;
  }
  const utf8Match = value.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1].replace(/"/g, ""));
  }
  const filenameMatch = value.match(/filename="?([^";]+)"?/i);
  return filenameMatch?.[1] ?? null;
}

async function requestAdminBlob(path: string, body: unknown): Promise<Blob> {
  const headers = new Headers();
  headers.set("Accept", "text/csv");
  headers.set("Content-Type", "application/json");
  const token = adminToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(adminUrl(path), {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
  } catch {
    throw new NetworkError();
  }

  if (!response.ok) {
    const text = await response.text();
    try {
      const parsed = JSON.parse(text);
      if (parsed?.error) {
        throw new ApiClientError(
          parsed.error.message,
          parsed.error.code,
          response.status,
          parsed.error.details
        );
      }
    } catch (error) {
      if (error instanceof ApiClientError) {
        throw error;
      }
    }
    throw new ApiClientError("CSV export request failed.", "INTERNAL_ERROR", response.status);
  }

  const blob = await response.blob();
  const filename = filenameFromContentDisposition(response.headers.get("Content-Disposition"));
  return filename ? new File([blob], filename, { type: blob.type }) : blob;
}

export function adminLogin(email: string, password: string): Promise<AdminLoginResponse> {
  return requestJson<AdminLoginResponse>("/admin/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

export function getAdminMe(token = adminToken()): Promise<AdminMeResponse> {
  return requestJson<AdminMeResponse>("/admin/auth/me", { authToken: token });
}

export function getAdminDashboard(eventSlug: string): Promise<AdminDashboardResponse> {
  return requestJson<AdminDashboardResponse>(`/admin/events/${encoded(eventSlug)}/dashboard`, {
    authToken: adminToken(),
  });
}

export function listAdminCards(
  eventSlug: string,
  filters: ListFilters = {}
): Promise<AdminListResponse<AdminCardReviewItem>> {
  return requestJson<AdminListResponse<AdminCardReviewItem>>(
    `/admin/events/${encoded(eventSlug)}/cards${queryString(filters)}`,
    { authToken: adminToken() }
  );
}

export function reviewAdminCard(
  cardId: string,
  payload: AdminReviewRequest
): Promise<{ auditLogCreated: boolean }> {
  return requestJson(`/admin/cards/${encoded(cardId)}/review`, {
    method: "PATCH",
    body: payload,
    authToken: adminToken(),
  });
}

export function createManualCard(
  eventSlug: string,
  payload: AdminManualCardCreateRequest
): Promise<{ auditLogCreated: boolean; card: AdminCardReviewItem; keywordJob?: { id: string; status: string } | null }> {
  return requestJson(`/admin/events/${encoded(eventSlug)}/manual-cards`, {
    method: "POST",
    body: payload,
    authToken: adminToken(),
  });
}

export function updateManualCardStatus(
  cardId: string,
  payload: AdminManualContentStatusRequest
): Promise<{ auditLogCreated: boolean; card: AdminCardReviewItem }> {
  return requestJson(`/admin/manual-cards/${encoded(cardId)}/status`, {
    method: "PATCH",
    body: payload,
    authToken: adminToken(),
  });
}

export function listAdminReplies(
  eventSlug: string,
  filters: ListFilters = {}
): Promise<AdminListResponse<AdminReplyReviewItem>> {
  return requestJson<AdminListResponse<AdminReplyReviewItem>>(
    `/admin/events/${encoded(eventSlug)}/replies${queryString(filters)}`,
    { authToken: adminToken() }
  );
}

export function reviewAdminReply(
  replyId: string,
  payload: AdminReviewRequest
): Promise<{ auditLogCreated: boolean }> {
  return requestJson(`/admin/replies/${encoded(replyId)}/review`, {
    method: "PATCH",
    body: payload,
    authToken: adminToken(),
  });
}

export function createManualReply(
  eventSlug: string,
  payload: AdminManualReplyCreateRequest
): Promise<{ auditLogCreated: boolean; reply: AdminReplyReviewItem; keywordJob?: { id: string; status: string } | null }> {
  return requestJson(`/admin/events/${encoded(eventSlug)}/manual-replies`, {
    method: "POST",
    body: payload,
    authToken: adminToken(),
  });
}

export function updateManualReplyStatus(
  replyId: string,
  payload: AdminManualContentStatusRequest
): Promise<{ auditLogCreated: boolean; reply: AdminReplyReviewItem }> {
  return requestJson(`/admin/manual-replies/${encoded(replyId)}/status`, {
    method: "PATCH",
    body: payload,
    authToken: adminToken(),
  });
}

export function listAdminKeywords(
  eventSlug: string,
  filters: ListFilters = {}
): Promise<AdminListResponse<AdminKeywordItem>> {
  return requestJson<AdminListResponse<AdminKeywordItem>>(
    `/admin/events/${encoded(eventSlug)}/keywords${queryString(filters)}`,
    { authToken: adminToken() }
  );
}

export function createManualKeyword(
  eventSlug: string,
  payload: AdminManualKeywordCreateRequest
): Promise<{ auditLogCreated: boolean; keyword: AdminKeywordItem }> {
  return requestJson(`/admin/events/${encoded(eventSlug)}/keywords/manual`, {
    method: "POST",
    body: payload,
    authToken: adminToken(),
  });
}

export function updateAdminKeyword(
  keywordId: string,
  payload: AdminKeywordUpdateRequest
): Promise<{ auditLogCreated: boolean; keyword: AdminKeywordItem }> {
  return requestJson(`/admin/keywords/${encoded(keywordId)}`, {
    method: "PATCH",
    body: payload,
    authToken: adminToken(),
  });
}

export function updateManualKeywordStatus(
  keywordId: string,
  payload: AdminManualKeywordStatusRequest
): Promise<{ auditLogCreated: boolean; keyword: AdminKeywordItem }> {
  return requestJson(`/admin/keywords/${encoded(keywordId)}/manual-status`, {
    method: "PATCH",
    body: payload,
    authToken: adminToken(),
  });
}

export function listAdminKeywordJobs(
  eventSlug: string,
  filters: ListFilters = {}
): Promise<AdminListResponse<AdminKeywordJobItem>> {
  return requestJson<AdminListResponse<AdminKeywordJobItem>>(
    `/admin/events/${encoded(eventSlug)}/keyword-jobs${queryString(filters)}`,
    { authToken: adminToken() }
  );
}

export function retryAdminKeywordJob(
  jobId: string,
  reason?: string
): Promise<{ auditLogCreated: boolean; job: AdminKeywordJobItem }> {
  return requestJson(`/admin/keyword-jobs/${encoded(jobId)}/retry`, {
    method: "POST",
    body: { reason },
    authToken: adminToken(),
  });
}

export function getCompletionCode(
  eventSlug: string,
  code: string
): Promise<AdminCompletionCodeResponse> {
  return requestJson<AdminCompletionCodeResponse>(
    `/admin/events/${encoded(eventSlug)}/completion-codes/${encoded(code)}`,
    { authToken: adminToken() }
  );
}

export function redeemCompletionCode(
  eventSlug: string,
  code: string,
  notes?: string
): Promise<AdminCompletionCodeRedeemResponse> {
  return requestJson<AdminCompletionCodeRedeemResponse>(
    `/admin/events/${encoded(eventSlug)}/completion-codes/${encoded(code)}/redeem`,
    {
      method: "POST",
      body: { notes },
      authToken: adminToken(),
    }
  );
}

export function listAuditLogs(
  eventSlug: string,
  filters: ListFilters = {}
): Promise<AdminListResponse<AdminAuditLogItem>> {
  return requestJson<AdminListResponse<AdminAuditLogItem>>(
    `/admin/events/${encoded(eventSlug)}/audit-logs${queryString(filters)}`,
    { authToken: adminToken() }
  );
}

export function listAdminResponses(
  eventSlug: string,
  filters: AdminResponsesListFilters = {}
): Promise<AdminResponsesListResponse> {
  return requestJson<AdminResponsesListResponse>(
    `/admin/events/${encoded(eventSlug)}/responses${queryString(filters)}`,
    { authToken: adminToken() }
  );
}

export function getAdminResponseColumns(eventSlug: string): Promise<AdminResponsesColumnsResponse> {
  return requestJson<AdminResponsesColumnsResponse>(
    `/admin/events/${encoded(eventSlug)}/responses/columns`,
    { authToken: adminToken() }
  );
}

export function exportAdminResponsesCsv(
  eventSlug: string,
  request: AdminResponsesExportRequest
): Promise<Blob> {
  return requestAdminBlob(
    `/admin/events/${encoded(eventSlug)}/responses/export.csv`,
    request
  );
}
