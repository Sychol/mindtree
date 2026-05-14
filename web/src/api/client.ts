import type { ApiErrorBody, ApiRequestOptions } from "../types/api";

const DEFAULT_TIMEOUT_MS = 12000;

export class ApiClientError extends Error {
  code: string;
  status: number;
  details?: Record<string, unknown>;

  constructor(message: string, code: string, status: number, details?: Record<string, unknown>) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export class NetworkError extends Error {
  constructor(message = "네트워크 연결이 원활하지 않습니다.") {
    super(message);
    this.name = "NetworkError";
  }
}

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000/api";

function joinPath(path: string): string {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

function composeSignals(signal: AbortSignal | undefined, timeoutMs: number): AbortSignal {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  const abort = () => {
    window.clearTimeout(timeoutId);
    controller.abort();
  };

  if (signal) {
    if (signal.aborted) {
      abort();
    } else {
      signal.addEventListener("abort", abort, { once: true });
    }
  }

  return controller.signal;
}

export async function requestJson<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const headers = new Headers();
  headers.set("Accept", "application/json");

  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (options.idempotencyKey) {
    headers.set("Idempotency-Key", options.idempotencyKey);
  }

  let response: Response;
  try {
    response = await fetch(joinPath(path), {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: composeSignals(options.signal, options.timeoutMs ?? DEFAULT_TIMEOUT_MS)
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new NetworkError("요청 시간이 초과되었습니다.");
    }
    throw new NetworkError();
  }

  const text = await response.text();
  const parsed = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const errorBody = parsed as ApiErrorBody | null;
    if (errorBody?.error) {
      throw new ApiClientError(
        errorBody.error.message,
        errorBody.error.code,
        response.status,
        errorBody.error.details
      );
    }
    throw new ApiClientError("요청을 처리하지 못했습니다.", "INTERNAL_ERROR", response.status);
  }

  return parsed as T;
}
