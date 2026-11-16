import axios from "axios";

const baseURL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

export const api = axios.create({ baseURL });

const ACCESS = "acervo_access";
const REFRESH = "acervo_refresh";

export function readAccess() {
  return localStorage.getItem(ACCESS);
}

export function saveSession(access: string, refresh: string) {
  localStorage.setItem(ACCESS, access);
  localStorage.setItem(REFRESH, refresh);
}

export function clearSession() {
  localStorage.removeItem(ACCESS);
  localStorage.removeItem(REFRESH);
}

api.interceptors.request.use((config) => {
  const token = readAccess();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function renewAccess() {
  const refresh = localStorage.getItem(REFRESH);
  if (!refresh) return null;
  const { data } = await axios.post(`${baseURL}/auth/refresh/`, { refresh });
  saveSession(data.access, data.refresh || refresh);
  return data.access as string;
}

function isAuthCall(url?: string) {
  if (!url) return false;
  return ["/auth/login/", "/auth/admin/login/", "/auth/register/", "/auth/refresh/", "/auth/password-reset/"].some(
    (path) => url.includes(path),
  );
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;
    const detail = String(error.response?.data?.detail || "");
    if (status === 403 && detail.toLowerCase().includes("bloqueada")) {
      clearSession();
      if (!window.location.pathname.startsWith("/entrar")) {
        window.location.href = "/entrar?aviso=bloqueada";
      }
      return Promise.reject(error);
    }
    if (status === 401 && original && !original._retry && !isAuthCall(original.url)) {
      original._retry = true;
      try {
        refreshing ??= renewAccess().finally(() => {
          refreshing = null;
        });
        const access = await refreshing;
        if (!access) throw error;
        original.headers.Authorization = `Bearer ${access}`;
        return api(original);
      } catch {
        clearSession();
        const admin = window.location.pathname.startsWith("/admin");
        const onLogin = window.location.pathname.includes("entrar");
        if (!onLogin) window.location.href = admin ? "/admin/entrar" : "/entrar";
      }
    }
    return Promise.reject(error);
  },
);

export function errorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (error.response?.status === 401) return "Credenciais inválidas.";
  }
  return "Não foi possível concluir a operação.";
}
