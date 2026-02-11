## Arijentek Core – App Context

This file summarizes what the `arijentek_core` app does inside the Arijentek HRMS stack so tools and new contributors don’t need to scan all files on every run.

---

## 1. Purpose of `arijentek_core`

- **Role**: Single custom app used to centralize Arijentek‑specific behavior on top of Frappe v16, ERPNext, HRMS, Helpdesk, etc.
- **Current focus**:
  - Custom **login** flow (supports Employee ID as username).
  - **Employee portal** mounted at `/employee-portal`.
  - **Redirection logic** so employees land on the portal instead of the Desk.
  - **HRMS APIs** for the employee portal: clock in/out, leave management, payslips, attendance summary, and issue/ticket creation.

This app is loaded by the bench created in the Docker image described in the root `project_context.md`.

---

## 2. High-Level Architecture

### 2.1 Key Python modules

- `arijentek_core/hooks.py`
  - Declares the app metadata.
  - Registers **web includes**:
    - `web_include_js = "/assets/arijentek_core/js/login_redirect.js"` – patches the login success handler in the browser.
  - **Overrides** the default login endpoint:
    - `override_whitelisted_methods["frappe.auth.login"] = "arijentek_core.auth.custom_login.login"`.
  - Defines **website route rules**:
    - Maps `/employee-portal` URL to the `employee-portal` template in `www/`.
  - Configures **website home behavior** for employees:
    - `get_website_user_home_page = "arijentek_core.utils.get_employee_home_page"`.
    - `role_home_page = {"Employee": "/employee-portal"}`.
  - Session/boot hooks for redirect behavior:
    - `on_session_creation = "arijentek_core.utils.redirect_employee_after_login"`.
    - `boot_session = "arijentek_core.utils.redirect_employee_on_boot"`.

- `arijentek_core/auth/custom_login.py`
  - Exposes `login(usr, pwd)` as a **whitelisted override** for `frappe.auth.login`.
  - Supports login via **Employee ID**:
    - If `usr` matches an active `Employee.name`, it resolves the corresponding `user_id` and logs in that user.
  - Falls back to standard Frappe login:
    - Uses `LoginManager.authenticate` and `LoginManager.post_login()`.
  - Returns a JSON response with:
    - `"home_page"` set to `/employee-portal` for Employee‑only users.
    - Otherwise uses Frappe’s default home path (Desk).

- `arijentek_core/utils.py`
  - `get_employee_home_page(user)`:
    - Used by `get_website_user_home_page` hook.
    - For non‑guest users with the `Employee` role but **without** `System Manager`, returns `/employee-portal` as the landing page.
  - `redirect_employee_after_login(login_manager, *args, **kwargs)`:
    - `on_session_creation` hook.
    - Sets `frappe.local.flags.home_page` and `frappe.local.response["home_page"]` / `["redirect_to"]` so the login flow sends Employees to `/employee-portal`.
  - `redirect_employee_on_boot(bootinfo)`:
    - `boot_session` hook.
    - When an Employee tries to open Desk (`/desk`), it changes `bootinfo.home_page` to `employee-portal`.

- `arijentek_core/api.py`
  - HRMS‑facing API surface for the **employee portal frontend**:
    - **Employee info**: `get_employee_info()`.
    - **Clock in/out**:
      - `get_today_checkin()` – fetches IN/OUT logs from `Employee Checkin` for today.
      - `clock_in()` / `clock_out()` – create `Employee Checkin` docs using server‑side `now_datetime()`.
    - **Leave management**:
      - `get_leave_types()`, `get_leave_balance()`, `apply_leave()`, `get_leave_applications()`, `cancel_leave()`.
      - Uses HRMS APIs such as `get_leave_balance_on`.
    - **Payslips**:
      - `get_salary_slips()` – lists last 12 submitted slips for the employee.
      - `download_payslip(name)` – returns a PDF via `frappe.utils.pdf.get_pdf`.
    - **Issues / tickets**:
      - `create_issue(issue_type, description)` – creates either a `HD Ticket` (Helpdesk) or `Issue`, depending on availability.
    - Helper: `get_current_employee()` – maps the logged‑in `User` to their `Employee` record.

- `arijentek_core/www/employee-portal.py` and `employee-portal.html`
  - `get_context(context)`:
    - Redirects guests to `/login?redirect-to=/employee-portal`.
    - Verifies the logged‑in user has an `Employee` record; otherwise redirects to `/login`.
    - Turns off caching and hides sidebar for a focused portal view.
  - The `.html` template provides the actual portal UI shell; it is intended to call methods from `arijentek_core.api`.

### 2.2 Frontend JS helpers

- `public/js/login_redirect.js`
  - Injected on web pages via `web_include_js`.
  - Patches Frappe’s `window.login.login_handlers[200]`:
    - If the login response has `message == "No App"` and a `redirect_to` property, it:
      - Shows a lightweight “Redirecting…” message.
      - Navigates the browser to `data.redirect_to`.
    - Otherwise, delegates to Frappe’s original handler.
  - Purpose: fix edge cases where Employees receive a “No App” response but should be redirected to `/employee-portal`.

- `public/js/employee_redirect.js`
  - Not currently wired in via `hooks.py`.
  - Intended behavior:
    - On Desk (`/desk` or `/app`), calls `arijentek_core.api.check_employee_redirect`.
    - If the API responds with `redirect: true`, performs a client‑side redirect.
  - **Note**: There is no `check_employee_redirect` method defined in `arijentek_core.api`, and this file is not referenced in hooks. It is effectively **unused** at present.

---

## 3. How Redirection & Login Work Together

1. **Login submission**:
   - Browser posts to `frappe.auth.login` → actually routed to `arijentek_core.auth.custom_login.login`.
2. **Custom login handler**:
   - Accepts either a standard username or an Employee ID.
   - Logs in via `LoginManager`.
   - Picks a `home_page` value for the JSON response:
     - Employees (non‑System Managers) → `/employee-portal`.
     - Others → default Desk path.
3. **Client‑side handler (`login_redirect.js`)**:
   - Observes the login response.
   - For “No App” + `redirect_to` responses, forces a redirect to the given URL.
4. **Session hooks in `utils.py`**:
   - `on_session_creation` and `boot_session` consolidate the home page overrides so even non‑standard flows drive Employees to `/employee-portal`.

This ensures Employees land on the portal reliably, while admins still land in Desk.

---

## 4. Known Gaps / Dead or Legacy Code

- **`utils.on_login`**:
  - Currently defined as an empty legacy hook:
    - `def on_login(login_manager): pass`
  - It is no longer referenced by `hooks.py` (correct v16 hook is `on_session_creation`), so it is safe but unused.
  - It can be removed in a future cleanup pass once you confirm no other app references it.

- **`public/js/employee_redirect.js`**:
  - Not wired into `hooks.py` and relies on a non‑existent `arijentek_core.api.check_employee_redirect`.
  - At present, it has no effect and can be:
    - Either wired up properly (add the API + include JS from `hooks.py`), or
    - Deleted if you’re satisfied with the current redirect behavior via hooks and `login_redirect.js`.

No other obvious dead monkey patches are present: the active hooks (`override_whitelisted_methods`, `get_website_user_home_page`, `on_session_creation`, `boot_session`) all point to functions that exist and are coherent with Frappe v16 behavior.

---

## 5. When Extending This App

- Prefer adding **new HRMS endpoints** (e.g. biometric integration, richer dashboards) to `arijentek_core/api.py`.
- Keep **login/auth changes** isolated in `auth/custom_login.py` and small helpers in `utils.py`.
- If you add a Vue or other frontend layer for the portal:
  - Mount it inside the existing `/employee-portal` page.
  - Expose backend APIs via whitelisted methods in `api.py`.
- For future cleanup:
  - Remove `utils.on_login` once confirmed unused outside this app.
  - Decide whether to keep or delete `public/js/employee_redirect.js` depending on your desired redirect strategy.

