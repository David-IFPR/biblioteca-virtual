import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../../api/http";
import { StatusPill } from "../../components/ui";
import { formatDate } from "../../format";
import type { AdminDashboard } from "../../types";

export function AdminDashboardPage() {
  const [data, setData] = useState<AdminDashboard | null>(null);
  useEffect(() => {
    api.get<AdminDashboard>("/admin/dashboard/").then((response) => setData(response.data));
  }, []);
  if (!data) return <main className="page">Carregando painel...</main>;
  const max = Math.max(...data.chart.map((item) => item.value), 1);
  const cards = [
    ["Livros", data.books, "/admin/livros"],
    ["Exemplares", data.copies, "/admin/livros"],
    ["Disponíveis", data.available_copies, "/admin/livros"],
    ["Emprestados", data.loaned_copies, "/admin/emprestimos"],
    ["Solicitações", data.pending_requests, "/admin/solicitacoes"],
    ["Devoluções", data.returns_waiting, "/admin/emprestimos?status=return_requested"],
    ["Atrasados", data.overdue, "/admin/emprestimos?status=overdue"],
    ["Alunos", data.students, "/admin/alunos"],
  ] as const;

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <p className="kicker">Painel</p>
          <h1>Situação da biblioteca</h1>
        </div>
      </div>
      <section className="stat-grid eight">
        {cards.map(([label, value, to]) => (
          <Link key={label} className="stat" to={to}><b>{value}</b><span>{label}</span></Link>
        ))}
      </section>
      <section className="two section">
        <article className="panel pad">
          <h2 className="section-title">Indicadores</h2>
          <div className="bars">
            {data.chart.map((item) => (
              <div key={item.label} className="bar-row">
                <span>{item.label}</span>
                <div className="bar-track"><div className="bar-fill" style={{ width: `${(item.value / max) * 100}%` }} /></div>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
        </article>
        <article className="panel pad">
          <h2 className="section-title">Aguardando retirada</h2>
          <p className="lede">{data.approved_waiting_pickup} solicitação(ões) aprovada(s) ainda sem registro de retirada.</p>
          <Link className="btn btn-primary" to="/admin/solicitacoes?status=approved">Registrar retiradas</Link>
        </article>
      </section>
      <section className="section">
        <h2 className="section-title">Solicitações pendentes</h2>
        {data.recent_requests.length === 0 ? <p className="muted">Nenhuma solicitação pendente.</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Aluno</th><th>Livro</th><th>Quando</th><th></th></tr></thead>
              <tbody>
                {data.recent_requests.map((item) => (
                  <tr key={item.id}>
                    <td>{item.student_name}<div className="muted mini">{item.enrollment}</div></td>
                    <td>{item.book_title}</td>
                    <td>{formatDate(item.requested_at)}</td>
                    <td><StatusPill status={item.status} label={item.status_label} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <section className="section">
        <h2 className="section-title">Empréstimos atrasados</h2>
        {data.overdue_loans.length === 0 ? <p className="muted">Nenhum atraso no momento.</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Aluno</th><th>Livro</th><th>Prazo</th></tr></thead>
              <tbody>
                {data.overdue_loans.map((loan) => (
                  <tr key={loan.id}>
                    <td>{loan.student_name}</td>
                    <td>{loan.book_title}</td>
                    <td>{formatDate(loan.due_date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
