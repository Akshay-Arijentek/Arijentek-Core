import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

interface SessionInfo {
  user: string;
  full_name: string;
  is_logged_in: boolean;
  has_desk_access: boolean;
  employee: string | null;
  employee_name: string;
  department: string;
  designation: string;
}

/**
 * Fetch CSRF token via GET (exempt from CSRF validation).
 */
async function fetchCsrfToken(): Promise<string> {
  const res = await fetch('/api/method/arijentek_core.api.v1.auth.get_csrf_token', {
    method: 'GET',
    headers: { Accept: 'application/json' },
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to fetch CSRF token');
  const data = await res.json();
  return data.message;
}

/**
 * Fetch session info from the backend (GET, works for guests too).
 */
async function fetchSessionInfo(): Promise<SessionInfo> {
  const res = await fetch('/api/method/arijentek_core.api.get_session_info', {
    method: 'GET',
    headers: { Accept: 'application/json' },
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to fetch session info');
  const data = await res.json();
  return data.message;
}

export const useAuthStore = defineStore('auth', () => {
  // --- State ---
  const user = ref('Guest');
  const fullName = ref('Guest');
  const csrfToken = ref('');
  const hasDeskAccess = ref(false);
  const employee = ref<string | null>(null);
  const employeeName = ref('');
  const department = ref('');
  const designation = ref('');
  const ready = ref(false); // true once init() completes

  // --- Getters ---
  const isLoggedIn = computed(() => user.value !== 'Guest' && user.value !== '');

  // --- Actions ---

  /**
   * Initialise the auth state. Called once at app startup before mounting.
   * 1. Fetches CSRF token (needed for all POST requests).
   * 2. Fetches session info from the server to determine login status,
   *    user details, and desk access.
   */
  async function init() {
    try {
      // Fetch CSRF token first (always needed)
      const token = await fetchCsrfToken();
      csrfToken.value = token;
      ;(window as any).csrf_token = token;

      // Fetch session info to know who we are
      const info = await fetchSessionInfo();
      if (info.is_logged_in) {
        user.value = info.user;
        fullName.value = info.full_name || info.user;
        hasDeskAccess.value = info.has_desk_access;
        employee.value = info.employee;
        employeeName.value = info.employee_name || '';
        department.value = info.department || '';
        designation.value = info.designation || '';
      } else {
        _resetToGuest();
      }
    } catch {
      // If server is unreachable, fall back to cookie check
      const cookies = new URLSearchParams(document.cookie.split('; ').join('&'));
      const uid = cookies.get('user_id');
      if (uid && uid !== 'Guest') {
        user.value = uid;
        fullName.value = uid; // best-effort
      } else {
        _resetToGuest();
      }
    } finally {
      ready.value = true;
    }
  }

  /**
   * Log in with username/password.
   */
  async function login(usr: string, pwd: string) {
    try {
      // Ensure we have a CSRF token
      if (!csrfToken.value) {
        csrfToken.value = await fetchCsrfToken();
        ;(window as any).csrf_token = csrfToken.value;
      }

      const res = await fetch('/api/method/arijentek_core.api.v1.auth.login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          'X-Frappe-CSRF-Token': csrfToken.value,
        },
        credentials: 'include',
        body: JSON.stringify({ usr, pwd }),
      });

      const data = await res.json();
      const msg = typeof data.message === 'object' ? data.message : data;
      const text = msg?.message ?? data.message;

      if (text === 'Logged In') {
        // Update CSRF token (session changed)
        const newToken = msg.csrf_token || data.csrf_token;
        if (newToken) {
          csrfToken.value = newToken;
          ;(window as any).csrf_token = newToken;
        }

        // Fetch full session info now that we're logged in
        try {
          const info = await fetchSessionInfo();
          user.value = info.user;
          fullName.value = info.full_name || msg.full_name || usr;
          hasDeskAccess.value = info.has_desk_access;
          employee.value = info.employee;
          employeeName.value = info.employee_name || '';
          department.value = info.department || '';
          designation.value = info.designation || '';
        } catch {
          // Fallback to login response data
          user.value = msg.user || usr;
          fullName.value = msg.full_name || data.full_name || usr;
        }

        return { success: true, home_page: data.home_page || msg.home_page };
      } else {
        let errorMsg = 'Login failed';
        if (data._server_messages) {
          try {
            const msgs = JSON.parse(data._server_messages);
            errorMsg = JSON.parse(msgs[0]).message || errorMsg;
          } catch { /* ignore */ }
        }
        throw new Error(data.exception || errorMsg);
      }
    } catch (error) {
      return { success: false, error };
    }
  }

  /**
   * Log out and redirect to login page.
   */
  async function logout() {
    try {
      await fetch('/api/method/logout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Frappe-CSRF-Token': csrfToken.value || (window as any).csrf_token || '',
        },
        credentials: 'include',
      });
    } catch { /* ignore */ }
    _resetToGuest();
    window.location.href = '/employee-portal#/login';
  }

  function _resetToGuest() {
    user.value = 'Guest';
    fullName.value = 'Guest';
    csrfToken.value = '';
    hasDeskAccess.value = false;
    employee.value = null;
    employeeName.value = '';
    department.value = '';
    designation.value = '';
    ;(window as any).csrf_token = '';
  }

  return {
    user,
    fullName,
    csrfToken,
    hasDeskAccess,
    employee,
    employeeName,
    department,
    designation,
    ready,
    isLoggedIn,
    init,
    login,
    logout,
  };
});
