import { useEffect, useId, type ReactNode } from "react";

export function Button({
  children,
  tone = "primary",
  type = "button",
  disabled,
  onClick,
}: {
  children: ReactNode;
  tone?: "primary" | "ghost" | "danger" | "forest";
  type?: "button" | "submit";
  disabled?: boolean;
  onClick?: () => void;
}) {
  return (
    <button className={`btn btn-${tone}`} type={type} disabled={disabled} onClick={onClick}>
      {children}
    </button>
  );
}

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint ? <small>{hint}</small> : null}
    </label>
  );
}

export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="modal-backdrop" onMouseDown={onClose} role="presentation">
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header>
          <h2>{title}</h2>
          <button className="icon-btn" type="button" onClick={onClose} aria-label="Fechar">
            ×
          </button>
        </header>
        {children}
      </div>
    </div>
  );
}

export function StatusPill({
  status,
  label,
  overdue = false,
}: {
  status: string;
  label: string;
  overdue?: boolean;
}) {
  const tone = status === "return_requested" && overdue ? "return_requested" : status === "active" && overdue ? "overdue" : status;
  const text = status === "return_requested" && overdue ? `${label} · Atrasado` : status === "active" && overdue ? "Atrasado" : label;
  return <span className={`pill pill-${tone}`}>{text}</span>;
}

export function Pagination({
  page,
  pages,
  onPage,
}: {
  page: number;
  pages: number;
  onPage: (page: number) => void;
}) {
  if (pages <= 1) return null;
  return (
    <div className="pager">
      <button type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        Anterior
      </button>
      <span>
        Página {page} de {pages}
      </span>
      <button type="button" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        Próxima
      </button>
    </div>
  );
}

export function Empty({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      <p>{text}</p>
    </div>
  );
}

export function ScreenLoader() {
  return (
    <div className="screen-loader">
      <span />
      Carregando o acervo
    </div>
  );
}

export function useFormId(prefix: string) {
  const id = useId();
  return `${prefix}-${id}`;
}
