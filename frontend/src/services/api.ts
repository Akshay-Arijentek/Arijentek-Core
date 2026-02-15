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

// Caching helper — TTL: 1 hour
const CACHE_TTL_MS = 60 * 60 * 1000; // 1 hour

export async function useCachedFetch<T>(
  key: string,
  fetcher: () => Promise<T>,
  onData: (data: T) => void
) {
  // 1. Try cache (with expiry check)
  const cached = localStorage.getItem(`cache_${key}`);
  if (cached) {
    try {
      const { data, timestamp } = JSON.parse(cached);
      const isExpired = Date.now() - timestamp > CACHE_TTL_MS;
      if (!isExpired) {
        onData(data);
      } else {
        // Remove stale cache
        localStorage.removeItem(`cache_${key}`);
      }
    } catch (e) {
      console.warn('Cache parse error', key);
      localStorage.removeItem(`cache_${key}`);
    }
  }

  // 2. Fetch fresh
  try {
    const freshData = await fetcher();
    onData(freshData);
    // 3. Update cache
    localStorage.setItem(`cache_${key}`, JSON.stringify({
      data: freshData,
      timestamp: Date.now()
    }));
  } catch (e) {
    console.error('Fetch failed', key, e);
    // If we had no cache, propagate error? Or just silent fail?
    // user wants "offline" behavior, so silent fail if we have cache is good.
    if (!cached) throw e;
  }
}

// ---------- Dashboard ----------
export const dashboardApi = {
  getData: () => get('arijentek_core.api.get_dashboard_data'),
  getEmployeeInfo: () => get('arijentek_core.api.get_employee_info'),
  getReportingInfo: () => get('arijentek_core.api.get_reporting_info'),
};

// ---------- Attendance / Clock ----------
export const attendanceApi = {
  punch: (timestamp?: string) => post('arijentek_core.api.punch', { timestamp }),
  getTodayCheckin: () => get('arijentek_core.api.get_today_checkin'),
  getStatus: () => get('arijentek_core.api.v1.attendance.get_status'),
  getSummary: () => get('arijentek_core.api.get_attendance_summary'),
  getRecords: (month?: number, year?: number) =>
    get(`arijentek_core.api.get_attendance_records${month && year ? `?month=${month}&year=${year}` : ''}`),
};

// ---------- Leave ----------
export const leaveApi = {
  getTypes: () => get('arijentek_core.api.get_leave_types'),
  getBalance: () => get('arijentek_core.api.get_leave_balance'),
  getApplications: () => get('arijentek_core.api.get_leave_applications'),
  getHolidays: (from_date?: string, to_date?: string, exclude_weekly_off?: boolean) => {
    const params: string[] = [];
    if (from_date && to_date) {
      params.push(`from_date=${from_date}`, `to_date=${to_date}`);
    }
    if (exclude_weekly_off) {
      params.push('exclude_weekly_off=1');
    }
    const qs = params.length ? `?${params.join('&')}` : '';
    return get(`arijentek_core.api.get_holidays${qs}`);
  },
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
  generatePayroll: (month?: number, year?: number) =>
    post('arijentek_core.api.generate_payroll', { month, year }),
  getSlipDetails: (name: string) =>
    get(`arijentek_core.api.get_payslip_details?name=${encodeURIComponent(name)}`),
  getPreview: (month?: number, year?: number) =>
    get(`arijentek_core.api.get_payroll_preview${month && year ? `?month=${month}&year=${year}` : ''}`),
  getDashboard: () => get('arijentek_core.api.get_payroll_dashboard'),
  generateMyPayslip: (month?: number, year?: number) =>
    post('arijentek_core.api.generate_my_payslip', { month, year }),
  deletePayslip: (name: string) =>
    post('arijentek_core.api.delete_my_payslip', { name }),
};

export const managerApi = {
  getTeamLeaves: () => get('arijentek_core.api.get_team_leaves'),
  processLeave: (application: string, status: 'Approved' | 'Rejected') =>
    post('arijentek_core.api.process_leave', { leave_application: application, status })
};

export const authApi = {
  changePassword: (oldPw: string, newPw: string) =>
    post('arijentek_core.api.auth.change_password', { old_password: oldPw, new_password: newPw })
};

export const expensesApi = {
  getTypes: () => get('arijentek_core.api.expenses.get_expense_types'),
  getMyExpenses: () => get('arijentek_core.api.expenses.get_my_expenses'),
  submit: (data: any) => post('arijentek_core.api.expenses.submit_expense_claim', data),
  // Manager
  getTeamExpenses: () => get('arijentek_core.api.expenses.get_team_expenses'),
  process: (name: string, action: 'Approve' | 'Reject') =>
    post('arijentek_core.api.expenses.process_expense', { name, action })
};
