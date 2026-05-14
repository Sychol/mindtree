export function createIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `retry-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
