import type { AdminPayload } from "../types/admin";

const ADMIN_TOKEN_STORAGE_KEY = "maeumnamu.admin.accessToken";
const ADMIN_PAYLOAD_STORAGE_KEY = "maeumnamu.admin.payload";

export function getStoredAdminToken(): string | null {
  return window.sessionStorage.getItem(ADMIN_TOKEN_STORAGE_KEY);
}

export function getStoredAdmin(): AdminPayload | null {
  const rawValue = window.sessionStorage.getItem(ADMIN_PAYLOAD_STORAGE_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    return JSON.parse(rawValue) as AdminPayload;
  } catch {
    return null;
  }
}

export function storeAdminAuth(accessToken: string, admin: AdminPayload): void {
  window.sessionStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, accessToken);
  window.sessionStorage.setItem(ADMIN_PAYLOAD_STORAGE_KEY, JSON.stringify(admin));
}

export function clearAdminAuth(): void {
  window.sessionStorage.removeItem(ADMIN_TOKEN_STORAGE_KEY);
  window.sessionStorage.removeItem(ADMIN_PAYLOAD_STORAGE_KEY);
}
