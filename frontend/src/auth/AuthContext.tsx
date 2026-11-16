import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, clearSession, readAccess, saveSession } from "../api/http";
import type { AuthUser } from "../types";

interface RegisterInput {
  full_name: string;
  enrollment: string;
  email: string;
  password: string;
  password_confirm: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  loginStudent: (enrollment: string, password: string) => Promise<AuthUser>;
  loginAdmin: (email: string, password: string) => Promise<AuthUser>;
  register: (input: RegisterInput) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!readAccess()) {
      setLoading(false);
      return;
    }
    api
      .get<AuthUser>("/auth/me/")
      .then((response) => setUser(response.data))
      .catch(() => {
        clearSession();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      async loginStudent(enrollment, password) {
        const { data } = await api.post("/auth/login/", { enrollment, password });
        saveSession(data.access, data.refresh);
        setUser(data.user);
        return data.user;
      },
      async loginAdmin(email, password) {
        const { data } = await api.post("/auth/admin/login/", { email, password });
        saveSession(data.access, data.refresh);
        setUser(data.user);
        return data.user;
      },
      async register(input) {
        const { data } = await api.post("/auth/register/", input);
        saveSession(data.access, data.refresh);
        setUser(data.user);
        return data.user;
      },
      async logout() {
        const refresh = localStorage.getItem("acervo_refresh");
        try {
          if (refresh) await api.post("/auth/logout/", { refresh });
        } catch {
          /* a sessão local é encerrada mesmo se o token já expirou */
        }
        clearSession();
        setUser(null);
      },
      async refreshUser() {
        const { data } = await api.get<AuthUser>("/auth/me/");
        setUser(data);
      },
    }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth fora do provedor");
  return context;
}
