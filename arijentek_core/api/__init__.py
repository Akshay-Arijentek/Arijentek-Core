import frappe
from frappe import _
from frappe.utils import nowdate, now_datetime, getdate, get_first_day, get_last_day, flt
from datetime import datetime, timedelta

# ============ DASHBOARD ============


@frappe.whitelist()
def get_dashboard_data():
	"""Get all dashboard data in one call"""
	employee = get_current_employee()
	if not employee:
		return {"error": "Employee not found"}

	today = nowdate()
	current_month = getdate(today).strftime("%B")
	year = getdate(today).year

	# Get last checkin
	last_checkin = frappe.db.sql(
		"""
        SELECT name, time, log_type
        FROM `tabEmployee Checkin`
        WHERE employee = %s AND DATE(time) = %s
        ORDER BY time DESC
        LIMIT 1
    """,
		(employee, today),
		as_dict=True,
	)

	last_punch = None
	if last_checkin:
		last_punch = {
			"name": last_checkin[0].name,
			"time": last_checkin[0].time.isoformat()
			if hasattr(last_checkin[0].time, "isoformat")
			else str(last_checkin[0].time),
			"log_type": last_checkin[0].log_type,
		}

	# Get attendance summary
	first_day = get_first_day(today)
	last_day = get_last_day(today)

	summary = frappe.db.sql(
		"""
        SELECT status, COUNT(*) as count
        FROM `tabAttendance`
        WHERE employee = %s
        AND attendance_date BETWEEN %s AND %s
        AND docstatus = 1
        GROUP BY status
    """,
		(employee, first_day, last_day),
		as_dict=True,
	)

	attendance_summary = {"Present": 0, "Absent": 0, "Half Day": 0, "On Leave": 0}
	for row in summary:
		if row.status in attendance_summary:
			attendance_summary[row.status] = row.count

	# Get leave-type breakdown for "On Leave" days
	on_leave_types = frappe.db.sql(
		"""
		SELECT leave_type, COUNT(*) as count
		FROM `tabAttendance`
		WHERE employee = %s
		AND attendance_date BETWEEN %s AND %s
		AND docstatus = 1
		AND status = 'On Leave'
		GROUP BY leave_type
		""",
		(employee, first_day, last_day),
		as_dict=True,
	)
	leave_type_breakdown = {r.leave_type: r.count for r in on_leave_types}

	return {
		"employee": employee,
		"employee_name": frappe.db.get_value("Employee", employee, "employee_name"),
		"department": frappe.db.get_value("Employee", employee, "department"),
		"designation": frappe.db.get_value("Employee", employee, "designation"),
		"current_month": current_month,
		"year": year,
		"last_punch": last_punch,
		"attendance_summary": attendance_summary,
		"leave_type_breakdown": leave_type_breakdown,
	}


# ============ EMPLOYEE INFO ============


@frappe.whitelist()
def get_employee_info():
	"""Get current employee details"""
	user = frappe.session.user
	employee = frappe.db.get_value(
		"Employee", {"user_id": user}, ["name", "employee_name", "department", "designation"], as_dict=True
	)

	if not employee:
		return {"error": "No employee record found for this user"}

	return {
		"employee_id": employee.name,
		"employee_name": employee.employee_name,
		"department": employee.department,
		"designation": employee.designation,
	}


# ============ CLOCK IN/OUT ============

# Maximum shift duration in hours — auto clock-out after this
MAX_SHIFT_HOURS = 12


@frappe.whitelist()
def get_today_checkin():
	"""Get today's check-in status.

	Returns:
	  clock_in  – ISO timestamp of the single IN log (or None)
	  clock_out – ISO timestamp of the single OUT log (or None)
	  completed – True if the employee has already clocked in AND out today
	"""
	employee = get_current_employee()
	if not employee:
		return {"error": "Employee not found"}

	today = nowdate()

	checkins = frappe.db.sql(
		"""
		SELECT time, log_type
		FROM `tabEmployee Checkin`
		WHERE employee = %s AND DATE(time) = %s
		ORDER BY time ASC
		""",
		(employee, today),
		as_dict=True,
	)

	if not checkins:
		return {"clock_in": None, "clock_out": None, "completed": False}

	in_log = None
	out_log = None
	for c in checkins:
		if c.log_type == "IN" and not in_log:
			in_log = c
		elif c.log_type == "OUT" and not out_log:
			out_log = c

	completed = bool(in_log and out_log)

	return {
		"clock_in": in_log.time.isoformat() if in_log and hasattr(in_log.time, "isoformat") else (str(in_log.time) if in_log else None),
		"clock_out": out_log.time.isoformat() if out_log and hasattr(out_log.time, "isoformat") else (str(out_log.time) if out_log else None),
		"completed": completed,
	}


@frappe.whitelist()
def clock_in():
	"""Record clock in (once per day only) and auto-mark attendance"""
	employee = get_current_employee()
	if not employee:
		return {"success": False, "error": "Employee not found"}

	today = nowdate()

	# Check if already clocked in today
	existing_in = frappe.db.exists(
		"Employee Checkin",
		{"employee": employee, "log_type": "IN", "time": ["between", [today, f"{today} 23:59:59"]]},
	)
	if existing_in:
		return {"success": False, "error": "You have already clocked in today"}

	try:
		checkin = frappe.get_doc(
			{"doctype": "Employee Checkin", "employee": employee, "time": now_datetime(), "log_type": "IN"}
		)
		checkin.insert(ignore_permissions=True)
		frappe.db.commit()

		# Auto-sync attendance after clock in
		from arijentek_core.attendance.auto_attendance import sync_attendance_after_clock
		sync_attendance_after_clock(employee, checkin.time)

		return {"success": True, "time": checkin.time.isoformat()}
	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def clock_out():
	"""Record clock out (must have clocked in first, once per day) and auto-mark attendance"""
	employee = get_current_employee()
	if not employee:
		return {"success": False, "error": "Employee not found"}

	today = nowdate()

	# Must have clocked in today
	in_checkin = frappe.db.sql(
		"""
		SELECT time FROM `tabEmployee Checkin`
		WHERE employee = %s AND DATE(time) = %s AND log_type = 'IN'
		ORDER BY time ASC LIMIT 1
		""",
		(employee, today),
		as_dict=True,
	)
	if not in_checkin:
		return {"success": False, "error": "You must clock in before clocking out"}

	# Check if already clocked out today
	existing_out = frappe.db.exists(
		"Employee Checkin",
		{"employee": employee, "log_type": "OUT", "time": ["between", [today, f"{today} 23:59:59"]]},
	)
	if existing_out:
		return {"success": False, "error": "You have already clocked out today"}

	# Enforce max shift duration
	clock_in_time = in_checkin[0].time
	now = now_datetime()
	hours_worked = (now - clock_in_time).total_seconds() / 3600
	if hours_worked > MAX_SHIFT_HOURS:
		return {"success": False, "error": f"Shift exceeded {MAX_SHIFT_HOURS} hours. Please contact HR."}

	try:
		checkin = frappe.get_doc(
			{"doctype": "Employee Checkin", "employee": employee, "time": now, "log_type": "OUT"}
		)
		checkin.insert(ignore_permissions=True)
		frappe.db.commit()

		# Auto-sync attendance after clock out
		from arijentek_core.attendance.auto_attendance import sync_attendance_after_clock
		sync_attendance_after_clock(employee, checkin.time)

		return {"success": True, "time": checkin.time.isoformat()}
	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def punch():
	"""Unified punch endpoint — one clock-in and one clock-out per day.

	Rules:
	  - First punch of the day → Clock IN
	  - Second punch (after IN) → Clock OUT
	  - No further punches allowed after both IN and OUT exist
	  - Cannot clock out without clocking in first
	  - Max shift duration: MAX_SHIFT_HOURS (12 hours)
	"""
	employee = get_current_employee()
	if not employee:
		return {"status": "error", "error": "Employee not found"}

	today = nowdate()

	# Get today's checkins
	today_checkins = frappe.db.sql(
		"""
		SELECT time, log_type FROM `tabEmployee Checkin`
		WHERE employee = %s AND DATE(time) = %s
		ORDER BY time ASC
		""",
		(employee, today),
		as_dict=True,
	)

	has_in = any(c.log_type == "IN" for c in today_checkins)
	has_out = any(c.log_type == "OUT" for c in today_checkins)

	# Already completed for the day
	if has_in and has_out:
		return {"status": "error", "error": "You have already clocked in and out today"}

	# Determine log type
	if not has_in:
		log_type = "IN"
	elif has_in and not has_out:
		log_type = "OUT"
		# Enforce max shift duration
		in_time = next(c.time for c in today_checkins if c.log_type == "IN")
		now = now_datetime()
		hours_worked = (now - in_time).total_seconds() / 3600
		if hours_worked > MAX_SHIFT_HOURS:
			return {"status": "error", "error": f"Shift exceeded {MAX_SHIFT_HOURS} hours. Please contact HR."}
	else:
		return {"status": "error", "error": "Invalid state"}

	try:
		checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"time": now_datetime(),
				"log_type": log_type,
			}
		)
		checkin.insert(ignore_permissions=True)
		frappe.db.commit()

		# Auto-sync attendance after punch
		from arijentek_core.attendance.auto_attendance import sync_attendance_after_clock
		sync_attendance_after_clock(employee, checkin.time)

		return {
			"status": "success",
			"log_type": log_type,
			"time": checkin.time.isoformat() if hasattr(checkin.time, "isoformat") else str(checkin.time),
		}
	except Exception as e:
		return {"status": "error", "error": str(e)}


# ============ LEAVE MANAGEMENT ============


@frappe.whitelist()
def get_leave_types():
	"""Get available leave types from ERPNext (non-LWP leave types)"""
	return frappe.get_all("Leave Type", filters={"is_lwp": 0}, pluck="name")


@frappe.whitelist()
def get_holidays(from_date=None, to_date=None, exclude_weekly_off=None):
	"""Get holidays for the current employee's Holiday List from ERPNext.

	Args:
		from_date: Start date (defaults to first day of current month)
		to_date: End date (defaults to last day of current month)
		exclude_weekly_off: If "1" or True, exclude Saturday/Sunday weekly-off entries
			and only return gazetted/public holidays (Jan 1, Jan 26, May 1, etc.)

	Returns list of {holiday_date, description, weekly_off} for the given date range.
	"""
	employee = get_current_employee()
	if not employee:
		return []

	try:
		from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
	except ImportError:
		return []

	holiday_list = get_holiday_list_for_employee(employee, raise_exception=False)
	if not holiday_list:
		return []

	today = nowdate()
	from_date = from_date or get_first_day(today)
	to_date = to_date or get_last_day(today)

	filters = {
		"parent": holiday_list,
		"holiday_date": ["between", [from_date, to_date]],
	}

	# Exclude weekly off (Sat/Sun) if requested — show only gazetted holidays
	if exclude_weekly_off in (1, "1", True, "true", "True"):
		filters["weekly_off"] = 0

	holidays = frappe.get_all(
		"Holiday",
		filters=filters,
		fields=["holiday_date", "description", "weekly_off"],
		order_by="holiday_date",
	)

	from frappe.utils import strip_html

	for h in holidays:
		dt = h.get("holiday_date")
		if hasattr(dt, "strftime"):
			h["holiday_date"] = dt.strftime("%Y-%m-%d")
		desc = h.get("description") or ""
		h["description"] = strip_html(desc).strip()

	return holidays


# Standard leave balance categories (order for display)
LEAVE_BALANCE_CATEGORIES = [
	"Casual Leave",
	"Sick Leave",
	"Earned Leave",
	"Regional Holidays",
]


def _get_earned_leave_balance(employee, today):
	"""Calculate earned leave: 1 day per 20 working days since date of joining, minus used."""
	date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
	if not date_of_joining:
		return 0

	date_of_joining = getdate(date_of_joining)
	today_d = getdate(today)
	if date_of_joining > today_d:
		return 0

	# Count working days (Present + Half Day) from Attendance
	working_days_result = frappe.db.sql(
		"""
		SELECT COUNT(DISTINCT attendance_date) as days
		FROM `tabAttendance`
		WHERE employee = %s
		AND docstatus = 1
		AND attendance_date BETWEEN %s AND %s
		AND status IN ('Present', 'Half Day')
		""",
		(employee, date_of_joining, today_d),
		as_dict=True,
	)
	working_days = flt(working_days_result[0].days) if working_days_result else 0

	# Earned = floor(working_days / 20)
	earned = int(working_days // 20)

	# Minus earned leave already taken (Approved Leave Applications)
	used_result = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(total_leave_days), 0) as used
		FROM `tabLeave Application`
		WHERE employee = %s
		AND leave_type = 'Earned Leave'
		AND status = 'Approved'
		AND docstatus = 1
		""",
		(employee,),
		as_dict=True,
	)
	used = flt(used_result[0].used) if used_result else 0

	balance = earned - used
	return max(0, balance)


@frappe.whitelist()
def get_leave_balance():
	"""Get leave balance for standard categories: Casual Leave, Sick Leave, Earned Leave, Regional Holidays, plus Total."""
	employee = get_current_employee()
	if not employee:
		return []

	from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

	today = nowdate()
	balance_map = {}

	# Get balances from ERPNext for leave types that exist
	for leave_type in LEAVE_BALANCE_CATEGORIES:
		if leave_type == "Earned Leave":
			balance_map[leave_type] = _get_earned_leave_balance(employee, today)
		else:
			if not frappe.db.exists("Leave Type", leave_type):
				balance_map[leave_type] = 0
			else:
				try:
					balance_map[leave_type] = get_leave_balance_on(employee, leave_type, today)
				except Exception:
					balance_map[leave_type] = 0

	# Build result in fixed order (Total computed on frontend)
	return [{"leave_type": k, "balance": flt(v)} for k, v in balance_map.items()]


@frappe.whitelist()
def apply_leave(leave_type, from_date, to_date, half_day=0, reason=""):
	"""Submit leave application.

	Auto-creates a Leave Allocation for the calendar year if one does
	not already exist, so employees can apply without HR manually
	setting up allocations first.
	"""
	employee = get_current_employee()
	if not employee:
		return {"success": False, "error": "Employee not found"}

	# Ensure a submitted Leave Allocation covers the requested dates
	_ensure_leave_allocation(employee, leave_type, from_date, to_date)

	try:
		leave = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"leave_type": leave_type,
				"from_date": from_date,
				"to_date": to_date,
				"half_day": half_day,
				"description": reason,
				"status": "Open",
			}
		)
		leave.insert(ignore_permissions=True)
		frappe.db.commit()

		return {"success": True, "name": leave.name}
	except Exception as e:
		msg = str(e)
		# Strip noisy traceback bits
		if "ValidationError" in msg and ":" in msg:
			msg = msg.split(":")[-1].strip()
		return {"success": False, "error": msg}


@frappe.whitelist()
def get_leave_applications():
	"""Get employee's leave applications"""
	employee = get_current_employee()
	if not employee:
		return []

	apps = frappe.get_all(
		"Leave Application",
		filters={"employee": employee},
		fields=["name", "leave_type", "from_date", "to_date", "total_leave_days", "status"],
		order_by="creation desc",
		limit=20,
	)

	# Convert to plain dicts with string dates (handle Frappe Document objects)
	result = []
	for app in apps:
		app_dict = dict(app) if hasattr(app, '__dict__') else app
		# Convert date objects to ISO strings
		if hasattr(app_dict.get('from_date'), 'isoformat'):
			app_dict['from_date'] = app_dict['from_date'].isoformat()
		if hasattr(app_dict.get('to_date'), 'isoformat'):
			app_dict['to_date'] = app_dict['to_date'].isoformat()
		result.append(app_dict)

	return result


@frappe.whitelist()
def cancel_leave(leave_application):
	"""Cancel a pending leave application"""
	employee = get_current_employee()
	if not employee:
		return {"success": False, "error": "Employee not found"}

	try:
		leave = frappe.get_doc("Leave Application", leave_application)

		if leave.employee != employee:
			return {"success": False, "error": "Not authorized"}

		if leave.status != "Open":
			return {"success": False, "error": "Cannot cancel - leave already processed"}

		leave.status = "Cancelled"
		leave.save(ignore_permissions=True)
		frappe.db.commit()

		return {"success": True}
	except Exception as e:
		return {"success": False, "error": str(e)}


# ============ PAYSLIPS ============


@frappe.whitelist()
def get_salary_slips():
	"""Get employee's salary slips"""
	employee = get_current_employee()
	if not employee:
		return []

	slips = frappe.get_all(
		"Salary Slip",
		filters={"employee": employee, "docstatus": 1},
		fields=["name", "start_date", "end_date", "net_pay", "gross_pay"],
		order_by="start_date desc",
		limit=12,
	)

	for slip in slips:
		slip["month"] = getdate(slip["start_date"]).strftime("%B")
		slip["year"] = getdate(slip["start_date"]).year

	return slips


@frappe.whitelist(allow_guest=False)
def download_payslip(name):
	"""Download salary slip PDF"""
	employee = get_current_employee()
	slip = frappe.get_doc("Salary Slip", name)

	if slip.employee != employee:
		frappe.throw(_("Not authorized"))

	# Generate and return PDF
	from frappe.utils.pdf import get_pdf

	html = frappe.get_print("Salary Slip", name)
	frappe.local.response.filename = f"Payslip_{slip.start_date}.pdf"
	frappe.local.response.filecontent = get_pdf(html)
	frappe.local.response.type = "pdf"


@frappe.whitelist()
def generate_payroll(month=None, year=None):
	"""Generate salary slips for a month. Requires HR Manager or Payroll Entry create permission.

	month: 1-12, year: e.g. 2026. Defaults to previous month.
	"""
	user = frappe.session.user
	if not (frappe.has_permission("Payroll Entry", "create") or "HR Manager" in frappe.get_roles(user)):
		return {"success": False, "error": "Not authorized to generate payroll"}

	from frappe.utils import getdate, get_first_day, get_last_day
	from arijentek_core.payroll.automation import generate_monthly_payroll, process_payroll_entry

	today = getdate()
	year = int(year) if year else today.year
	month = int(month) if month else (today.month - 1 if today.month > 1 else 12)
	if month < 1:
		month = 12
		year -= 1

	posting_date = getdate(f"{year}-{month:02d}-01")
	posting_date = get_last_day(posting_date)

	try:
		payroll_entry = generate_monthly_payroll(posting_date=posting_date, dry_run=False)
		if not payroll_entry:
			return {"success": False, "error": "No eligible employees found for payroll"}

		process_payroll_entry(payroll_entry.name, submit_salary_slips=True)

		return {
			"success": True,
			"payroll_entry": payroll_entry.name,
			"message": f"Payroll generated for {posting_date.strftime('%B %Y')}",
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Payroll Generation Error")
		return {"success": False, "error": str(e)}


# ============ ATTENDANCE SUMMARY & RECORDS ============


@frappe.whitelist()
def get_attendance_summary():
	"""Get attendance summary for current month"""
	employee = get_current_employee()
	if not employee:
		return {}

	today = getdate(nowdate())
	first_day = get_first_day(today)
	last_day = get_last_day(today)

	summary = frappe.db.sql(
		"""
        SELECT status, COUNT(*) as count
        FROM `tabAttendance`
        WHERE employee = %s
        AND attendance_date BETWEEN %s AND %s
        AND docstatus = 1
        GROUP BY status
    """,
		(employee, first_day, last_day),
		as_dict=True,
	)

	result = {"present": 0, "absent": 0, "half_day": 0}
	for row in summary:
		if row.status == "Present":
			result["present"] = row.count
		elif row.status == "Absent":
			result["absent"] = row.count
		elif row.status == "Half Day":
			result["half_day"] = row.count

	return result


@frappe.whitelist()
def get_attendance_records(month=None, year=None):
	"""Get attendance records for a given month/year (defaults to current month).

	Returns list of records with date, status, working_hours, in_time, out_time
	plus a summary count.
	"""
	import calendar

	employee = get_current_employee()
	if not employee:
		return {"records": [], "summary": {}}

	today = getdate(nowdate())
	month = int(month) if month else today.month
	year = int(year) if year else today.year

	last_day = calendar.monthrange(year, month)[1]
	start_date = getdate(f"{year}-{month:02d}-01")
	end_date = getdate(f"{year}-{month:02d}-{last_day}")

	records = frappe.db.sql(
		"""
		SELECT attendance_date, status, working_hours, in_time, out_time
		FROM `tabAttendance`
		WHERE employee = %s
			AND attendance_date BETWEEN %s AND %s
			AND docstatus = 1
		ORDER BY attendance_date
		""",
		(employee, start_date, end_date),
		as_dict=True,
	)

	summary = {"Present": 0, "Absent": 0, "Half Day": 0, "On Leave": 0}
	result_records = []
	for r in records:
		if r.status in summary:
			summary[r.status] += 1
		result_records.append({
			"date": str(r.attendance_date),
			"status": r.status,
			"working_hours": round(flt(r.working_hours), 2),
			"in_time": str(r.in_time) if r.in_time else None,
			"out_time": str(r.out_time) if r.out_time else None,
		})

	return {
		"records": result_records,
		"summary": summary,
		"period": {"start": str(start_date), "end": str(end_date), "month": month, "year": year},
	}


# ============ ISSUES ============


@frappe.whitelist()
def create_issue(issue_type, description):
	"""Create HR issue/ticket"""
	employee = get_current_employee()
	if not employee:
		return {"success": False, "error": "Employee not found"}

	try:
		# Using HD Ticket (Frappe Helpdesk) or Issue
		doctype = "HD Ticket" if frappe.db.exists("DocType", "HD Ticket") else "Issue"

		doc = frappe.get_doc(
			{
				"doctype": doctype,
				"subject": f"[{issue_type}] Issue from Employee Portal",
				"description": description,
				"raised_by": frappe.session.user,
			}
		)
		doc.insert(ignore_permissions=True)
		frappe.db.commit()

		return {"success": True, "ticket": doc.name}
	except Exception as e:
		return {"success": False, "error": str(e)}


# ============ REPORTING / MANAGER ============


@frappe.whitelist()
def get_reporting_info():
	"""Get reporting manager and leave approver details for the current employee."""
	employee = get_current_employee()
	if not employee:
		return {}

	emp = frappe.get_doc("Employee", employee)
	result = {}

	if emp.reports_to:
		try:
			manager = frappe.get_doc("Employee", emp.reports_to)
			result["reporting_manager"] = {
				"name": manager.name,
				"employee_name": manager.employee_name,
				"designation": manager.designation or "",
				"department": manager.department or "",
				"user_id": manager.user_id or "",
			}
		except Exception:
			pass

	if emp.leave_approver:
		try:
			approver_emp = frappe.db.get_value(
				"Employee",
				{"user_id": emp.leave_approver},
				["name", "employee_name", "designation"],
				as_dict=True,
			)
			result["leave_approver"] = {
				"user_id": emp.leave_approver,
				"employee_name": approver_emp.employee_name if approver_emp else emp.leave_approver,
				"designation": approver_emp.designation if approver_emp else "",
			}
		except Exception:
			pass

	return result


# ============ SESSION ============


@frappe.whitelist(allow_guest=True)
def get_session_info():
	"""Return session information for the current user.

	Called by the Vue SPA on startup to determine:
	- Whether the user is logged in
	- Their full name, employee ID, designation, department
	- Whether they have desk access (System User)
	"""
	user = frappe.session.user

	if user == "Guest":
		return {
			"user": "Guest",
			"is_logged_in": False,
			"has_desk_access": False,
		}

	employee = get_current_employee()
	emp_data = {}
	if employee:
		emp_data = frappe.db.get_value(
			"Employee",
			employee,
			["employee_name", "department", "designation"],
			as_dict=True,
		) or {}

	user_type = frappe.db.get_value("User", user, "user_type") or ""
	has_payroll_permission = frappe.has_permission("Payroll Entry", "create") or "HR Manager" in frappe.get_roles(user)

	return {
		"user": user,
		"full_name": frappe.utils.get_fullname(user),
		"is_logged_in": True,
		"has_desk_access": user_type == "System User",
		"has_payroll_permission": bool(has_payroll_permission),
		"employee": employee,
		"employee_name": emp_data.get("employee_name", ""),
		"department": emp_data.get("department", ""),
		"designation": emp_data.get("designation", ""),
	}


# ============ LEAVE ALLOCATION HELPER ============


def _ensure_leave_allocation(employee, leave_type, from_date, to_date):
	"""Create a Leave Allocation for the calendar year if none covers the dates.

	This lets employees apply for leave even if HR hasn't manually created
	allocations.  The allocation uses the Leave Type's ``max_leaves_allowed``
	(falls back to 12 days per year).
	"""
	# Already covered?
	covered = frappe.db.sql(
		"""
		SELECT name FROM `tabLeave Allocation`
		WHERE employee = %s AND leave_type = %s
		AND from_date <= %s AND to_date >= %s
		AND docstatus = 1
		LIMIT 1
		""",
		(employee, leave_type, from_date, to_date),
	)
	if covered:
		return

	year = getdate(from_date).year
	lt_doc = frappe.get_doc("Leave Type", leave_type)
	max_leaves = lt_doc.max_leaves_allowed or 12

	try:
		alloc = frappe.get_doc(
			{
				"doctype": "Leave Allocation",
				"employee": employee,
				"leave_type": leave_type,
				"from_date": f"{year}-01-01",
				"to_date": f"{year}-12-31",
				"new_leaves_allocated": max_leaves,
			}
		)
		alloc.insert(ignore_permissions=True)
		alloc.submit()
		frappe.db.commit()
	except Exception:
		# Might fail if an overlapping allocation already exists — that's OK,
		# the Leave Application validation will catch it with a clearer message.
		frappe.db.rollback()


# ============ HELPERS ============


def get_current_employee():
	"""Get employee ID for current user"""
	return frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
