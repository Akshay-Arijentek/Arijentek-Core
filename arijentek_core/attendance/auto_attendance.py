"""
Auto Attendance Module
======================

Automatically creates/updates Attendance records when Employee Checkin
records are created (clock in / clock out from the portal).

Flow:
1. Employee clocks in  → Employee Checkin (IN) is created
2. Employee clocks out → Employee Checkin (OUT) is created
3. On each checkin insert, this module is triggered via doc_events hook
4. It finds all checkins for that employee on that date and creates/updates
   the Attendance record accordingly.

The attendance is marked as:
- "Present" on clock-in (with 0 working hours initially)
- Updated with working_hours and out_time on clock-out
- Status is re-evaluated based on shift settings (Late, Half Day, etc.)
"""

import frappe
from frappe.utils import getdate, add_days


def on_employee_checkin_insert(doc, method):
	"""Hook called after Employee Checkin is inserted.

	Automatically creates or updates the Attendance record for the
	employee on the checkin date.
	"""
	if not doc.employee or not doc.time:
		return

	try:
		checkin_date = getdate(doc.time)
		_sync_attendance_for_employee(doc.employee, checkin_date)
	except Exception:
		# Log the error but don't block the checkin from being saved
		frappe.log_error(
			frappe.get_traceback(),
			f"Auto Attendance Error for {doc.employee}",
		)


def _sync_attendance_for_employee(employee, date):
	"""Fetch all checkins for the employee on the given date and create/update attendance.

	Re-uses the existing sync logic from arijentek_core.attendance.sync.
	"""
	from arijentek_core.attendance.sync import create_or_update_attendance

	next_date = add_days(date, 1)

	checkins = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ["between", [date, next_date]],
		},
		fields=["name", "employee", "time", "log_type", "device_id"],
		order_by="time",
	)

	if not checkins:
		return

	create_or_update_attendance(employee, date, checkins)


def sync_attendance_after_clock(employee, checkin_time):
	"""Convenience function to trigger attendance sync after clock in/out.

	Called directly from the clock_in / clock_out / punch API endpoints
	as an immediate sync (in addition to the doc_events hook which serves
	as a safety net).

	Args:
		employee: Employee ID
		checkin_time: datetime of the checkin
	"""
	try:
		checkin_date = getdate(checkin_time)
		_sync_attendance_for_employee(employee, checkin_date)
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			f"Auto Attendance Sync Error for {employee}",
		)
