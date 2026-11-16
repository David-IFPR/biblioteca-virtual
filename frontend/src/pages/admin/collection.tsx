import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, errorMessage } from "../../api/http";
import { useToast } from "../../components/toast";
import { Button, Empty, Field, Modal, Pagination, StatusPill } from "../../components/ui";
import { pagesOf } from "../../format";
import type { Book, Category, Page } from "../../types";

export function BooksPage() {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<Page<Book> | null>(null);
  const [target, setTarget] = useState<Book | null>(null);
  const toast = useToast();

  function load() {
    api.get<Page<Book>>("/catalog/books/", { params: { q: query, page, page_size: 10, ordering: "title" } })
      .then((response) => setResult(response.data));
  }
  useEffect(() => { load(); }, [query, page]);

  async function remove() {
    if (!target) return;
    try {
      await api.delete(`/catalog/books/${target.id}/`);
      toast("Livro excluído.");
      setTarget(null);
      load();
    } catch (error) {
      toast(errorMessage(error), "bad");
    }
  }

  return (
    <main className="page">
      <div className="page-head">
        <div><p className="kicker">Acervo</p><h1>Livros</h1></div>
        <Link className="btn btn-primary" to="/admin/livros/novo">Cadastrar livro</Link>
      </div>
      <div className="search-line">
        <input placeholder="Título, autor ou ISBN" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} />
      </div>
      {!result || result.results.length === 0 ? <Empty title="Nenhum livro" text="Cadastre o primeiro título do acervo." /> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Título</th><th>Autor</th><th>Categoria</th><th>Exemplares</th><th>Situação</th><th></th></tr></thead>
            <tbody>
              {result.results.map((book) => (
                <tr key={book.id}>
                  <td>{book.title}<div className="muted mini">{book.isbn || "Sem ISBN"}</div></td>
                  <td>{book.author}</td>
                  <td>{book.category_name}</td>
                  <td>{book.available_copies}/{book.total_copies}</td>
                  <td><StatusPill status={book.availability} label={book.availability === "available" ? "Disponível" : "Indisponível"} /></td>
                  <td className="actions">
                    <Link className="btn btn-ghost" to={`/admin/livros/${book.id}`}>Editar</Link>
                    <Button tone="danger" onClick={() => setTarget(book)}>Excluir</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pagination page={page} pages={pagesOf(result?.count || 0, 10)} onPage={setPage} />
      {target ? (
        <Modal title="Excluir livro" onClose={() => setTarget(null)}>
          <p className="lede">Excluir «{target.title}»? Livros com empréstimos ou histórico vinculado não podem ser apagados.</p>
          <div className="actions">
            <Button tone="danger" onClick={remove}>Excluir</Button>
            <Button tone="ghost" onClick={() => setTarget(null)}>Cancelar</Button>
          </div>
        </Modal>
      ) : null}
    </main>
  );
}

export function BookFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const editing = Boolean(id);
  const [categories, setCategories] = useState<Category[]>([]);
  const [book, setBook] = useState<Book | null>(null);
  const [form, setForm] = useState({
    title: "", author: "", publisher: "", isbn: "", publication_year: String(new Date().getFullYear()),
    category: "", description: "", shelf_location: "", quantity: "1",
  });
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<Category[]>("/catalog/categories/").then((response) => setCategories(response.data));
    if (!id) return;
    api.get<Book>(`/catalog/books/${id}/`).then((response) => {
      const current = response.data;
      setBook(current);
      setForm({
        title: current.title,
        author: current.author,
        publisher: current.publisher,
        isbn: current.isbn || "",
        publication_year: String(current.publication_year),
        category: String(current.category),
        description: current.description,
        shelf_location: current.shelf_location,
        quantity: String(current.total_copies),
      });
    });
  }, [id]);

  function set<K extends keyof typeof form>(key: K, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    const body = new FormData();
    Object.entries(form).forEach(([key, value]) => body.append(key, value));
    if (file) body.append("cover", file);
    try {
      if (editing) await api.patch(`/catalog/books/${id}/`, body);
      else await api.post("/catalog/books/", body);
      toast(editing ? "Livro atualizado." : "Livro cadastrado.");
      navigate("/admin/livros");
    } catch (error) {
      toast(errorMessage(error), "bad");
    } finally {
      setBusy(false);
    }
  }

  async function toggleCopy(copyId: number, status: string) {
    try {
      await api.post(`/catalog/copies/${copyId}/status/`, { status: status === "available" ? "unavailable" : "available" });
      const { data } = await api.get<Book>(`/catalog/books/${id}/`);
      setBook(data);
      toast("Disponibilidade do exemplar atualizada.");
    } catch (error) {
      toast(errorMessage(error), "bad");
    }
  }

  return (
    <main className="page">
      <form className="panel pad stack" onSubmit={submit}>
        <div>
          <p className="kicker">{editing ? "Edição" : "Novo livro"}</p>
          <h1 className="section-title">{editing ? form.title || "Editar livro" : "Cadastrar livro"}</h1>
        </div>
        <div className="two">
          <Field label="Título"><input value={form.title} onChange={(event) => set("title", event.target.value)} required /></Field>
          <Field label="Autor"><input value={form.author} onChange={(event) => set("author", event.target.value)} required /></Field>
          <Field label="Editora"><input value={form.publisher} onChange={(event) => set("publisher", event.target.value)} required /></Field>
          <Field label="ISBN"><input value={form.isbn} onChange={(event) => set("isbn", event.target.value)} /></Field>
          <Field label="Ano"><input type="number" value={form.publication_year} onChange={(event) => set("publication_year", event.target.value)} required /></Field>
          <Field label="Categoria">
            <select value={form.category} onChange={(event) => set("category", event.target.value)} required>
              <option value="">Selecione</option>
              {categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </Field>
          <Field label="Quantidade de exemplares"><input type="number" min={editing ? 0 : 1} value={form.quantity} onChange={(event) => set("quantity", event.target.value)} required /></Field>
          <Field label="Localização física"><input value={form.shelf_location} onChange={(event) => set("shelf_location", event.target.value)} required /></Field>
        </div>
        <Field label="Descrição"><textarea value={form.description} onChange={(event) => set("description", event.target.value)} required /></Field>
        <Field label="Capa (JPG, PNG ou WEBP, até 2 MB)"><input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setFile(event.target.files?.[0] || null)} /></Field>
        <div className="actions">
          <Button type="submit" disabled={busy}>{busy ? "Salvando..." : "Salvar"}</Button>
          <Link className="btn btn-ghost" to="/admin/livros">Cancelar</Link>
        </div>
      </form>
      {book ? (
        <section className="section">
          <h2 className="section-title">Exemplares</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Código</th><th>Local</th><th>Situação</th><th></th></tr></thead>
              <tbody>
                {book.copies.map((copy) => (
                  <tr key={copy.id}>
                    <td>{copy.inventory_code}</td>
                    <td>{copy.location}</td>
                    <td><StatusPill status={copy.status} label={copy.status_label} /></td>
                    <td>
                      {copy.status === "available" || copy.status === "unavailable" ? (
                        <Button tone="ghost" onClick={() => toggleCopy(copy.id, copy.status)}>
                          {copy.status === "available" ? "Indisponibilizar" : "Disponibilizar"}
                        </Button>
                      ) : <span className="muted mini">Vinculado a uma movimentação</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </main>
  );
}

export function CategoriesPage() {
  const toast = useToast();
  const [items, setItems] = useState<Category[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  function load() {
    api.get<Category[]>("/catalog/categories/").then((response) => setItems(response.data));
  }
  useEffect(() => { load(); }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    try {
      await api.post("/catalog/categories/", { name, description });
      setName("");
      setDescription("");
      toast("Categoria cadastrada.");
      load();
    } catch (error) {
      toast(errorMessage(error), "bad");
    }
  }

  async function remove(id: number) {
    try {
      await api.delete(`/catalog/categories/${id}/`);
      toast("Categoria excluída.");
      load();
    } catch (error) {
      toast(errorMessage(error), "bad");
    }
  }

  return (
    <main className="page">
      <div className="page-head"><div><p className="kicker">Acervo</p><h1>Categorias</h1></div></div>
      <form className="panel pad stack" onSubmit={create}>
        <div className="two">
          <Field label="Nome"><input value={name} onChange={(event) => setName(event.target.value)} required /></Field>
          <Field label="Descrição"><input value={description} onChange={(event) => setDescription(event.target.value)} /></Field>
        </div>
        <Button type="submit">Adicionar categoria</Button>
      </form>
      <div className="table-wrap" style={{ marginTop: 16 }}>
        <table>
          <thead><tr><th>Nome</th><th>Livros</th><th></th></tr></thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.name}<div className="muted mini">{item.description}</div></td>
                <td>{item.book_count}</td>
                <td><Button tone="danger" onClick={() => remove(item.id)}>Excluir</Button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
