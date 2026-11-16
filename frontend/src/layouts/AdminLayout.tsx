import {
  Bell,
  BookMarked,
  ClipboardList,
  History,
  KeyRound,
  LayoutDashboard,
  Library,
  LogOut,
  Menu,
  Settings,
  Users,
} from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api, errorMessage } from "../api/http";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/toast";
import { Button, Field, Modal } from "../components/ui";

const LINKS = [
  { to: "/admin", label: "Painel", icon: LayoutDashboard, end: true },
  { to: "/admin/livros", label: "Livros", icon: BookMarked, end: false },
  { to: "/admin/categorias", label: "Categorias", icon: Library, end: false },
  { to: "/admin/alunos", label: "Alunos", icon: Users, end: false },
  { to: "/admin/solicitacoes", label: "Solicitações", icon: ClipboardList, end: false },
  { to: "/admin/emprestimos", label: "Empréstimos", icon: Library, end: false },
  { to: "/admin/movimentos", label: "Histórico", icon: History, end: false },
  { to: "/admin/configuracoes", label: "Regras", icon: Settings, end: false },
];

export function AdminLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");

  useEffect(() => {
    const load = () => {
      api.get<{ unread: number }>("/notifications/summary/").then((response) => setUnread(response.data.unread)).catch(() => undefined);
    };
    load();
    const timer = window.setInterval(load, 60000);
    return () => window.clearInterval(timer);
  }, []);

  async function savePassword() {
    try {
      await api.post("/auth/change-password/", {
        current_password: current,
        password: next,
        password_confirm: confirm,
      });
      toast("Senha alterada.");
      setPasswordOpen(false);
    } catch (error) {
      toast(errorMessage(error), "bad");
    }
  }

  return (
    <div className={open ? "admin-shell nav-open" : "admin-shell"}>
      <aside className="sidebar">
        <NavLink to="/admin" end className="brand" onClick={() => setOpen(false)}>
          <span className="mark">A</span> Acervo
        </NavLink>
        <nav className="side-nav">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className="side-link"
              onClick={() => setOpen(false)}
            >
              <link.icon size={16} /> {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="foot">
          <button className="side-link" type="button" onClick={() => setPasswordOpen(true)}>
            <KeyRound size={16} /> Alterar senha
          </button>
          <button
            className="side-link"
            type="button"
            onClick={async () => {
              await logout();
              navigate("/admin/entrar");
            }}
          >
            <LogOut size={16} /> Sair
          </button>
        </div>
      </aside>
      <div className="admin-main">
        <div className="admin-top">
          <button className="menu-btn icon-btn" type="button" onClick={() => setOpen((value) => !value)} aria-label="Menu">
            <Menu />
          </button>
          <div>
            <strong>{user?.full_name}</strong>
            <div className="muted mini">Administração da biblioteca</div>
          </div>
          <NavLink to="/admin/notificacoes" className="bell" aria-label="Notificações">
            <Bell size={18} />
            {unread > 0 ? <em>{unread}</em> : null}
          </NavLink>
        </div>
        <Outlet />
      </div>
      {passwordOpen ? (
        <Modal title="Alterar senha" onClose={() => setPasswordOpen(false)}>
          <div className="stack">
            <Field label="Senha atual"><input type="password" value={current} onChange={(event) => setCurrent(event.target.value)} /></Field>
            <Field label="Nova senha"><input type="password" value={next} onChange={(event) => setNext(event.target.value)} /></Field>
            <Field label="Confirmar"><input type="password" value={confirm} onChange={(event) => setConfirm(event.target.value)} /></Field>
            <Button onClick={savePassword}>Salvar senha</Button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
