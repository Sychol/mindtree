import { ApiClientError, NetworkError } from "../api/client";

const STATUS_LABELS: Record<string, string> = {
  active: "활성",
  all: "전체",
  closed: "종료",
  draft: "준비 중",
  exclude: "제외 필요",
  excluded: "제외",
  failed: "실패",
  hidden: "숨김",
  issued: "발급됨",
  loading: "불러오는 중",
  open: "운영 중",
  pending: "대기",
  processing: "처리 중",
  public: "공개",
  redeemed: "지급 완료",
  retry_wait: "재시도 대기",
  review: "검토 필요",
  safe: "안전",
  succeeded: "성공",
  void: "무효",
};

const CATEGORY_LABELS: Record<string, string> = {
  coping: "대처",
  mind_signal: "마음신호",
  neutral: "중립",
  recovery: "회복",
  support: "응원",
};

const SOURCE_TYPE_LABELS: Record<string, string> = {
  admin: "관리자",
  admin_manual: "관리자 추가",
  admin_user: "관리자",
  card: "마음카드",
  completion_code: "완료 코드",
  keyword: "키워드",
  keyword_job: "키워드 작업",
  mind_card: "마음카드",
  reply: "응원문장",
};

const PROMPT_TYPE_LABELS: Record<string, string> = {
  stress_memory: "힘들었던 시간",
  to_colleague: "동료에게",
  to_now_me: "지금의 나에게",
  to_past_me: "과거의 나에게",
};

const REPLY_TYPE_LABELS: Record<string, string> = {
  comfort: "위로",
  empathy: "공감",
  small_coping: "작은 대처",
};

const PROVIDER_LABELS: Record<string, string> = {
  disabled: "비활성",
  fallback: "대체 추출",
  mock: "모의 실행",
  openai: "외부 분석",
  policy: "정책 제외",
};

const ACTION_LABELS: Record<string, string> = {
  "admin.login_failed": "관리자 로그인 실패",
  "card.delete": "카드 삭제",
  "card.edit": "카드 수정",
  "card.hide": "카드 숨김",
  "card.publish": "카드 공개",
  "completion_code.redeem": "완료 코드 지급",
  "completion_code.void": "완료 코드 무효화",
  "keyword.edit": "키워드 수정",
  "keyword.hide": "키워드 숨김",
  "keyword.recalculate": "키워드 재계산",
  "keyword_job.retry": "키워드 작업 재시도",
  "manual_card.create": "수동 마음카드 추가",
  "manual_card.update_status": "수동 마음카드 상태 변경",
  "manual_keyword.create": "수동 키워드 추가",
  "manual_keyword.update_status": "수동 키워드 상태 변경",
  "manual_reply.create": "수동 응원문장 추가",
  "manual_reply.update_status": "수동 응원문장 상태 변경",
  "reply.delete": "응원문장 삭제",
  "reply.edit": "응원문장 수정",
  "reply.hide": "응원문장 숨김",
  "reply.publish": "응원문장 공개",
};

const ERROR_CODE_LABELS: Record<string, string> = {
  BAD_REQUEST: "요청 내용을 확인해 주세요.",
  CARD_NOT_FOUND: "마음카드를 찾을 수 없습니다.",
  COMPLETION_CODE_ALREADY_REDEEMED: "이미 지급 처리된 완료 코드입니다.",
  COMPLETION_CODE_NOT_FOUND: "완료 코드를 찾을 수 없습니다.",
  EVENT_NOT_FOUND: "이벤트를 찾을 수 없습니다.",
  FORBIDDEN: "접근 권한이 없습니다.",
  INTERNAL_ERROR: "서버 오류가 발생했습니다.",
  REPLY_NOT_FOUND: "응원문장을 찾을 수 없습니다.",
  UNAUTHORIZED: "관리자 로그인이 필요합니다.",
};

export const AUDIT_ACTION_FILTERS = [
  "",
  "card.publish",
  "card.hide",
  "card.edit",
  "reply.publish",
  "reply.hide",
  "reply.edit",
  "keyword.hide",
  "keyword.edit",
  "keyword.recalculate",
  "manual_card.create",
  "manual_card.update_status",
  "manual_reply.create",
  "manual_reply.update_status",
  "manual_keyword.create",
  "manual_keyword.update_status",
  "keyword_job.retry",
  "completion_code.redeem",
  "completion_code.void",
  "admin.login_failed",
] as const;

export const AUDIT_TARGET_FILTERS = [
  "",
  "mind_card",
  "card",
  "reply",
  "keyword",
  "keyword_job",
  "completion_code",
] as const;

export function adminStatusLabel(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  return STATUS_LABELS[value] ?? "기타 상태";
}

export function adminCategoryLabel(value: string | null | undefined): string {
  if (!value) {
    return "전체 분류";
  }
  return CATEGORY_LABELS[value] ?? "기타 분류";
}

export function adminSourceTypeLabel(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  return SOURCE_TYPE_LABELS[value] ?? "기타 원본";
}

export function adminPromptTypeLabel(value: string | null | undefined): string {
  if (!value) {
    return "마음카드";
  }
  return PROMPT_TYPE_LABELS[value] ?? "마음카드";
}

export function adminReplyTypeLabel(value: string | null | undefined): string {
  if (!value) {
    return "응원문장";
  }
  return REPLY_TYPE_LABELS[value] ?? "응원문장";
}

export function adminProviderLabel(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  return PROVIDER_LABELS[value] ?? "기타 제공자";
}

export function adminActionLabel(value: string | null | undefined): string {
  if (!value) {
    return "전체 작업";
  }
  return ACTION_LABELS[value] ?? "기타 작업";
}

export function adminTargetTypeLabel(value: string | null | undefined): string {
  return adminSourceTypeLabel(value);
}

export function adminJobErrorLabel(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  const normalized = value.toLowerCase();
  if (normalized.includes("timeout")) {
    return "처리 시간 초과";
  }
  if (normalized.includes("unsupported")) {
    return "지원하지 않는 원본 유형";
  }
  if (normalized.includes("public") || normalized.includes("excluded")) {
    return "공개 정책 제외";
  }
  return "작업 오류";
}

export function adminErrorMessage(error: unknown, fallback = "요청에 실패했습니다."): string {
  if (error instanceof ApiClientError) {
    return ERROR_CODE_LABELS[error.code] ?? fallback;
  }
  if (error instanceof NetworkError) {
    return error.message;
  }
  return fallback;
}
