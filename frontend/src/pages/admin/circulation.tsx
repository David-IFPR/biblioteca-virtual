import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, errorMessage } from "../../api/http";
import { useToast } from "../../components/toast";
import { Button, Empty, Field, Modal, Pagination, StatusPill } from "../../components/ui";
import { formatDate, formatDateTime, pagesOf } from "../../format";
import type { Book, Loan, LoanRequestItem, Movement, Page, Policy, StudentRow } from "../../types";

export function RequestsPage() {
  const [params, setParams] = useSearchParams();
  const status = params.get("status") || "pending";
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<Page<LoanRequestItem> | null>(null);
  const [rejecting, setRejecting] = useState<LoanRequestItem | null>(null);
  const [reason, setReason] = useState("");
  const [registering, setRegistering] = useState<LoanRequestItem | null>(null);
  const [due, setDue] = useState("");
  const toast = useToast();

  function load() {
    api.get<Page<LoanRequestItem>>("/admin/requests/", { params: { status, q: query, page, page_size: 10 } })
      .then((response) => setResult(response.data));
  }
  useEffect(() => { load(); }, [status, query, page]);

  async function approve(item: LoanRequestItem) {
    try {
      const { data } = await api.post(`/admin/requests/${item.id}/approve/`);
      toast(data.detail || "Solicitação aprovada.");
      load();
    } catch (error) {
      toast(errorMessage(error), "bad");
    }
  }

  async function reject() {
    if (!rejecting) return;
    try {
      const { data } = await api.post(`/admin/requests/${rejecting.id}/reject/`, { reason });
      toast(data.detail || "Solicitação recusada.");
      setRejecting(null);
      setReason("");
      load();
    } catch (error) {
      toast(errorMessage(error), "bad");
    }
  }

  async function registerLoan() {
    if (!registering) return;
    try {
      const { data } = await api.post(`/admin/requests/${registering.id}/register-loan/`, { due_date: due || undefined });
      toast(data.detail || "Retirada registrada.");
      setRegistering(null);
      load();
    } catch (error) {
      toast(errorMessage(error), "bad");
    }
  }

  return (
    <main className="page">
      <div className="page-head"><div><p className="kicker">Circulação</p><h1>Solicitações</h1></div></div>
      <div className="chips">
        {[["pending", "Pendentes"], ["approved", "Aprovadas"], ["rejected", "Recusadas"], ["fulfilled", "Retiradas"]].map(([key, label]) => (
          <button key={key} className={status === key ? "chip on" : "chip"} type="button" onClick={() => { setParams({ status: key }); setPage(1); }}>{label}</button>
        ))}
      </div>
      <div className="search-line"><input placeholder="Aluno ou livro" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} /></div>
      {!result || result.results.length === 0 ? <Empty title="Nenhuma solicitação" text="Os pedidos dos alunos aparecem nesta fila." /> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Aluno</th><th>Livro</th><th>Data</th><th>Disponíveis</th><th>Situação</th><th></th></tr></thead>
            <tbody>
              {result.results.map((item) => (
                <tr key={item.id}>
                  <td>{item.student_name}<div className="muted mini">{item.enrollment}</div></td>
                  <td>{item.book_title}{item.copy_code ? <div className="muted mini">{item.copy_code}</div> : null}</td>
                  <td>{formatDateTime(item.requested_at)}</td>
                  <td>{item.available_copies}</td>
                  <td><StatusPill status={item.status} label={item.status_label} /></td>
                  <td className="actions">
                    {item.status === "pending" ? <Button onClick={() => approve(item)}>Aprovar</Button> : null}
                    {item.status === "pending" ? <Button tone="danger" onClick={() => setRejecting(item)}>Recusar</Button> : null}
                    {item.status === "approved" ? <Button tone="forest" onClick={() => setRegistering(item)}>Registrar retirada</Button> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pagination page={page} pages={pagesOf(result?.count || 0, 10)} onPage={setPage} />
      {rejecting ? (
        <Modal title="Recusar solicitação" onClose={() => setRejecting(null)}>
          <div className="stack">
            <p>Recusar «{rejecting.book_title}» para {rejecting.student_name}.</p>
            <Field label="Motivo"><textarea value={reason} onChange={(event) => setReason(event.target.value)} /></Field>
            <Button tone="danger" onClick={reject}>Recusar</Button>
          </div>
        </Modal>
      ) : null}
      {registering ? (
        <Modal title="Registrar retirada" onClose={() => setRegistering(null)}>
          <div className="stack">
            <p>Confirme que {registering.student_name} retirou «{registering.book_title}». O exemplar passa a ficar emprestado.</p>
            <Field label="Devolução prevista" hint="Em branco, usa o prazo padrão da biblioteca.">
              <input type="date" value={due} onChange={(event) => setDue(event.target.value)} />
            </Field>
            <Button tone="forest" onClick={registerLoan}>Registrar empréstimo</Button>
          </div>
        </Modal>
      ) : null}
    </main>
  );
}

export function LoansPage() {
  const [params] = useSearchParams();
  const [status, setStatus] = useState(params.get("status") || "open");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<Page<Loan> | null>(null);
  const [returning, setReturning] = useState<Loan | null>(null);
  const [editing, setEditing] = useState<Loan | null>(null);
  const [due, setDue] = useState("");
  const [reason, setReason] = useState("");
  const [direct, setDirect] = useState(false);
  const toast = useToast();

  function load() {
    api.get<Page<Loan>>("/admin/loans/", { params: { status, q: query, page, page_size: 10 } })
      .then((response) => setResult(response.data));
  }
  useEffect(() => { load(); }, [status, query, page]);

  async function confirm() {
    if (!returning) return;
    try {
      const { data } = await api.post(`/admin/loans/${returning.id}/confirm-return/`);
      toast(data.detail || "Devolução confirmada.");
      setReturning(null);
      load();
    } catch (error) {
      toast(errorMessage(error), "bad");
    }
  }

  async function changeDue(event: FormEvent) {
    event.preventDefault();
    if (!editing) return;
    try {
      await api.patch(`/admin/loans/${editing.id}/due-date/`, { due_date: due, reason });
      toast("Prazo alterado e registrado.");
      setEditing(null);
      load();
    } catch (error) {
      toast(errorMessage(error), "bad");
    }
  }

  return (
    <main className="page">
      <div className="page-head">
        <div><p className="kicker">Circulação</p><h1>Empréstimos</h1></div>
        <Button onClick={() => setDirect(true)}>Registrar empréstimo direto</Button>
      </div>
      <div className="chips">
        {[["open", "Em aberto"], ["return_requested", "Aguardando confirmação"], ["overdue", "Atrasados"], ["active", "Emprestados"], ["returned", "Devolvidos"]].map(([key, label]) => (
          <button key={key} type="button" className={status === key ? "chip on" : "chip"} onClick={() => { setStatus(key); setPage(1); }}>{label}</button>
        ))}
      </div>
      <div className="search-line"><input placeholder="Aluno, livro ou exemplar" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} /></div>
      {!result || result.results.length === 0 ? <Empty title="Nenhum empréstimo" text="Os registros de retirada aparecem aqui." /> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Aluno</th><th>Livro</th><th>Retirada</th><th>Prazo</th><th>Situação</th><th></th></tr></thead>
            <tbody>
              {result.results.map((loan) => (
                <tr key={loan.id}>
                  <td>{loan.student_name}<div className="muted mini">{loan.enrollment}</div></td>
                  <td>{loan.book_title}<div className="muted mini">{loan.copy_code}</div></td>
                  <td>{formatDateTime(loan.loaned_at)}</td>
                  <td>{formatDate(loan.due_date)}</td>
                  <td><StatusPill status={loan.status} label={loan.status_label} overdue={loan.is_overdue} /></td>
                  <td className="actions">
                    {loan.status !== "returned" ? <Button tone="forest" onClick={() => setReturning(loan)}>Confirmar devolução</Button> : null}
                    {loan.status !== "returned" ? <Button tone="ghost" onClick={() => { setEditing(loan); setDue(loan.due_date); }}>Alterar prazo</Button> : <span className="muted mini">Confirmado por {loan.confirmed_by_name}</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pagination page={page} pages={pagesOf(result?.count || 0, 10)} onPage={setPage} />
      {returning ? (
        <Modal title="Confirmar devolução" onClose={() => setReturning(null)}>
          <p className="lede">Confirme que «{returning.book_title}» foi recebido de {returning.student_name}. Só então o exemplar volta a ficar disponível.</p>
          <div className="actions">
            <Button tone="forest" onClick={confirm}>Confirmar recebimento</Button>
            <Button tone="ghost" onClick={() => setReturning(null)}>Cancelar</Button>
          </div>
        </Modal>
      ) : null}
      {editing ? (
        <Modal title="Alterar prazo" onClose={() => setEditing(null)}>
          <form className="stack" onSubmit={changeDue}>
            <Field label="Nova data"><input type="date" value={due} onChange={(event) => setDue(event.target.value)} required /></Field>
            <Field label="Motivo"><textarea value={reason} onChange={(event) => setReason(event.target.value)} required /></Field>
            {editing.due_date_changes.length > 0 ? (
              <div className="muted mini">{editing.due_date_changes.length} alteração(ões) já registrada(s).</div>
            ) : null}
            <Button type="submit">Salvar prazo</Button>
          </form>
        </Modal>
      ) : null}
      {direct ? <DirectLoan onClose={() => { setDirect(false); load(); }} /> : null}
    </main>
  );
}

function DirectLoan({ onClose }: { onClose: () => void }) {
  const toast = useToast();
  const [studentQuery, setStudentQuery] = useState("");
  const [bookQuery, setBookQuery] = useState("");
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [books, setBooks] = useState<Book[]>([]);
  const [studentId, setStudentId] = useState("");
  const [bookId, setBookId] = useState("");
  const [due, setDue] = useState("");

  useEffect(() => {
    if (studentQuery.trim().length < 2) return;
    api.get<Page<StudentRow>>("/admin/students/", { params: { q: studentQuery, page_size: 6 } })
      .then((response) => setStudents(response.data.results));
  }, [studentQuery]);
  useEffect(() => {
    if (bookQuery.trim().length < 2) return;
    api.get<Page<Book>>("/catalog/books/", { params: { q: bookQuery, available: "true", page_size: 6 } })
      .then((response) => setBooks(response.data.results));
  }, [bookQuery]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      const { data } = await api.post("/admin/loans/", { student_id: studentId, book_id: bookId, due_date: due || undefined });
      toast(data.detail || "Empréstimo registrado.");
      onClose();
    } catch (error) {
      toast(errorMessage(error), "bad");
    }
  }

  return (
    <Modal title="Empréstimo direto" onClose={onClose}>
      <form className="stack" onSubmit={submit}>
        <Field label="Buscar aluno">
          <input value={studentQuery} onChange={(event) => setStudentQuery(event.target.value)} placeholder="Nome ou matrícula" />
        </Field>
        <select value={studentId} onChange={(event) => setStudentId(event.target.value)} required>
          <option value="">Selecione o aluno</option>
          {students.map((student) => <option key={student.id} value={student.id}>{student.full_name} · {student.enrollment}</option>)}
        </select>
        <Field label="Buscar livro">
          <input value={bookQuery} onChange={(event) => setBookQuery(event.target.value)} placeholder="Título" />
        </Field>
        <select value={bookId} onChange={(event) => setBookId(event.target.value)} required>
          <option value="">Selecione o livro</option>
          {books.map((book) => <option key={book.id} value={book.id}>{book.title} · {book.available_copies} disponíveis</option>)}
        </select>
        <Field label="Devolução prevista"><input type="date" value={due} onChange={(event) => setDue(event.target.value)} /></Field>
        <Button type="submit">Registrar</Button>
      </form>
    </Modal>
  );
}

export function MovementsPage() {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<Page<Movement> | null>(null);
  useEffect(() => {
    api.get<Page<Movement>>("/admin/movements/", { params: { q: query, page, page_size: 12 } })
      .then((response) => setResult(response.data));
  }, [query, page]);
  return (
    <main className="page">
      <div className="page-head"><div><p className="kicker">Auditoria</p><h1>Histórico</h1></div></div>
      <div className="search-line"><input placeholder="Buscar movimentação" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} /></div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Quando</th><th>Ação</th><th>Descrição</th><th>Responsável</th></tr></thead>
          <tbody>
            {(result?.results || []).map((item) => (
              <tr key={item.id}>
                <td>{formatDateTime(item.created_at)}</td>
                <td>{item.action_label}</td>
                <td>{item.description}</td>
                <td>{item.actor_name}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination page={page} pages={pagesOf(result?.count || 0, 12)} onPage={setPage} />
    </main>
  );
}

export function SettingsPage() {
  const toast = useToast();
  const [policy, setPolicy] = useState<Policy | null>(null);
  useEffect(() => {
    api.get<Policy>("/admin/settings/").then((response) => setPolicy(response.data));
  }, []);
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!policy) return;
    try {
      const { data } = await api.patch<Policy>("/admin/settings/", policy);
      setPolicy(data);
      toast("Regras atualizadas.");
    } catch (error) {
      toast(errorMessage(error), "bad");
    }
  }
  if (!policy) return <main className="page">Carregando regras...</main>;
  return (
    <main className="page">
      <form className="panel pad stack" onSubmit={save} style={{ maxWidth: 560 }}>
        <div><p className="kicker">Regras</p><h1 className="section-title">Limites da biblioteca</h1></div>
        <Field label="Empréstimos simultâneos por aluno">
          <input type="number" min={1} max={20} value={policy.max_active_loans} onChange={(event) => setPolicy({ ...policy, max_active_loans: Number(event.target.value) })} />
        </Field>
        <Field label="Prazo padrão (dias)">
          <input type="number" min={1} max={180} value={policy.loan_days} onChange={(event) => setPolicy({ ...policy, loan_days: Number(event.target.value) })} />
        </Field>
        <Field label="Avisar quantos dias antes do prazo">
          <input type="number" min={1} value={policy.reminder_days} onChange={(event) => setPolicy({ ...policy, reminder_days: Number(event.target.value) })} />
        </Field>
        <Button type="submit">Salvar regras</Button>
      </form>
    </main>
  );
}
