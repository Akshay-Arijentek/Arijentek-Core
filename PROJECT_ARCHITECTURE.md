# Arijentek Core – Complete Project Architecture & Code Reference

> **Purpose**: A self-contained guide explaining every folder, file, function, and architectural decision in the Arijentek Employee Portal project. By reading this document, anyone can understand the codebase, locate functionality, and comprehend how backend and frontend communicate.

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Directory Structure](#3-directory-structure)
4. [Backend (Python/Frappe)](#4-backend-pythonfrappe)
5. [Frontend (Vue.js/Vite)](#5-frontend-vuejsvite)
6. [Backend–Frontend Communication](#6-backendfrontend-communication)
7. [Data Flow & Request Lifecycle](#7-data-flow--request-lifecycle)
8. [Function Reference Map](#8-function-reference-map)
9. [Configuration Files](#9-configuration-files)
10. [Development & Deployment](#10-development--deployment)

---

## 1. Project Overview

### What Is This?

**Arijentek Core** is a Frappe app that provides an **Employee Portal** – a modern, web-based interface for employees to:

- **Clock in/out** – Record attendance with a single toggle button
- **Manage leave** – View balance, apply, track, and cancel leave
- **Access payroll** – View and download salary slips (PDF)
- **See dashboard** – Summary of attendance, leave balance, profile

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Backend | Frappe Framework (Python) | API, database, auth, session |
| HR Data | ERPNext HRMS | Employee, Attendance, Leave, Salary Slip doctypes |
| Frontend | Vue 3 + TypeScript | SPA for employee portal UI |
| Build | Vite | Fast dev server, production build |
| Styling | Tailwind CSS | Utility-first CSS, dark theme |
| State | Pinia | Auth and global state |
| Routing | Vue Router (hash mode) | Client-side navigation |

### Why This Architecture?

1. **Frappe** – Provides ERPNext HRMS (Employee, Leave Application, Salary Slip, Attendance, etc.), user/role management, session, and REST API.
2. **Vue SPA** – Lightweight, fast, mobile-friendly UI instead of Frappe’s Jinja-based web.
3. **Custom login** – Employee ID login, role-based redirects (employees → portal, system users → desk).
4. **Separation** – Backend exposes whitelisted API methods; frontend consumes them via `fetch`.

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    BROWSER (User)                                        │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  VUE SPA (Employee Portal)                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │   Login     │  │  Dashboard  │  │   Leave     │  │   Payroll   │  │ AppLayout   │   │
│  │   .vue      │  │  View.vue   │  │   View.vue  │  │  View.vue   │  │  (sidebar)  │   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────────────┘   │
│         │                │                │                │                             │
│         └────────────────┼────────────────┼────────────────┘                             │
│                          │                │                                              │
│  ┌───────────────────────▼────────────────▼───────────────────────────────────────────┐  │
│  │  Pinia (auth.ts)          │  api.ts (services)         │  Vue Router              │  │
│  │  - user, fullName         │  - dashboardApi            │  - /login, /, /leave,    │  │
│  │  - csrfToken              │  - attendanceApi           │    /payroll              │  │
│  │  - hasDeskAccess          │  - leaveApi                │  - Auth guards           │  │
│  └──────────────────────────┴───────────────────────────┴───────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                          HTTP GET/POST + X-Frappe-CSRF-Token + credentials: include
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  FRAPPE BACKEND (Python)                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │  website_route_rules: /employee-portal → employee-portal.html                      │   │
│  │  www/employee-portal.py: get_context() → redirect guests / non-employees         │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                               │
│  ┌──────────────────────────────────────▼──────────────────────────────────────────┐   │
│  │  /api/method/<module>.<function>                                                   │   │
│  │  - arijentek_core.api.get_session_info      (GET, guest OK)                       │   │
│  │  - arijentek_core.api.v1.auth.get_csrf_token (GET, guest OK)                      │   │
│  │  - arijentek_core.api.v1.auth.login         (POST, guest OK)                      │   │
│  │  - arijentek_core.api.punch                 (POST, auth required)                │   │
│  │  - arijentek_core.api.get_dashboard_data    (GET)                                 │   │
│  │  - arijentek_core.api.apply_leave           (POST)                                 │   │
│  │  - ... etc                                                                        │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                               │
│  ┌──────────────────────────────────────▼──────────────────────────────────────────┐   │
│  │  hooks.py: before_request → security.validate_request                            │   │
│  │  hooks.py: override_whitelisted_methods["frappe.auth.login"] → custom_login       │   │
│  │  hooks.py: on_session_creation → redirect_employee_after_login                    │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                               │
│  ┌──────────────────────────────────────▼──────────────────────────────────────────┐   │
│  │  ERPNext HRMS DocTypes                                                            │   │
│  │  - Employee, Employee Checkin, Attendance, Leave Application,                     │   │
│  │    Leave Type, Salary Slip, Salary Structure Assignment, Payroll Entry            │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Request Flow (Simplified)

```
User clicks "Clock In" 
  → ClockWidget.vue calls attendanceApi.punch()
  → api.ts does POST /api/method/arijentek_core.api.punch
  → Headers: X-Frappe-CSRF-Token, credentials: include
  → Frappe routes to arijentek_core.api.punch()
  → punch() creates Employee Checkin doc, returns JSON
  → Frontend receives { status, log_type, time }
  → ClockWidget updates UI (timer starts)
```

---

## 3. Directory Structure

```
arijentek_core/                          # Root of the Frappe app
├── .github/workflows/                   # CI (tests, linter)
│   ├── ci.yml                           # Run Frappe tests, bench setup
│   └── linter.yml                       # Lint checks
├── .editorconfig                        # Editor formatting
├── .eslintrc                            # Legacy ESLint (if used)
├── .gitignore
├── .oxlintrc.json                       # Oxlint config (frontend)
├── .pre-commit-config.yaml              # Pre-commit hooks
├── CONTEXT.md                           # High-level context (legacy)
├── license.txt
├── PROJECT_ARCHITECTURE.md              # THIS DOCUMENT
├── README.md
├── pyproject.toml                       # Python project config, Ruff
│
├── arijentek_core/                      # Python package (backend)
│   ├── __init__.py
│   ├── hooks.py                         # ★ Frappe hooks (critical)
│   ├── modules.txt                      # App modules
│   ├── patches.txt                      # DB patches
│   │
│   ├── api/                             # ★ API endpoints
│   │   ├── __init__.py                  # Main API (dashboard, punch, leave, payroll, etc.)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py                  # get_csrf_token, login
│   │       └── attendance.py            # punch, get_status, get_dashboard_data (v1)
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   └── custom_login.py              # Override frappe.auth.login
│   │
│   ├── attendance/
│   │   ├── __init__.py
│   │   ├── auto_attendance.py           # ★ Real-time attendance sync
│   │   └── sync.py                      # Sync checkins → Attendance
│   │
│   ├── config/                          # Empty config module
│   │   └── __init__.py
│   │
│   ├── payroll/
│   │   ├── __init__.py
│   │   ├── automation.py               # Monthly payroll automation
│   │   ├── calculator.py               # ★ Attendance-based payroll calculation
│   │   ├── payslip_generator.py        # ★ Salary slip generation with LOP
│   │   └── setup.py                    # ★ Default salary components setup
│   │
│   ├── security.py                     # Request validation, session hooks
│   ├── utils.py                        # Portal redirect helpers
│   │
│   ├── public/                          # Static assets (served by Frappe)
│   │   ├── js/
│   │   │   └── login_redirect.js        # Patches login handler on web
│   │   └── frontend/                    # ★ Built Vue SPA output
│   │       ├── assets/                  # main.js, *.css, chunk JS
│   │       ├── index.html
│   │       └── favicon.ico
│   │
│   ├── templates/                      # Jinja (minimal use)
│   │   └── pages/
│   │       └── __init__.py
│   │
│   ├── arijentek_solution/              # Frappe module placeholder
│   │   └── __init__.py
│   │
│   └── www/                             # ★ Web pages
│       ├── employee-portal.py          # Controller for /employee-portal
│       └── employee-portal.html        # HTML shell for SPA
│
└── frontend/                            # Vue 3 SPA source
    ├── index.html                       # Dev entry
    ├── package.json
    ├── vite.config.ts                   # Build, proxy, output dir
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── tsconfig*.json
    ├── eslint.config.ts
    ├── env.d.ts
    ├── public/favicon.ico
    │
    └── src/
        ├── main.ts                      # App bootstrap, auth init
        ├── App.vue                      # Root: Login vs AppLayout
        ├── assets/
        │   ├── main.css                 # Tailwind + custom styles
        │   ├── base.css
        │   └── logo.svg
        ├── router/index.ts              # Routes, auth guards
        ├── stores/auth.ts               # Pinia auth store
        ├── services/api.ts              # API wrappers
        ├── types/frappe.d.ts            # Window.csrf_token types
        ├── components/
        │   ├── AppLayout.vue            # Sidebar, nav, user, logout
        │   ├── ClockWidget.vue          # Clock in/out, timer
        │   └── __tests__/
        │       └── HelloWorld.spec.ts   # Sample test (may reference deleted component)
        └── views/
            ├── Login.vue                # Login form
            ├── DashboardView.vue        # Dashboard (Summary + Clock)
            ├── AttendanceView.vue       # ★ Detailed history, Stats, Holidays
            ├── LeaveView.vue            # Leave balance, apply, list
            └── PayrollView.vue          # Salary slips, download
```

---

## 4. Backend (Python/Frappe)

### 4.1 `arijentek_core/hooks.py`

**Purpose**: Central configuration for the app. Registers overrides, routes, and hooks.

| Key | Value | Meaning |
|-----|-------|---------|
| `override_whitelisted_methods` | `{"frappe.auth.login": "arijentek_core.auth.custom_login.login"}` | All login requests go to custom login |
| `before_request` | `["arijentek_core.security.validate_request"]` | Every request passes security checks |
| `doc_events` | Employee Checkin → `log_attendance_event`, `on_employee_checkin_insert` | Log event & Auto Attendance sync |
| `Attendance` → `log_attendance_event` | Log attendance events |
| `on_session_creation` | `arijentek_core.security.on_session_created` | After login, set redirect for employees |
| `website_route_rules` | `/employee-portal`, `/employee-portal/<path>` | Map URLs to employee-portal page |
| `role_home_page` | `{"Employee": "/employee-portal"}` | Employees land on portal |
| `get_website_user_home_page` | `arijentek_core.utils.get_employee_home_page` | Custom home page for website users |
| `boot_session` | `arijentek_core.utils.redirect_employee_on_boot` | Desk boot redirects employees to portal |
| `scheduler_events` | monthly → `run_monthly_payroll_automation` | Run payroll automation |
| `web_include_js` | `login_redirect.js` | Inject script on web pages |

---

### 4.2 `arijentek_core/api/__init__.py`

**Purpose**: Main HRMS API for the employee portal. All functions are `@frappe.whitelist()`.

#### Dashboard
| Function | Method | Purpose |
|----------|--------|---------|
| `get_dashboard_data()` | GET | Employee info, last punch, attendance summary (Present/Absent/Half Day) |
| `get_employee_info()` | GET | Current employee details |

#### Clock In/Out
| Function | Method | Purpose |
|----------|--------|---------|
| `get_today_checkin()` | GET | Today's clock_in/clock_out timestamps |
| `clock_in()` | POST | Create Employee Checkin with log_type=IN |
| `clock_out()` | POST | Create Employee Checkin with log_type=OUT |
| `punch()` | POST | **Unified**: toggles IN↔OUT based on last status |

#### Leave
| Function | Method | Purpose |
|----------|--------|---------|
| `get_leave_types()` | GET | All non-LWP leave types |
| `get_leave_balance()` | GET | Balance per leave type (uses HRMS `get_leave_balance_on`) |
| `apply_leave(leave_type, from_date, to_date, half_day, reason)` | POST | Create Leave Application |
| `get_leave_applications()` | GET | Employee's leave applications |
| `cancel_leave(leave_application)` | POST | Cancel Open leave |

#### Payroll
| Function | Method | Purpose |
|----------|--------|---------|
| `get_salary_slips()` | GET | Last 12 submitted Salary Slips |
| `download_payslip(name)` | GET | Return PDF (sets `frappe.local.response`) |

#### Other
| Function | Method | Purpose |
|----------|--------|---------|
| `get_attendance_summary()` | GET | Current month Present/Absent/Half Day counts |
| `get_reporting_info()` | GET | Reporting manager, leave approver |
| `create_issue(issue_type, description)` | POST | Create HD Ticket or Issue |
| `get_session_info()` | GET | **Guest allowed** – user, full_name, is_logged_in, has_desk_access, employee, department, designation |
| `get_current_employee()` | (internal) | Resolve Employee from `frappe.session.user` |

---

### 4.3 `arijentek_core/api/v1/auth.py`

**Purpose**: Auth-specific API (CSRF, login).

| Function | Methods | Guest | Purpose |
|----------|---------|-------|---------|
| `get_csrf_token()` | GET | Yes | Return CSRF token for session |
| `login(usr, pwd)` | POST | Yes | Authenticate, rate-limited. Supports Employee ID → resolves user_id. Returns `{message, user, full_name, csrf_token}` |

---

### 4.4 `arijentek_core/api/v1/attendance.py`

**Purpose**: Alternative/v1 attendance API. Used by `api.ts` for `getStatus`, `getRecords`. Main portal uses `arijentek_core.api.punch` and `get_today_checkin`.

| Function | Purpose |
|----------|---------|
| `punch(employee, timestamp)` | Rate-limited punch; accepts optional employee/timestamp |
| `get_status(employee)` | Last checkin log |
| `get_dashboard_data()` | Attendance summary, last punch (v1 format) |
| `get_attendance_records(month, year)` | Attendance records for month |

---

### 4.5 `arijentek_core/auth/custom_login.py`

**Purpose**: Overrides `frappe.auth.login`. Called when user submits login form.

- Resolves **Employee ID** → `user_id` if `usr` matches `Employee.name`
- Uses `LoginManager` for auth
- Returns `home_page` = `/employee-portal` for Employee role (no System Manager), else default Desk path
- Returns `csrf_token`, `sid`, `site_url` for SPA

---

### 4.6 `arijentek_core/utils.py`

**Purpose**: Redirect and home-page logic for employees.

| Function | Hook | Purpose |
|----------|------|---------|
| `_is_portal_employee(user)` | — | True if Employee role, not System Manager |
| `get_employee_home_page(user)` | `get_website_user_home_page` | Returns `/employee-portal` for portal employees |
| `redirect_employee_after_login(login_manager)` | `on_session_creation` (via security) | Sets `home_page`, `redirect_to` for employees |
| `redirect_employee_on_boot(bootinfo)` | `boot_session` | Overrides desk boot so employees see portal |

---

### 4.7 `arijentek_core/security.py`

**Purpose**: Request security and session hooks.

| Function | Hook / Caller | Purpose |
|----------|---------------|---------|
| `validate_request()` | `before_request` | Blocks bad User-Agents, suspicious patterns, enforces Content-Type |
| `log_attendance_event(doc, method)` | `doc_events` | Logs Employee Checkin/Attendance events |
| `on_session_created(login_manager)` | `on_session_creation` | Calls `redirect_employee_after_login` |

---

### 4.8 `arijentek_core/www/employee-portal.py`

**Purpose**: Controller for `/employee-portal` page.

- **Guest** → Redirect to `/login?redirect-to=/employee-portal`
- **Logged-in, no Employee** → Redirect to `/app` (desk)
- **Logged-in + Employee** → Renders `employee-portal.html`, sets `no_cache`, `show_sidebar=False`

---

### 4.9 `arijentek_core/www/employee-portal.html`

**Purpose**: HTML shell for the SPA in production.

- Loads `/assets/arijentek_core/frontend/assets/index.css`
- Injects `window.csrf_token` via Jinja
- Mounts SPA: `<script src="/assets/arijentek_core/frontend/assets/main.js">`
- `<div id="app">` is where Vue mounts

---

### 4.10 `arijentek_core/public/js/login_redirect.js`

**Purpose**: Patches Frappe's login handler when "No App" + `redirect_to` is returned. Forces redirect to `data.redirect_to` (e.g. `/employee-portal`).

---

### 4.11 `arijentek_core/attendance/auto_attendance.py`

**Purpose**: Automatically creates/updates Attendance records when check-ins occur.

| Function | Purpose |
|----------|---------|
| `on_employee_checkin_insert(doc, method)` | `doc_events` hook to trigger sync on insert |
| `sync_attendance_after_clock(employee, time)` | Immediate sync for API calls |

### 4.12 `arijentek_core/attendance/sync.py`

**Purpose**: Sync Employee Checkins → Attendance records.

| Function | Purpose |
|----------|---------|
| `sync_attendance_from_checkins(employee, date)` | Create/update Attendance from checkins |
| `create_or_update_attendance(...)` | Determine status (Present/Half Day/Absent), working hours |
| `sync_today_attendance()` | Whitelisted API to sync today |
| `sync_date_range(from_date, to_date, employee)` | Sync date range |
| `get_employee_attendance(employee, month, year)` | Attendance summary |

---

### 4.12 `arijentek_core/payroll/automation.py`

**Purpose**: Monthly payroll automation with attendance-based calculations.

| Function | Purpose |
|----------|---------|
| `generate_monthly_payroll(company, ...)` | Create payroll for eligible employees with attendance-based payment days |
| `run_monthly_payroll_automation(posting_date)` | Scheduler hook: generate + process payroll |
| `get_payroll_status(employee, month, year)` | Check if salary slip exists, with attendance summary |
| `get_payroll_preview_for_employee(...)` | Preview payroll calculation before generation |
| `recalculate_payroll_for_employee(...)` | Recalculate after attendance changes |
| `get_payroll_summary(company, month, year)` | Company-wide payroll statistics |

---

### 4.13 `arijentek_core/payroll/calculator.py`

**Purpose**: Core payroll calculation engine with attendance-based logic.

| Class/Function | Purpose |
|----------------|---------|
| `PayrollCalculator` | Main class for attendance-based payroll calculation |
| `load_data()` | Load salary structure, attendance, holidays |
| `calculate_earnings()` | Calculate earnings based on payment days |
| `calculate_deductions()` | Calculate all deductions (PT, PF, ESI, TDS) |
| `get_payment_days()` | Get payable days (working days - LOP) |
| `_calculate_statutory_deductions()` | Calculate PT, PF, ESI based on Indian rules |
| `calculate_employee_payroll(employee, start, end)` | API: Calculate payroll for employee |
| `get_payroll_preview(employee, month, year)` | API: Get payroll preview |
| `get_lop_summary(employee, start, end)` | Get LOP days breakdown |

**Key Features**:
- Attendance-based payment days calculation
- LOP (Loss of Pay) deduction from absences and LWP leave
- Professional Tax (PT) based on state-wise slabs
- Provident Fund (PF) at 12% of Basic
- ESI at 0.75% for eligible employees (gross ≤ ₹21,000)
- Formula-based salary component calculation

---

### 4.14 `arijentek_core/payroll/payslip_generator.py`

**Purpose**: Generate salary slips with detailed breakdown.

| Class/Function | Purpose |
|----------------|---------|
| `PayslipGenerator` | Generate salary slips for employees |
| `get_eligible_employees()` | Get employees with salary structure assignments |
| `generate_payslip(employee, submit)` | Generate single salary slip |
| `generate_all_payslips(employees, submit)` | Batch generation |
| `generate_payslip_for_employee(...)` | API: Generate for single employee |
| `generate_payroll_for_month(...)` | API: Generate for all eligible |
| `get_payslip_details(name)` | Get detailed payslip with attendance breakdown |
| `get_employee_payslips(employee, limit)` | List employee's salary slips |
| `download_payslip_pdf(name)` | Generate and download PDF |
| `get_payroll_dashboard_data(employee)` | YTD totals, latest slip, monthly breakdown |

---

### 4.15 `arijentek_core/payroll/setup.py`

**Purpose**: Setup default salary components for Indian payroll.

| Function | Purpose |
|----------|---------|
| `create_default_salary_components(company)` | Create earnings and deduction components |
| `create_default_salary_structure(company)` | Create standard salary structure |
| `setup_payroll_for_company(company)` | Complete payroll setup |
| `get_payroll_setup_status(company)` | Check setup completion status |

**Default Components Created**:
- **Earnings**: Basic, HRA, Conveyance, Medical, Special Allowance, DA, LTA, Bonus, Overtime
- **Deductions**: Professional Tax, Provident Fund, ESI, TDS, Voluntary PF, Health Insurance, Loan Recovery, LOP Deduction

---

## 5. Frontend (Vue.js/Vite)

### 5.1 Entry & Bootstrap

| File | Purpose |
|------|---------|
| `frontend/index.html` | Dev entry: loads `/src/main.ts` |
| `frontend/src/main.ts` | Creates Vue app, Pinia, Router; calls `authStore.init()`; mounts after init |
| `frontend/src/App.vue` | If `/login` → bare RouterView; else AppLayout + RouterView with transitions |

---

### 5.2 Auth Store (`stores/auth.ts`)

**Purpose**: Central auth state and actions.

| State | Type | Meaning |
|-------|------|---------|
| `user` | string | Username or "Guest" |
| `fullName` | string | Display name |
| `csrfToken` | string | Token for POST requests |
| `hasDeskAccess` | boolean | System User → can open Desk |
| `employee` | string \| null | Employee ID |
| `employeeName`, `department`, `designation` | string | Profile info |
| `ready` | boolean | `init()` finished |

| Action | Purpose |
|--------|---------|
| `init()` | Fetch CSRF token + session info; set state or fallback to cookie |
| `login(usr, pwd)` | POST to `arijentek_core.api.v1.auth.login`; update state on success |
| `logout()` | POST to `/api/method/logout`; reset; redirect to `/employee-portal#/login` |

---

### 5.3 API Service (`services/api.ts`)

**Purpose**: Wraps all backend API calls with CSRF and error handling.

| API | Methods | Backend Endpoint |
|-----|---------|------------------|
| `dashboardApi.getData()` | GET | `arijentek_core.api.get_dashboard_data` |
| `dashboardApi.getEmployeeInfo()` | GET | `arijentek_core.api.get_employee_info` |
| `dashboardApi.getReportingInfo()` | GET | `arijentek_core.api.get_reporting_info` |
| `attendanceApi.punch()` | POST | `arijentek_core.api.punch` |
| `attendanceApi.getTodayCheckin()` | GET | `arijentek_core.api.get_today_checkin` |
| `attendanceApi.getStatus()` | GET | `arijentek_core.api.v1.attendance.get_status` |
| `attendanceApi.getSummary()` | GET | `arijentek_core.api.get_attendance_summary` |
| `attendanceApi.getRecords(month, year)` | GET | `arijentek_core.api.v1.attendance.get_attendance_records` |
| `leaveApi.getTypes()` | GET | `arijentek_core.api.get_leave_types` |
| `leaveApi.getBalance()` | GET | `arijentek_core.api.get_leave_balance` |
| `leaveApi.getApplications()` | GET | `arijentek_core.api.get_leave_applications` |
| `leaveApi.apply(data)` | POST | `arijentek_core.api.apply_leave` |
| `leaveApi.cancel(name)` | POST | `arijentek_core.api.cancel_leave` |
| `payrollApi.getSlips()` | GET | `arijentek_core.api.get_salary_slips` |
| `payrollApi.getDownloadUrl(name)` | — | URL for PDF download |
| `payrollApi.generatePayroll(month, year)` | POST | `arijentek_core.api.generate_payroll` |
| `payrollApi.getSlipDetails(name)` | GET | `arijentek_core.api.get_payslip_details` |
| `payrollApi.getPreview(month, year)` | GET | `arijentek_core.api.get_payroll_preview` |
| `payrollApi.getDashboard()` | GET | `arijentek_core.api.get_payroll_dashboard` |
| `payrollApi.generateMyPayslip(month, year)` | POST | `arijentek_core.api.generate_my_payslip` |

**Implementation detail**: `request()` adds `X-Frappe-CSRF-Token` for non-GET, uses `credentials: 'include'` for cookies.

---

### 5.4 Router (`router/index.ts`)

| Route | Component | Meta |
|-------|------------|------|
| `/login` | Login.vue | guest: true |
| `/` | DashboardView.vue | requiresAuth: true |
| `/attendance` | AttendanceView.vue | requiresAuth: true |
| `/leave` | LeaveView.vue | requiresAuth: true |
| `/payroll` | PayrollView.vue | requiresAuth: true |
| `/:pathMatch(.*)*` | Redirect to `/` | — |

**Guard**: Before each route, if `!auth.ready` → allow (init pending). If `requiresAuth && !auth.isLoggedIn` → login. If `guest && isLoggedIn` → dashboard.

---

### 5.5 Views & Components

| File | Purpose |
|------|---------|
| **Login.vue** | Form (username, password); calls `authStore.login`; on success `router.push('/')` |
| **DashboardView.vue** | Greeting, Stats summary, ClockWidget, Quick actions |
| **AttendanceView.vue** | Monthly selector, Attendance Stats (Present/Absent/Half Day), Holiday list, Detailed record table |
| **LeaveView.vue** | Reporting/approver info, leave balance cards, apply form (modal), applications table |
| **PayrollView.vue** | Summary cards (avg net, YTD gross/net), salary slip list, download buttons |
| **AppLayout.vue** | Sidebar (desktop), bottom nav (mobile), user info, "Open Desk" (if hasDeskAccess), logout. Nav items: Dashboard, Attendance, Leave, Payroll. |
| **ClockWidget.vue** | SVG progress ring (8h), toggle Clock In/Out, timer display. Handles **Day Complete** state (both IN/OUT present). |

---

### 5.6 Styling (`assets/main.css`)

- Tailwind base/components/utilities
- CSS vars: `--accent`, `--surface`, `--bg`
- Custom classes: `.glass-card`, `.btn-accent`, `.input-dark`, `.badge-*`
- Page/modal transitions, clock ring animation

---

## 6. Backend–Frontend Communication

### Protocol

1. **Base URL**: `/api/method/<module>.<function>`
2. **Cookies**: Sent with `credentials: 'include'` (session cookie).
3. **CSRF**: For POST/PUT/DELETE, header `X-Frappe-CSRF-Token` required. Token from `get_csrf_token` or `login` response.
4. **Response**: JSON `{ message: <result> }` or `{ exc_type, exception, _server_messages }` on error.

### Sequence: App Startup

```
1. main.ts runs
2. authStore.init()
   ├─ GET /api/method/arijentek_core.api.v1.auth.get_csrf_token  → csrfToken
   └─ GET /api/method/arijentek_core.api.get_session_info        → user, employee, hasDeskAccess, etc.
3. ready = true
4. app.mount('#app')
5. Router renders; guard checks auth
```

### Sequence: Login

```
1. User submits Login.vue form
2. authStore.login(usr, pwd)
   └─ POST /api/method/arijentek_core.api.v1.auth.login
      Body: { usr, pwd }
      Header: X-Frappe-CSRF-Token
3. Response: { message: "Logged In", user, full_name, csrf_token }
4. authStore updates state; router.push('/')
```

### Sequence: Clock In

```
1. User clicks ClockWidget button
2. attendanceApi.punch()
   └─ POST /api/method/arijentek_core.api.punch
      Header: X-Frappe-CSRF-Token
      (no body)
3. Response: { status: "success", log_type: "IN", time: "..." }
4. ClockWidget sets isClockedIn, clockInTime, starts timer
```

---

## 7. Data Flow & Request Lifecycle

### Production vs Development

| Mode | SPA URL | API Proxy | SPA Served By |
|------|---------|-----------|----------------|
| **Production** | `https://site/employee-portal` | N/A | Frappe serves built assets from `public/frontend/` |
| **Development** | `http://localhost:3000/#/` | Vite proxies `/api`, `/assets`, `/files` → `127.0.0.1:8000` with Host: arijentek.localhost | Vite dev server |

### Build Output

`npm run build` → output in `arijentek_core/public/frontend/`:

- `assets/main.js` (entry + chunks)
- `assets/index.css`
- `assets/*.js` (lazy-loaded views)
- `index.html` (if generated)

Frappe serves these at `/assets/arijentek_core/frontend/`.

---

## 8. Function Reference Map

Quick lookup: where is function X?

| Frontend Call | Backend Function |
|---------------|------------------|
| `authStore.init` → fetchCsrfToken | `arijentek_core.api.v1.auth.get_csrf_token` |
| `authStore.init` → fetchSessionInfo | `arijentek_core.api.get_session_info` |
| `authStore.login` | `arijentek_core.api.v1.auth.login` |
| `authStore.logout` | `frappe` `/api/method/logout` |
| `dashboardApi.getData` | `arijentek_core.api.get_dashboard_data` |
| `dashboardApi.getReportingInfo` | `arijentek_core.api.get_reporting_info` |
| `attendanceApi.punch` | `arijentek_core.api.punch` |
| `attendanceApi.getTodayCheckin` | `arijentek_core.api.get_today_checkin` |
| `leaveApi.getTypes` | `arijentek_core.api.get_leave_types` |
| `leaveApi.getBalance` | `arijentek_core.api.get_leave_balance` |
| `leaveApi.getApplications` | `arijentek_core.api.get_leave_applications` |
| `leaveApi.apply` | `arijentek_core.api.apply_leave` |
| `leaveApi.cancel` | `arijentek_core.api.cancel_leave` |
| `payrollApi.getSlips` | `arijentek_core.api.get_salary_slips` |
| `payrollApi.getDownloadUrl` | URL to `arijentek_core.api.download_payslip` |

---

## 9. Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python package, Ruff lint/format |
| `frontend/package.json` | npm deps, scripts (dev, build, lint) |
| `frontend/vite.config.ts` | Vite: base path, build outDir, proxy to bench |
| `frontend/tailwind.config.js` | Tailwind theme, fonts |
| `frontend/tsconfig*.json` | TypeScript configs |
| `.github/workflows/ci.yml` | CI: bench init, install app, run tests |
| `.github/workflows/linter.yml` | Lint workflow |

---

## 10. Development & Deployment

### Local Development

```bash
# Terminal 1: Frappe
cd frappe-bench && bench start

# Terminal 2: Vue dev server
cd apps/arijentek_core/frontend && npm run dev
```

- Frontend: http://localhost:3000
- API: Proxied to http://127.0.0.1:8000 (Host: arijentek.localhost)
- Add `127.0.0.1 arijentek.localhost` to `/etc/hosts` if needed

### Production Build

```bash
cd apps/arijentek_core/frontend && npm run build-only
```

Output → `arijentek_core/public/frontend/`. Frappe serves at `/assets/arijentek_core/frontend/`.

### Access URLs

| User Type | After Login |
|-----------|-------------|
| Guest | Redirect to `/login?redirect-to=/employee-portal` |
| Employee (no System Manager) | `/employee-portal` |
| System User (with Employee) | `/employee-portal` + "Open Desk" button |
| System User (no Employee) | `/app` (Desk) |

---

## Quick Reference: File → Purpose

| Path | One-line purpose |
|------|------------------|
| `hooks.py` | App config, overrides, routes, hooks |
| `api/__init__.py` | Main HRMS API for portal |
| `api/v1/auth.py` | CSRF, login |
| `api/v1/attendance.py` | V1 attendance API |
| `auth/custom_login.py` | Override frappe login, Employee ID support |
| `utils.py` | Portal redirect helpers |
| `security.py` | Request validation, session hooks |
| `www/employee-portal.py` | Controller: redirect guests/non-employees |
| `www/employee-portal.html` | SPA HTML shell |
| `public/js/login_redirect.js` | Patch login handler for redirect |
| `attendance/sync.py` | Checkin → Attendance sync |
| `payroll/automation.py` | Monthly payroll |
| `frontend/src/main.ts` | Bootstrap Vue app |
| `frontend/src/stores/auth.ts` | Auth state and init/login/logout |
| `frontend/src/services/api.ts` | API wrappers with CSRF |
| `frontend/src/router/index.ts` | Routes and auth guards |
| `frontend/src/App.vue` | Root layout switch |
| `frontend/src/views/*.vue` | Login, Dashboard, Leave, Payroll |
| `frontend/src/components/AppLayout.vue` | Sidebar, nav, user |
| `frontend/src/components/ClockWidget.vue` | Clock in/out, timer |

---

*Document generated for Arijentek Core. For questions, refer to `CONTEXT.md` or the code comments.*
