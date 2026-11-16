import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../../api/http";
import { BookCover } from "../../components/BookCover";
import { StatusPill } from "../../components/ui";
import { firstName, formatDate } from "../../format";
import type { StudentDashboard } from "../../types";

export function StudentDashboardPage() {
  const [data, setData] = useState<StudentDashboard | null>(null);

  useEffect(() => {
    api.get<StudentDashboard>("/student/dashboard/").then((response) => setData(response.data));
  }, []);

  if (!data) return <main className="page">Carregando...</main>;
  const featuredIds = new Set(data.featured_books.map((book) => book.id));
  const recent = data.recent_books.filter((book) => !featuredIds.has(book.id));

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <p className="kicker">Olá, {firstName(data.student_name)}</p>
          <h1>Seu lugar na biblioteca.</h1>
          <p className="lede">Matrícula {data.enrollment}. Veja o que está disponível e acompanhe suas locações.</p>
        </div>
        <Link className="btn btn-primary" to="/catalogo">Explorar catálogo</Link>
      </div>
      <section className="stats">
        <Link className="stat" to="/catalogo"><b>{data.available_books}</b><span>livros disponíveis</span></Link>
        <Link className="stat" to="/emprestimos"><b>{data.active_loans}</b><span>empréstimos ativos</span></Link>
        <Link className="stat" to="/emprestimos"><b>{data.pending_requests}</b><span>solicitações pendentes</span></Link>
        <Link className="stat" to="/emprestimos"><b>{data.loan_history}</b><span>devoluções no histórico</span></Link>
      </section>
      <section className="section">
        <h2 className="section-title">Novidades e destaques</h2>
        <div className="rail">
          {data.featured_books.map((book) => (
            <Link key={book.id} className="book-card" to={`/catalogo/${book.id}`}>
              <BookCover title={book.title} author={book.author} src={book.cover_url} />
              <div className="meta">
                <h3>{book.title}</h3>
                <span className="muted">{book.author}</span>
                <StatusPill status={book.availability} label={book.available_copies > 0 ? `${book.available_copies} disponíveis` : "Indisponível"} />
              </div>
            </Link>
          ))}
        </div>
      </section>
      {recent.length > 0 ? (
        <section className="section">
          <h2 className="section-title">Adicionados recentemente</h2>
          <div className="book-grid">
            {recent.map((book) => (
              <Link key={book.id} className="book-card" to={`/catalogo/${book.id}`}>
                <BookCover title={book.title} author={book.author} src={book.cover_url} />
                <div className="meta">
                  <h3>{book.title}</h3>
                  <span className="muted">{book.author}</span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      ) : null}
      <section className="section">
        <h2 className="section-title">Movimentação recente</h2>
        {data.recent_loans.length === 0 ? <p className="muted">Você ainda não retirou livros.</p> : (
          <div className="loan-list">
            {data.recent_loans.map((loan) => (
              <article key={loan.id} className="loan-card">
                <BookCover title={loan.book_title} src={loan.cover_url} />
                <div>
                  <strong>{loan.book_title}</strong>
                  <div className="muted">Devolução prevista em {formatDate(loan.due_date)}</div>
                </div>
                <StatusPill status={loan.display_status} label={loan.status_label} overdue={loan.is_overdue} />
              </article>
            ))}
          </div>
        )}
        {data.overdue_loans > 0 ? <p className="alert" style={{ marginTop: 12 }}>{data.overdue_loans} empréstimo(s) em atraso. Procure a biblioteca.</p> : null}
      </section>
    </main>
  );
}
