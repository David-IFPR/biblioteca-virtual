import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import { ScreenLoader } from "./components/ui";
import { AdminLayout } from "./layouts/AdminLayout";
import { StudentLayout } from "./layouts/StudentLayout";
import { AdminDashboardPage } from "./pages/admin/Dashboard";
import { BookFormPage, BooksPage, CategoriesPage } from "./pages/admin/collection";
import { LoansPage, MovementsPage, RequestsPage, SettingsPage } from "./pages/admin/circulation";
import { StudentDetailPage, StudentsPage } from "./pages/admin/people";
import { ForgotPassword, LoginAdmin, LoginStudent, RegisterStudent, ResetPassword } from "./pages/auth";
import { NotificationsPage } from "./pages/NotificationsPage";
import { BookDetailPage } from "./pages/student/BookDetail";
import { CatalogPage } from "./pages/student/Catalog";
import { StudentDashboardPage } from "./pages/student/Dashboard";
import { MyLoansPage } from "./pages/student/MyLoans";
import type { Role } from "./types";

function Require({ role, children }: { role: Role; children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <ScreenLoader />;
  if (!user) return <Navigate to={role === "admin" ? "/admin/entrar" : "/entrar"} replace />;
  if (user.role !== role) return <Navigate to={user.role === "admin" ? "/admin" : "/"} replace />;
  return children;
}

function Guest({ children }: { children: ReactNode; admin?: boolean }) {
  const { user, loading } = useAuth();
  if (loading) return <ScreenLoader />;
  if (user) return <Navigate to={user.role === "admin" ? "/admin" : "/"} replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/entrar" element={<Guest><LoginStudent /></Guest>} />
      <Route path="/cadastro" element={<Guest><RegisterStudent /></Guest>} />
      <Route path="/recuperar-senha" element={<ForgotPassword />} />
      <Route path="/redefinir-senha" element={<ResetPassword />} />
      <Route path="/admin/entrar" element={<Guest admin><LoginAdmin /></Guest>} />

      <Route element={<Require role="student"><StudentLayout /></Require>}>
        <Route index element={<StudentDashboardPage />} />
        <Route path="catalogo" element={<CatalogPage />} />
        <Route path="catalogo/:id" element={<BookDetailPage />} />
        <Route path="emprestimos" element={<MyLoansPage />} />
        <Route path="notificacoes" element={<NotificationsPage />} />
      </Route>

      <Route path="/admin" element={<Require role="admin"><AdminLayout /></Require>}>
        <Route index element={<AdminDashboardPage />} />
        <Route path="livros" element={<BooksPage />} />
        <Route path="livros/novo" element={<BookFormPage />} />
        <Route path="livros/:id" element={<BookFormPage />} />
        <Route path="categorias" element={<CategoriesPage />} />
        <Route path="alunos" element={<StudentsPage />} />
        <Route path="alunos/:id" element={<StudentDetailPage />} />
        <Route path="solicitacoes" element={<RequestsPage />} />
        <Route path="emprestimos" element={<LoansPage />} />
        <Route path="movimentos" element={<MovementsPage />} />
        <Route path="configuracoes" element={<SettingsPage />} />
        <Route path="notificacoes" element={<NotificationsPage admin />} />
      </Route>

      <Route path="*" element={<Navigate to="/entrar" replace />} />
    </Routes>
  );
}
