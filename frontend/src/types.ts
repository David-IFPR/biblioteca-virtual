export type Role = "student" | "admin";

export interface AuthUser {
  id: number;
  full_name: string;
  email: string;
  role: Role;
  enrollment: string | null;
  is_blocked: boolean;
}

export interface TokenResponse {
  access: string;
  refresh: string;
  user: AuthUser;
  detail?: string;
  debug_token?: string;
}

export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface CopySummary {
  available: number;
  reserved: number;
  loaned: number;
  unavailable: number;
  total: number;
}

export interface BookCopy {
  id: number;
  inventory_code: string;
  status: string;
  status_label: string;
  location: string;
}

export interface Book {
  id: number;
  title: string;
  author: string;
  publisher: string;
  isbn: string | null;
  publication_year: number;
  category: number;
  category_name: string;
  description: string;
  cover_url: string | null;
  shelf_location: string;
  total_copies: number;
  available_copies: number;
  availability: "available" | "unavailable";
  copy_summary: CopySummary;
  copies: BookCopy[];
  created_at: string;
  can_request?: boolean;
  request_block_reason?: string;
}

export interface Category {
  id: number;
  name: string;
  description: string;
  book_count: number;
}

export interface DueChange {
  id: number;
  previous_due_date: string;
  new_due_date: string;
  reason: string;
  changed_by_name: string;
  changed_at: string;
}

export interface Loan {
  id: number;
  book_id: number;
  book_title: string;
  book_author: string;
  cover_url: string | null;
  student_id: number;
  student_name: string;
  enrollment: string;
  copy_code: string;
  status: string;
  display_status: string;
  status_label: string;
  is_overdue: boolean;
  loaned_at: string;
  due_date: string;
  return_requested_at: string | null;
  returned_at: string | null;
  confirmed_by_name: string | null;
  registered_by_name: string | null;
  due_date_changes: DueChange[];
}

export interface LoanRequestItem {
  id: number;
  book_id: number;
  book_title: string;
  book_author: string;
  cover_url: string | null;
  student_name: string;
  enrollment: string;
  copy_code: string | null;
  status: string;
  status_label: string;
  available_copies: number;
  requested_at: string;
  reviewed_at: string | null;
  reviewed_by_name: string | null;
  rejection_reason: string;
  detail?: string;
}

export interface StudentRow {
  id: number;
  full_name: string;
  enrollment: string;
  email: string;
  created_at: string;
  loan_count: number;
  active_loan_count: number;
  is_blocked: boolean;
  blocked_reason: string;
  account_status: string;
  account_status_label: string;
  loans?: Loan[];
  requests?: LoanRequestItem[];
}

export interface Notice {
  id: number;
  kind: string;
  kind_label: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface Movement {
  id: number;
  action: string;
  action_label: string;
  description: string;
  actor_name: string;
  student_name: string | null;
  book_title: string | null;
  created_at: string;
}

export interface Policy {
  max_active_loans: number;
  loan_days: number;
  reminder_days: number;
}

export interface ChartItem {
  label: string;
  value: number;
}

export interface AdminDashboard {
  books: number;
  copies: number;
  available_copies: number;
  loaned_copies: number;
  reserved_copies: number;
  pending_requests: number;
  approved_waiting_pickup: number;
  returns_waiting: number;
  overdue: number;
  students: number;
  active_loans: number;
  chart: ChartItem[];
  recent_requests: LoanRequestItem[];
  overdue_loans: Loan[];
  recent_movements: Movement[];
}

export interface StudentDashboard {
  student_name: string;
  enrollment: string;
  available_books: number;
  active_loans: number;
  pending_requests: number;
  approved_requests: number;
  loan_history: number;
  overdue_loans: number;
  unread_notifications: number;
  recent_books: Book[];
  featured_books: Book[];
  recent_loans: Loan[];
}

export interface MyCirculation {
  requests: LoanRequestItem[];
  loans: Loan[];
  counts: Record<string, number>;
}
