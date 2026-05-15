const FORBIDDEN_DISPLAY_FIELDS = [
  "contentRaw",
  "contentRedacted",
  "mindCardContent",
  "replyContent",
  "sessionId",
  "resumeToken",
  "completionCode",
  "riskFlags",
  "scaleScores",
  "safetyStatus",
  "publicStatus",
  "moderationReason",
  "reviewedBy",
  "admin"
] as const;

export type DisplayContractViolation = {
  path: string;
  key: string;
};

function inspectValue(value: unknown, path: string, violations: DisplayContractViolation[]): void {
  if (Array.isArray(value)) {
    value.forEach((item, index) => inspectValue(item, `${path}[${index}]`, violations));
    return;
  }

  if (!value || typeof value !== "object") {
    return;
  }

  for (const [key, nestedValue] of Object.entries(value as Record<string, unknown>)) {
    const nextPath = path ? `${path}.${key}` : key;
    if ((FORBIDDEN_DISPLAY_FIELDS as readonly string[]).includes(key)) {
      violations.push({ path: nextPath, key });
    }
    inspectValue(nestedValue, nextPath, violations);
  }
}

export function findDisplayContractViolations(payload: unknown): DisplayContractViolation[] {
  const violations: DisplayContractViolation[] = [];
  inspectValue(payload, "", violations);
  return violations;
}

export function warnIfDisplayContractUnsafe(payload: unknown): void {
  if (import.meta.env.PROD) {
    return;
  }

  const violations = findDisplayContractViolations(payload);
  if (violations.length > 0) {
    console.warn("Display payload contains fields that must not appear on TV", violations);
  }
}
