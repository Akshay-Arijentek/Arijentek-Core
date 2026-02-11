import { useAuthStore } from '../stores/auth';

const BASE = '/api/method';

async function request<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const auth = useAuthStore();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  const token = auth.csrfToken || (window as any).csrf_token;
  if (token && options.method && options.method !== 'GET') {
    headers['X-Frappe-CSRF-Token'] = token;
  }

  const res = await fetch(`${BASE}/${endpoint}`, {
    ...options,
    headers: { ...headers, ...(options.headers as Record<string, string> || {}) },
    credentials: 'include',
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    let msg = 'Request failed';
    if (err._server_messages) {
      try {
        const msgs = JSON.parse(err._server_messages);
        msg = JSON.parse(msgs[0]).message || msg;
      } catch { /* ignore */ }
    } else if (err.exception) {
      msg = err.exception;
    }
    throw new Error(msg);
  }

  const data = await res.json();
  return data.message !== undefined ? data.message : data;
}

function get<T = any>(endpoint: string) {
  return request<T>(endpoint, { method: 'GET' });
}

function post<T = any>(endpoint: string, body?: any) {
  return request<T>(endpoint, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  });
}

// ---------- Dashboard ----------
export const dashboardApi = {
  getData: () => get('arijentek_core.api.get_dashboard_data'),
  getEmployeeInfo: () => get('arijentek_core.api.get_employee_info'),
  getReportingInfo: () => get('arijentek_core.api.get_reporting_info'),
};

// ---------- Attendance / Clock ----------
export const attendanceApi = {
  punch: () => post('arijentek_core.api.punch'),
  getTodayCheckin: () => get('arijentek_core.api.get_today_checkin'),
  getStatus: () => get('arijentek_core.api.v1.attendance.get_status'),
  getSummary: () => get('arijentek_core.api.get_attendance_summary'),
  getRecords: (month?: number, year?: number) =>
    get(`arijentek_core.api.v1.attendance.get_attendance_records${month && year ? `?month=${month}&year=${year}` : ''}`),
};

// ---------- Leave ----------
export const leaveApi = {
  getTypes: () => get('arijentek_core.api.get_leave_types'),
  getBalance: () => get('arijentek_core.api.get_leave_balance'),
  getApplications: () => get('arijentek_core.api.get_leave_applications'),
  apply: (data: {
    leave_type: string;
    from_date: string;
    to_date: string;
    half_day?: number;
    reason?: string;
  }) => post('arijentek_core.api.apply_leave', data),
  cancel: (leave_application: string) =>
    post('arijentek_core.api.cancel_leave', { leave_application }),
};

// ---------- Payroll ----------
export const payrollApi = {
  getSlips: () => get('arijentek_core.api.get_salary_slips'),
  getDownloadUrl: (name: string) =>
    `/api/method/arijentek_core.api.download_payslip?name=${encodeURIComponent(name)}`,
};
