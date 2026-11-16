import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, errorMessage } from "../../api/http";
import { useToast } from "../../components/toast";
import { Button, Empty, Field, Modal, Pagination, StatusPill } from "../../components/ui";
import { formatDate, formatDateTime, pagesOf } from "../../format";
import type { Page, StudentRow } from "../../types";

export function StudentsPage() {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<Page<StudentRow> | null>(null);

  useEffect(() => {
    api.get<Page<StudentRow>>("/admin/students/", { params: { q: query, status, page, page_size: 10 } })
      .then((response) => setResult(response.data));
  }, [query, status, page]);

  return (
    <main className="page">
      <div className="page-head"><div><p className="kicker">Pessoas</p><h1>Alunos</h1></div></div>
      <div className="search-line">
        <input placeholder="Nome, matrícula ou e-mail" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} />
        <select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}>
          <option value="">Todas as contas</option>
          <option value="active">Ativas</option>
          <option value="blocked">Bloqueadas</option>
        </select>
      </div>
      {!result || result.results.length === 0 ? <Empty title="Nenhum aluno" text="Os cadastros feitos pelos estudantes aparecem aqui." /> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Nome</th><th>Matrícula</th><th>E-mail</th><th>Cadastro</th><th>Empréstimos</th><th>Conta</th><th></th></tr></thead>
            <tbody>
              {result.results.map((student) => (
                <tr key={student.id}>
                  <td>{student.full_name}</td>
                  <td>{student.enrollment}</td>
                  <td>{student.email}</td>
                  <td>{formatDate(student.created_at)}</td>
                  <td>{student.active_loan_count} ativos · {student.loan_count} no total</td>
                  <td><StatusPill status={student.account_status === "blocked" ? "blocked" : "active"} label={student.account_status_label} /></td>
                  <td><Link className="btn btn-ghost" to={`/admin/alunos/${student.id}`}>Detalhes</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pagination page={page} pages={pagesOf(result?.count || 0, 10)} onPage={setPage} />
    </main>
  );
}

export function StudentDetailPage() {
  const { id } = useParams();
  const toast = useToast();
  const [student, setStudent] = useState<StudentRow | null>(null);
  const [editing, setEditing] = useState(false);
  const [blocking, setBlocking] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [reason, setReason] = useState("");

  function load() {
    api.get<StudentRow>(`/admin/students/${id}/`).then((response) => {
      setStudent(response.data);
      setName(response.data.full_name);
      setEmail(response.data.email);
    });
  }
  useEffect(() => { load(); }, [id]);

  async function save(event: FormEvent) {
    event.preventDefault();
    try {
      await api.patch(`/admin/students/${id}/`, { full_name: name, email });
      toast("Dados atualizados. A matrícula não foi alterada.");
      setEditing(false);
      load();
    } catch (error) {
      toast(errorMessage(error), "bad");
    }
  }

  async function block() {
    try {
      await api.post(`/admin/students/${id}/block/`, { reason });
      toast("Conta bloqueada.");
      setBlocking(false);
      load();
    } catch (error) {
      toast(errorMessage(error), "bad");
    }
  }

  async function unblock() {
    try {
      await api.post(`/admin/students/${id}/unblock/`);
      toast("Conta desbloqueada.");
      load();
    } catch (error) {
      toast(errorMessage(error), "bad");
    }
  }

  if (!student) return <main className="page">Carregando aluno...</main>;

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <p className="kicker">{student.enrollment}</p>
          <h1>{student.full_name}</h1>
          <p className="lede">{student.email} · cadastro em {formatDate(student.created_at)}</p>
        </div>
        <div className="actions">
          <Button tone="ghost" onClick={() => setEditing(true)}>Editar dados</Button>
          {student.is_blocked ? <Button tone="forest" onClick={unblock}>Desbloquear</Button> : <Button tone="danger" onClick={() => setBlocking(true)}>Bloquear</Button>}
        </div>
      </div>
      {student.blocked_reason ? <div className="alert">Conta bloqueada: {student.blocked_reason}</div> : null}
      <p className="muted" style={{ margin: "12px 0" }}>A senha do aluno não é exibida. A matrícula não pode ser alterada por esta tela.</p>
      <h2 className="section-title">Histórico</h2>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Livro</th><th>Situação</th><th>Prazo</th><th>Devolução</th></tr></thead>
          <tbody>
            {(student.loans || []).map((loan) => (
              <tr key={loan.id}>
                <td>{loan.book_title}<div className="muted mini">{loan.copy_code}</div></td>
                <td><StatusPill status={loan.status} label={loan.status_label} overdue={loan.is_overdue} /></td>
                <td>{formatDate(loan.due_date)}</td>
                <td>{loan.returned_at ? `${formatDateTime(loan.returned_at)} · ${loan.confirmed_by_name}` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {editing ? (
        <Modal title="Editar aluno" onClose={() => setEditing(false)}>
          <form className="stack" onSubmit={save}>
            <Field label="Nome completo"><input value={name} onChange={(event) => setName(event.target.value)} /></Field>
            <Field label="E-mail"><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></Field>
            <Field label="Matrícula"><input value={student.enrollment} disabled /></Field>
            <Button type="submit">Salvar</Button>
          </form>
        </Modal>
      ) : null}
      {blocking ? (
        <Modal title="Bloquear conta" onClose={() => setBlocking(false)}>
          <div className="stack">
            <Field label="Motivo"><textarea value={reason} onChange={(event) => setReason(event.target.value)} /></Field>
            <Button tone="danger" onClick={block}>Bloquear conta</Button>
          </div>
        </Modal>
      ) : null}
    </main>
  );
}
