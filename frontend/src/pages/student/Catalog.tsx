import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/http";
import { BookCover } from "../../components/BookCover";
import { Empty, Pagination, StatusPill } from "../../components/ui";
import { pagesOf } from "../../format";
import type { Book, Category, Page } from "../../types";

const PAGE_SIZE = 12;

export function CatalogPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [isbn, setIsbn] = useState("");
  const [category, setCategory] = useState("");
  const [available, setAvailable] = useState("");
  const [ordering, setOrdering] = useState("title");
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<Page<Book> | null>(null);

  useEffect(() => {
    api.get<Category[]>("/catalog/categories/").then((response) => setCategories(response.data));
  }, []);

  useEffect(() => {
    const params = { title, author, isbn, category, available, ordering, page, page_size: PAGE_SIZE };
    api.get<Page<Book>>("/catalog/books/", { params }).then((response) => setResult(response.data));
  }, [title, author, isbn, category, available, ordering, page]);

  function search(event: FormEvent) {
    event.preventDefault();
  }

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <p className="kicker">Catálogo</p>
          <h1>O que está na estante.</h1>
        </div>
      </div>
      <form className="filters" onSubmit={search}>
        <input name="title" placeholder="Título" value={title} onChange={(event) => { setTitle(event.target.value); setPage(1); }} />
        <input name="author" placeholder="Autor" value={author} onChange={(event) => { setAuthor(event.target.value); setPage(1); }} />
        <input name="isbn" placeholder="ISBN" value={isbn} onChange={(event) => { setIsbn(event.target.value); setPage(1); }} />
        <select value={category} onChange={(event) => { setCategory(event.target.value); setPage(1); }}>
          <option value="">Todas as categorias</option>
          {categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        <select value={available} onChange={(event) => { setAvailable(event.target.value); setPage(1); }}>
          <option value="">Qualquer situação</option>
          <option value="true">Disponíveis</option>
          <option value="false">Indisponíveis</option>
        </select>
        <button className="btn btn-forest" type="submit">Buscar</button>
      </form>
      <div className="search-line">
        <select value={ordering} onChange={(event) => { setOrdering(event.target.value); setPage(1); }}>
          <option value="title">Título A–Z</option>
          <option value="-title">Título Z–A</option>
          <option value="author">Autor</option>
          <option value="year">Ano</option>
          <option value="recent">Mais recentes</option>
        </select>
        <button className="btn btn-ghost" type="button" onClick={() => { setTitle(""); setAuthor(""); setIsbn(""); setCategory(""); setAvailable(""); setOrdering("title"); setPage(1); }}>Limpar</button>
      </div>
      {!result ? <p>Carregando catálogo...</p> : result.results.length === 0 ? (
        <Empty title="Nenhum livro encontrado" text="Ajuste a pesquisa ou os filtros." />
      ) : (
        <div className="book-grid">
          {result.results.map((book) => (
            <Link key={book.id} to={`/catalogo/${book.id}`} className="book-card">
              <BookCover title={book.title} author={book.author} src={book.cover_url} />
              <div className="meta">
                <h3>{book.title}</h3>
                <span className="muted">{book.author}</span>
                <span className="muted mini">{book.category_name} · {book.publication_year}</span>
                <StatusPill
                  status={book.availability}
                  label={book.available_copies > 0 ? `${book.available_copies} de ${book.total_copies} disponíveis` : "Indisponível"}
                />
              </div>
            </Link>
          ))}
        </div>
      )}
      <Pagination page={page} pages={pagesOf(result?.count || 0, PAGE_SIZE)} onPage={setPage} />
    </main>
  );
}
