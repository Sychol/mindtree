import { requestJson } from "./client";
import { getStoredAdminToken } from "../state/adminAuth";
import type {
  AdminAuditLogItem,
  AdminCardReviewItem,
  AdminCompletionCodeRedeemResponse,
  AdminCompletionCodeResponse,
  AdminDashboardResponse,
  AdminKeywordItem,
  AdminKeywordJobItem,
  AdminKeywordUpdateRequest,
  AdminListResponse,
  AdminLoginResponse,
  AdminMeResponse,
  AdminReplyReviewItem,
  AdminReviewRequest,
} from "../types/admin";

type ListFilters = {
  status?: string;
  category?: string;
  action?: string;
  targetType?: string;
  limit?: number;
  offset?: number;
};

function encoded(value: string): string {
  return encodeURIComponent(value);
}

function queryString(filters: ListFilters = {}): string {
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

export function listAdminKeywords(
  eventSlug: string,
  filters: ListFilters = {}
): Promise<AdminListResponse<AdminKeywordItem>> {
  return requestJson<AdminListResponse<AdminKeywordItem>>(
    `/admin/events/${encoded(eventSlug)}/keywords${queryString(filters)}`,
    { authToken: adminToken() }
  );
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
