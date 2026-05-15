import { requestJson } from "./client";
import type { CompletionCodeResponse } from "../types/completion";

export function getCompletionCode(sessionId: string): Promise<CompletionCodeResponse> {
  return requestJson<CompletionCodeResponse>(
    `/sessions/${encodeURIComponent(sessionId)}/completion-code`
  );
}
