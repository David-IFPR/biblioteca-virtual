import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

interface Toast {
  id: number;
  message: string;
  tone: "ok" | "bad";
}

const ToastContext = createContext<(message: string, tone?: "ok" | "bad") => void>(() => undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useMemo(
    () => (message: string, tone: "ok" | "bad" = "ok") => {
      const id = Date.now() + Math.random();
      setToasts((current) => [...current, { id, message, tone }]);
      window.setTimeout(() => {
        setToasts((current) => current.filter((item) => item.id !== id));
      }, 3800);
    },
    [],
  );
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toast-wrap">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast ${toast.tone}`}>
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
