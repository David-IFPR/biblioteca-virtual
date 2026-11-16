import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, errorMessage } from "../../api/http";
import { BookCover } from "../../components/BookCover";
import { useToast } from "../../components/toast";
import { Button } from "../../components/ui";
import type { Book } from "../../types";

export function BookDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [book, setBook] = useState<Book | null>(null);
  const [busy, setBusy] = useState(false);

  function load() {
    api.get<Book>(`/catalog/books/${id}/`).then((response) => setBook(response.data));
  }

  useEffect(() => {
    load();
  }, [id]);

  async function requestLoan() {
    if (!book) return;
    setBusy(true);
    try {
      const { data } = await api.post(`/student/requests/`, { book_id: book.id });
      toast(data.detail || "Solicitação registrada.");
      navigate("/emprestimos");
    } catch (error) {
      toast(errorMessage(error), "bad");
    } finally {
      setBusy(false);
    }
  }

  if (!book) return <main className="page">Carregando livro...</main>;
  const summary = book.copy_summary;

  return (
    <main className="page">
      <Link className="quiet-link" to="/catalogo">Voltar ao catálogo</Link>
      <article className="detail" style={{ marginTop: 18 }}>
        <BookCover large title={book.title} author={book.author} src={book.cover_url} />
        <div>
          <p className="kicker">{book.category_name}</p>
          <h1>{book.title}</h1>
          <p className="lede">{book.author}</p>
          <div className="facts">
            <div><span>Editora</span><strong>{book.publisher}</strong></div>
            <div><span>Ano</span><strong>{book.publication_year}</strong></div>
            <div><span>ISBN</span><strong>{book.isbn || "Não informado"}</strong></div>
            <div><span>Exemplares</span><strong>{summary.total}</strong></div>
            <div><span>Disponíveis</span><strong>{summary.available}</strong></div>
            <div><span>Emprestados</span><strong>{summary.loaned}</strong></div>
            <div><span>Reservados</span><strong>{summary.reserved}</strong></div>
            <div><span>Situação</span><strong>{summary.available > 0 ? "Disponível para solicitação" : "Indisponível"}</strong></div>
          </div>
          <p className="prose">{book.description}</p>
          <div style={{ marginTop: 22 }}>
            {book.can_request ? (
              <Button onClick={requestLoan} disabled={busy}>{busy ? "Enviando..." : "Solicitar empréstimo"}</Button>
            ) : (
              <div className="alert">{book.request_block_reason || "Este livro não está disponível para solicitação."}</div>
            )}
          </div>
        </div>
      </article>
    </main>
  );
}
