import { useEffect, useState } from "react";
import { api, errorMessage } from "../../api/http";
import { BookCover } from "../../components/BookCover";
import { useToast } from "../../components/toast";
import { Button, Empty, Modal, StatusPill } from "../../components/ui";
import { formatDate, formatDateTime } from "../../format";
import type { Loan, LoanRequestItem, MyCirculation } from "../../types";

const FILTERS = [
  ["all", "Tudo"],
  ["pending", "Pendentes"],
  ["approved", "Aprovadas"],
  ["active", "Emprestados"],
  ["return_requested", "Aguardando confirmação"],
  ["overdue", "Atrasados"],
  ["returned", "Devolvidos"],
  ["rejected", "Recusadas"],
] as const;

export function MyLoansPage() {
  const toast = useToast();
  const [data, setData] = useState<MyCirculation | null>(null);
  const [filter, setFilter] = useState<(typeof FILTERS)[number][0]>("all");
  const [target, setTarget] = useState<Loan | null>(null);
  const [busy, setBusy] = useState(false);

  function load() {
    api.get<MyCirculation>("/student/circulation/").then((response) => setData(response.data));
  }

  useEffect(() => {
    load();
  }, []);

  async function askReturn() {
    if (!target) return;
    setBusy(true);
    try {
      const { data: payload } = await api.post(`/student/loans/${target.id}/request-return/`);
      toast(payload.detail || "Devolução solicitada.");
      setTarget(null);
      load();
    } catch (error) {
      toast(errorMessage(error), "bad");
    } finally {
      setBusy(false);
    }
  }

  if (!data) return <main className="page">Carregando empréstimos...</main>;

  const requests = data.requests.filter((item) => filter === "all" || item.status === filter);
  const loans = data.loans.filter((item) => {
    if (filter === "all") return true;
    if (filter === "overdue") return item.is_overdue;
    if (filter === "active") return item.status === "active";
    return item.status === filter;
  });
  const showRequests = ["all", "pending", "approved", "rejected"].includes(filter);

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <p className="kicker">Meus empréstimos</p>
          <h1>Do pedido à devolução.</h1>
          <p className="lede">A devolução só é concluída quando a biblioteca confirma o recebimento do livro.</p>
        </div>
      </div>
      <div className="chips">
        {FILTERS.map(([key, label]) => (
          <button key={key} className={filter === key ? "chip on" : "chip"} type="button" onClick={() => setFilter(key)}>
            {label}{data.counts[key] ? ` (${data.counts[key]})` : ""}
          </button>
        ))}
      </div>
      {showRequests ? <RequestList items={requests} /> : null}
      <div className="loan-list" style={{ marginTop: 14 }}>
        {loans.length === 0 && requests.length === 0 ? (
          <Empty title="Nada por aqui" text="Quando você solicitar um livro, o processo aparece nesta página." />
        ) : loans.map((loan) => (
          <article key={loan.id} className="loan-card">
            <BookCover title={loan.book_title} src={loan.cover_url} />
            <div>
              <strong>{loan.book_title}</strong>
              <div className="muted">{loan.book_author} · exemplar {loan.copy_code}</div>
              <div className="muted mini">Retirada {formatDateTime(loan.loaned_at)} · prazo {formatDate(loan.due_date)}</div>
              {loan.returned_at ? <div className="muted mini">Devolvido em {formatDateTime(loan.returned_at)} · confirmado por {loan.confirmed_by_name}</div> : null}
              {loan.status === "return_requested" ? <div className="muted mini">Aguardando a biblioteca confirmar a devolução. O exemplar continua emprestado.</div> : null}
            </div>
            <div className="actions">
              <StatusPill status={loan.status} label={loan.status_label} overdue={loan.is_overdue} />
              {loan.status === "active" ? <Button onClick={() => setTarget(loan)}>Solicitar devolução</Button> : null}
            </div>
          </article>
        ))}
      </div>
      {target ? (
        <Modal title="Solicitar devolução" onClose={() => setTarget(null)}>
          <p className="lede">Você vai informar que está devolvendo «{target.book_title}». O livro só fica disponível de novo depois que um professor ou administrador confirmar o recebimento.</p>
          <div className="actions">
            <Button onClick={askReturn} disabled={busy}>{busy ? "Enviando..." : "Solicitar devolução"}</Button>
            <Button tone="ghost" onClick={() => setTarget(null)}>Cancelar</Button>
          </div>
        </Modal>
      ) : null}
    </main>
  );
}

function RequestList({ items }: { items: LoanRequestItem[] }) {
  if (items.length === 0) return null;
  return (
    <div className="loan-list">
      {items.map((item) => (
        <article key={item.id} className="loan-card">
          <BookCover title={item.book_title} src={item.cover_url} />
          <div>
            <strong>{item.book_title}</strong>
            <div className="muted">Solicitado em {formatDateTime(item.requested_at)}</div>
            {item.rejection_reason ? <div className="muted mini">Motivo: {item.rejection_reason}</div> : null}
            {item.status === "approved" ? <div className="muted mini">Aprovado. Retire o exemplar na biblioteca. A retirada ainda será registrada pela equipe.</div> : null}
          </div>
          <StatusPill status={item.status} label={item.status_label} />
        </article>
      ))}
    </div>
  );
}
