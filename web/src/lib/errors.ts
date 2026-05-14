import { ApiClientError, NetworkError } from "../api/client";

export function toUserMessage(error: unknown): string {
  if (error instanceof NetworkError) {
    return error.message;
  }
  if (error instanceof ApiClientError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "처리 중 문제가 발생했습니다.";
}
