export function formatDate(value?: string | null) {
  if (!value) return "—";
  const date = value.length <= 10 ? new Date(`${value}T12:00:00`) : new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("pt-BR");
}

export function formatDateTime(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export function firstName(fullName: string) {
  return fullName.trim().split(/\s+/)[0] || fullName;
}

export function pagesOf(count: number, pageSize: number) {
  return Math.max(1, Math.ceil(count / pageSize));
}
