import { FormEvent, useState, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { BookOpen } from "lucide-react";
import { api, errorMessage } from "../api/http";
import { useAuth } from "../auth/AuthContext";
import { Button, Field } from "../components/ui";

function Shell({ children, quote }: { children: ReactNode; quote: string }) {
  return (
    <div className="auth-screen">
      <section className="auth-panel">
        <div className="brand-mark"><i><BookOpen size={18} /></i> Acervo</div>
        <div>
          <h1>{quote}</h1>
          <p>A biblioteca da instituição, com catálogo, empréstimos e devoluções no mesmo lugar.</p>
        </div>
        <p>Área do aluno e área da biblioteca funcionam com acessos separados.</p>
      </section>
      <section className="auth-form">{children}</section>
    </div>
  );
}

export function LoginStudent() {
  const { loginStudent } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [enrollment, setEnrollment] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(params.get("aviso") === "bloqueada" ? "Sua conta está bloqueada. Procure a biblioteca." : "");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await loginStudent(enrollment, password);
      navigate("/");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell quote="O que você vai ler agora?">
      <form className="card stack" onSubmit={submit}>
        <div>
          <p className="kicker">Área do aluno</p>
          <h2>Entrar</h2>
          <p className="lede">Use a matrícula e a senha cadastradas na biblioteca.</p>
        </div>
        {error ? <div className="alert">{error}</div> : null}
        <Field label="Matrícula"><input value={enrollment} onChange={(event) => setEnrollment(event.target.value)} required /></Field>
        <Field label="Senha"><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></Field>
        <Button type="submit" disabled={busy}>{busy ? "Entrando..." : "Entrar"}</Button>
        <div className="link-row">
          <Link className="quiet-link" to="/recuperar-senha">Recuperar senha</Link>
          <Link className="quiet-link" to="/cadastro">Criar cadastro</Link>
        </div>
        <Link className="quiet-link" to="/admin/entrar">Sou da biblioteca</Link>
      </form>
    </Shell>
  );
}

export function RegisterStudent() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", enrollment: "", email: "", password: "", password_confirm: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function set(key: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (form.password !== form.password_confirm) {
      setError("A confirmação de senha não confere.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await register(form);
      navigate("/");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell quote="Sua matrícula abre o acervo.">
      <form className="card stack" onSubmit={submit}>
        <div>
          <p className="kicker">Novo aluno</p>
          <h2>Cadastro</h2>
          <p className="lede">A matrícula precisa ser única. A senha fica protegida no servidor.</p>
        </div>
        {error ? <div className="alert">{error}</div> : null}
        <Field label="Nome completo"><input value={form.full_name} onChange={(event) => set("full_name", event.target.value)} required /></Field>
        <Field label="Matrícula"><input value={form.enrollment} onChange={(event) => set("enrollment", event.target.value)} required /></Field>
        <Field label="E-mail"><input type="email" value={form.email} onChange={(event) => set("email", event.target.value)} required /></Field>
        <Field label="Senha" hint="Mínimo de 8 caracteres."><input type="password" value={form.password} onChange={(event) => set("password", event.target.value)} required /></Field>
        <Field label="Confirmar senha"><input type="password" value={form.password_confirm} onChange={(event) => set("password_confirm", event.target.value)} required /></Field>
        <Button type="submit" disabled={busy}>{busy ? "Criando..." : "Criar conta e entrar"}</Button>
        <Link className="quiet-link" to="/entrar">Já tenho cadastro</Link>
      </form>
    </Shell>
  );
}

export function ForgotPassword() {
  const [enrollment, setEnrollment] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [token, setToken] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const { data } = await api.post("/auth/password-reset/", { enrollment, email });
      setMessage(data.detail);
      setToken(data.debug_token || "");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <Shell quote="Vamos recuperar o acesso.">
      <form className="card stack" onSubmit={submit}>
        <div>
          <p className="kicker">Recuperação</p>
          <h2>Redefinir senha</h2>
          <p className="lede">Informe a matrícula do aluno ou o e-mail da conta.</p>
        </div>
        {error ? <div className="alert">{error}</div> : null}
        {message ? <div className="alert ok">{message}</div> : null}
        {token ? (
          <div className="alert warn">
            Ambiente de desenvolvimento: use este código para concluir a troca.
            <div><Link className="quiet-link" to={`/redefinir-senha?token=${token}`}>Abrir redefinição</Link></div>
          </div>
        ) : null}
        <Field label="Matrícula"><input value={enrollment} onChange={(event) => setEnrollment(event.target.value)} /></Field>
        <Field label="Ou e-mail"><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></Field>
        <Button type="submit">Enviar instruções</Button>
        <Link className="quiet-link" to="/entrar">Voltar ao login</Link>
      </form>
    </Shell>
  );
}

export function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [token, setToken] = useState(params.get("token") || "");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const { data } = await api.post("/auth/password-reset/confirm/", {
        token,
        password,
        password_confirm: passwordConfirm,
      });
      setDone(data.detail);
      window.setTimeout(() => navigate("/entrar"), 1200);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <Shell quote="Escolha uma senha nova.">
      <form className="card stack" onSubmit={submit}>
        <h2>Nova senha</h2>
        {error ? <div className="alert">{error}</div> : null}
        {done ? <div className="alert ok">{done}</div> : null}
        <Field label="Código de redefinição"><input value={token} onChange={(event) => setToken(event.target.value)} required /></Field>
        <Field label="Nova senha"><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></Field>
        <Field label="Confirmar senha"><input type="password" value={passwordConfirm} onChange={(event) => setPasswordConfirm(event.target.value)} required /></Field>
        <Button type="submit">Salvar senha</Button>
      </form>
    </Shell>
  );
}

export function LoginAdmin() {
  const { loginAdmin } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await loginAdmin(email, password);
      navigate("/admin");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell quote="A biblioteca em ordem.">
      <form className="card stack" onSubmit={submit}>
        <div>
          <p className="kicker">Professores e administradores</p>
          <h2>Área da biblioteca</h2>
          <p className="lede">Somente esta conta confirma devoluções e altera o acervo.</p>
        </div>
        {error ? <div className="alert">{error}</div> : null}
        <Field label="E-mail"><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></Field>
        <Field label="Senha"><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></Field>
        <Button type="submit" disabled={busy}>{busy ? "Entrando..." : "Entrar"}</Button>
        <Link className="quiet-link" to="/recuperar-senha">Recuperar senha</Link>
        <Link className="quiet-link" to="/entrar">Voltar à área do aluno</Link>
      </form>
    </Shell>
  );
}
