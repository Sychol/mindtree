import { useCallback, useState } from "react";

import { adminLogin, getAdminMe } from "../api/admin";
import {
  clearAdminAuth,
  getStoredAdmin,
  getStoredAdminToken,
  storeAdminAuth,
} from "../state/adminAuth";
import type { AdminPayload } from "../types/admin";

export function useAdminAuth() {
  const [accessToken, setAccessToken] = useState<string | null>(() => getStoredAdminToken());
  const [admin, setAdmin] = useState<AdminPayload | null>(() => getStoredAdmin());

  const login = useCallback(async (email: string, password: string) => {
    const response = await adminLogin(email, password);
    storeAdminAuth(response.accessToken, response.admin);
    setAccessToken(response.accessToken);
    setAdmin(response.admin);
    return response.admin;
  }, []);

  const logout = useCallback(() => {
    clearAdminAuth();
    setAccessToken(null);
    setAdmin(null);
  }, []);

  const restore = useCallback(async () => {
    const token = getStoredAdminToken();
    if (!token) {
      logout();
      return null;
    }

    try {
      const response = await getAdminMe(token);
      storeAdminAuth(token, response.admin);
      setAccessToken(token);
      setAdmin(response.admin);
      return response.admin;
    } catch {
      logout();
      return null;
    }
  }, [logout]);

  return {
    accessToken,
    admin,
    login,
    logout,
    restore,
    isAuthenticated: Boolean(accessToken),
  };
}
