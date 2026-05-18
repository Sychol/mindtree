export type AdminPayload = {
  id: string;
  email: string;
  displayName: string;
  role: string;
};

export type AdminLoginResponse = {
  accessToken: string;
  tokenType: "bearer";
  admin: AdminPayload;
};

export type AdminMeResponse = {
  admin: AdminPayload;
};

export type AdminDashboardResponse = {
  event: {
    slug: string;
    status: string;
  };
  metrics: {
    sessionCount: number;
    completedCount: number;
    cardCount: number;
    replyCount: number;
    reviewCount: number;
    keywordPendingCount: number;
    keywordFailedCount: number;
    completionIssuedCount: number;
    redeemedCount: number;
  };
};

export type AdminRiskFlags = {
  phq9Item9Positive: boolean;
  crisisExpressionDetected: boolean;
  traumaHighSignal: boolean;
  moralInjuryHighSignal: boolean;
  publicRestriction: boolean;
  helpNoticeRequired: boolean;
};

export type AdminReviewItemBase = {
  id: string;
  contentRaw: string;
  contentRedacted?: string | null;
  safetyStatus: string;
  publicStatus: string;
  moderationReason?: string | null;
  riskFlags: AdminRiskFlags;
  createdAt: string;
};

export type AdminCardReviewItem = AdminReviewItemBase & {
  promptType: string;
};

export type AdminReplyReviewItem = AdminReviewItemBase & {
  replyType: string;
  targetCardId: string;
};

export type AdminListResponse<T> = {
  items: T[];
  total: number;
};

export type ContentOrigin = "participant" | "admin_manual" | "system_seed";

export type AdminReviewRequest = {
  safetyStatus: string;
  publicStatus: string;
  contentRedacted?: string | null;
  reason?: string | null;
};

export type AdminKeywordItem = {
  id: string;
  keywordText: string;
  normalizedKeyword: string;
  category: string;
  weight: number;
  status: string;
  extractionMethod: string;
  sourceType: string;
  sourceId: string | null;
  origin?: ContentOrigin;
  originTag?: string | null;
  createdByAdminId?: string | null;
  createdAt: string;
};

export type AdminKeywordUpdateRequest = {
  normalizedKeyword?: string;
  category?: string;
  status?: string;
  reason?: string | null;
};

export type AdminManualKeywordCreateRequest = {
  keywordText: string;
  normalizedKeyword?: string;
  category: "mind_signal" | "support" | "recovery" | "coping" | "neutral";
  weight?: number;
  status?: "active" | "hidden" | "excluded";
  originTag?: string;
  reason?: string;
};

export type AdminManualKeywordStatusRequest = {
  status: "active" | "hidden" | "excluded";
  reason?: string;
};

export type AdminKeywordJobItem = {
  id: string;
  sourceType: string;
  sourceId: string;
  status: string;
  attempts: number;
  maxAttempts: number;
  fallbackUsed: boolean;
  provider?: string | null;
  errorMessage?: string | null;
  createdAt: string;
  updatedAt?: string | null;
};

export type AdminCompletionCode = {
  code: string;
  status: string;
  issuedAt: string;
  redeemedAt?: string | null;
};

export type AdminCompletionCodeResponse = {
  completionCode: AdminCompletionCode;
};

export type AdminCompletionCodeRedeemResponse = AdminCompletionCodeResponse & {
  auditLogCreated: boolean;
};

export type AdminAuditLogItem = {
  id: string;
  adminUserId?: string | null;
  action: string;
  targetType: string;
  targetId?: string | null;
  reason?: string | null;
  createdAt: string;
};

export type AdminResponsesView = "summary" | "wide" | "long";

export type AdminResponseColumn = {
  key: string;
  label: string;
  type: "text" | "answer" | "score" | "risk" | "completion" | string;
  questionNo?: number | null;
  questionKey?: string | null;
  scaleCode?: string | null;
};

export type AdminResponseRowValue = string | number | boolean | null;

export type AdminResponsesListResponse = {
  columns: AdminResponseColumn[];
  rows: Array<Record<string, AdminResponseRowValue>>;
  total: number;
  limit: number;
  offset: number;
};

export type AdminResponsesColumnsResponse = {
  summaryColumns: AdminResponseColumn[];
  questionColumns: AdminResponseColumn[];
  scoreColumns: AdminResponseColumn[];
  riskColumns: AdminResponseColumn[];
};

export type AdminResponsesListFilters = {
  view?: AdminResponsesView;
  status?: string;
  completedOnly?: boolean;
  includeScores?: boolean;
  includeRiskFlags?: boolean;
  includeCompletionStatus?: boolean;
  createdFrom?: string;
  createdTo?: string;
  limit?: number;
  offset?: number;
};

export type AdminResponsesExportRequest = {
  format: "wide" | "long";
  includeScores?: boolean;
  includeRiskFlags?: boolean;
  includeCompletionStatus?: boolean;
  status?: string;
  completedOnly?: boolean;
  createdFrom?: string | null;
  createdTo?: string | null;
  reason: string;
};
