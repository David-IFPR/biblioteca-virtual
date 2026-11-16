import { Bell, BookOpen, KeyRound, LogOut } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api, errorMessage } from "../api/http";
import { useAuth } from "../auth/AuthContext";
import { Button, Field, Modal } from "../components/ui";
import { useToast } from "../components/toast";

export function StudentLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [unread, setUnread] = useState(0);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const load = () => {
      api.get<{ unread: number }>("/notifications/summary/").then((response) => setUnread(response.data.unread)).catch(() => undefined);
    };
    load();
    const timer = window.setInterval(load, 60000);
    return () => window.clearInterval(timer);
  }, []);

  async function savePassword() {
    setBusy(true);
    try {
      await api.post("/auth/change-password/", {
        current_password: current,
        password: next,
        password_confirm: confirm,
      });
      toast("Senha alterada.");
      setPasswordOpen(false);
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (error) {
      toast(errorMessage(error), "bad");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <header className="topbar">
        <NavLink to="/" className="brand">
          <span className="mark"><BookOpen size={18} /></span>
          Acervo
        </NavLink>
        <nav className="nav-links">
          <NavLink to="/" end>Início</NavLink>
          <NavLink to="/catalogo">Catálogo</NavLink>
          <NavLink to="/emprestimos">Meus empréstimos</NavLink>
        </nav>
        <div className="top-actions">
          <NavLink to="/notificacoes" className="bell" aria-label="Notificações">
            <Bell size={18} />
            {unread > 0 ? <em>{unread}</em> : null}
          </NavLink>
          <div className="who">
            <strong>{user?.full_name}</strong>
            <span>{user?.enrollment}</span>
          </div>
          <button className="icon-btn" type="button" aria-label="Alterar senha" onClick={() => setPasswordOpen(true)}>
            <KeyRound size={18} />
          </button>
          <button
            className="icon-btn"
            type="button"
            aria-label="Sair"
            onClick={async () => {
              await logout();
              navigate("/entrar");
            }}
          >
            <LogOut size={18} />
          </button>
        </div>
      </header>
      <Outlet />
      {passwordOpen ? (
        <Modal title="Alterar senha" onClose={() => setPasswordOpen(false)}>
          <div className="stack">
            <Field label="Senha atual"><input type="password" value={current} onChange={(event) => setCurrent(event.target.value)} /></Field>
            <Field label="Nova senha"><input type="password" value={next} onChange={(event) => setNext(event.target.value)} /></Field>
            <Field label="Confirmar nova senha"><input type="password" value={confirm} onChange={(event) => setConfirm(event.target.value)} /></Field>
            <Button onClick={savePassword} disabled={busy}>{busy ? "Salvando..." : "Salvar senha"}</Button>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
