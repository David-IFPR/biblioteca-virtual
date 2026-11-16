import { useEffect, useState } from "react";
import { api, errorMessage } from "../api/http";
import { useToast } from "../components/toast";
import { Button, Empty } from "../components/ui";
import { formatDateTime } from "../format";
import type { Notice, Page } from "../types";

export function NotificationsPage({ admin = false }: { admin?: boolean }) {
  const toast = useToast();
  const [items, setItems] = useState<Notice[]>([]);

  function load() {
    api.get<Page<Notice>>("/notifications/", { params: { page_size: 30 } }).then((response) => setItems(response.data.results));
  }

  useEffect(() => {
    load();
  }, []);

  async function read(id: number) {
    try {
      await api.post(`/notifications/${id}/read/`);
      load();
    } catch (error) {
      toast(errorMessage(error), "bad");
    }
  }

  async function readAll() {
    await api.post("/notifications/read-all/");
    toast("Notificações marcadas como lidas.");
    load();
  }

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <p className="kicker">{admin ? "Administração" : "Avisos"}</p>
          <h1>Notificações</h1>
        </div>
        <Button tone="ghost" onClick={readAll}>Marcar todas como lidas</Button>
      </div>
      {items.length === 0 ? <Empty title="Sem notificações" text="Os avisos de empréstimo, prazo e devolução aparecem aqui." /> : (
        <div className="notice-list">
          {items.map((item) => (
            <article key={item.id} className="panel pad" style={{ opacity: item.is_read ? 0.72 : 1 }}>
              <div className="split">
                <strong>{item.title}</strong>
                <span className="muted mini">{formatDateTime(item.created_at)}</span>
              </div>
              <p className="lede">{item.message}</p>
              <div className="split">
                <span className="pill">{item.is_read ? "Lida" : "Não lida"}</span>
                {!item.is_read ? <Button tone="ghost" onClick={() => read(item.id)}>Marcar como lida</Button> : null}
              </div>
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
