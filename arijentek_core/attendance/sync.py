import frappe
from frappe import _
from frappe.utils import getdate, add_days, today, get_time


def sync_attendance_from_checkins(employee=None, date=None):
	"""
	Sync attendance from employee checkins for a specific date
	Called via: bench execute arijentek_core.attendance.sync.sync_attendance_from_checkins
	"""
	if not date:
		date = today()

	date = getdate(date)
	next_date = add_days(date, 1)

	filters = {"time": ["between", [date, next_date]]}
	if employee:
		filters["employee"] = employee

	checkins = frappe.get_all(
		"Employee Checkin",
		filters=filters,
		fields=["name", "employee", "time", "log_type", "device_id"],
		order_by="employee, time",
	)

	if not checkins:
		frappe.msgprint(_("No checkins found for {0}").format(date))
		return

	employee_checkins = {}
	for checkin in checkins:
		if checkin.employee not in employee_checkins:
			employee_checkins[checkin.employee] = []
		employee_checkins[checkin.employee].append(checkin)

	created_count = 0
	for emp, logs in employee_checkins.items():
		result = create_or_update_attendance(emp, date, logs)
		if result:
			created_count += 1

	frappe.msgprint(_("Created/Updated {0} attendance records").format(created_count))


def create_or_update_attendance(employee, date, checkins):
	"""
	Create or update attendance based on checkins
	"""
	existing = frappe.db.exists(
		"Attendance", {"employee": employee, "attendance_date": date, "docstatus": ["!=", 2]}
	)

	in_logs = [c for c in checkins if c.log_type == "IN"]
	out_logs = [c for c in checkins if c.log_type == "OUT"]

	if not in_logs:
		return None

	first_in = min(in_logs, key=lambda x: x.time)
	last_out = max(out_logs, key=lambda x: x.time) if out_logs else None

	working_hours = 0
	if last_out:
		working_hours = (last_out.time - first_in.time).total_seconds() / 3600

	status = determine_attendance_status(employee, date, working_hours, first_in)

	if existing:
		attendance = frappe.get_doc("Attendance", existing)
		attendance.working_hours = round(working_hours, 2)
		attendance.in_time = first_in.time
		attendance.out_time = last_out.time if last_out else None
		attendance.save()
		frappe.db.commit()
	else:
		attendance = frappe.new_doc("Attendance")
		attendance.update(
			{
				"employee": employee,
				"attendance_date": date,
				"status": status,
				"working_hours": round(working_hours, 2),
				"in_time": first_in.time,
				"out_time": last_out.time if last_out else None,
			}
		)
		attendance.insert()
		attendance.submit()
		frappe.db.commit()

	return attendance.name


def determine_attendance_status(employee, date, working_hours, first_in):
	"""
	Determine attendance status based on shift settings
	"""
	shift_type = frappe.db.get_value("Employee", employee, "default_shift")

	if not shift_type:
		return "Present" if working_hours > 0 else "Absent"

	shift = frappe.get_doc("Shift Type", shift_type)

	late_entry = False

	if shift.start_time and first_in:
		checkin_time = get_time(first_in.time)
		shift_start = get_time(shift.start_time)

		grace_minutes = getattr(shift, "late_entry_grace_period", 0) or 0

		checkin_minutes = checkin_time.hour * 60 + checkin_time.minute
		start_minutes = shift_start.hour * 60 + shift_start.minute + grace_minutes

		if checkin_minutes > start_minutes:
			late_entry = True

	half_day_threshold = getattr(shift, "working_hours_threshold_for_half_day", 4) or 4
	absent_threshold = getattr(shift, "working_hours_threshold_for_absent", 2) or 2

	if working_hours < absent_threshold:
		return "Absent"
	elif working_hours < half_day_threshold:
		return "Half Day"

	return "Present"


@frappe.whitelist()
def sync_today_attendance():
	"""
	API endpoint to sync today's attendance
	"""
	try:
		sync_attendance_from_checkins()
		return {"status": "success", "message": "Attendance synced successfully"}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Attendance Sync Error")
		return {"status": "error", "message": str(e)}


@frappe.whitelist()
def sync_date_range(from_date, to_date, employee=None):
	"""
	Sync attendance for a date range
	"""
	try:
		from_date = getdate(from_date)
		to_date = getdate(to_date)

		current_date = from_date
		while current_date <= to_date:
			sync_attendance_from_checkins(employee=employee, date=current_date)
			current_date = add_days(current_date, 1)

		return {"status": "success", "message": f"Attendance synced from {from_date} to {to_date}"}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Attendance Sync Error")
		return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_employee_attendance(employee, month=None, year=None):
	"""
	Get attendance summary for employee
	"""
	if not month or not year:
		today_date = getdate()
		month = month or today_date.month
		year = year or today_date.year

	start_date = getdate(f"{year}-{month:02d}-01")
	end_date = getdate(f"{year}-{month:02d}-28")

	import calendar

	last_day = calendar.monthrange(year, month)[1]
	end_date = getdate(f"{year}-{month:02d}-{last_day}")

	attendance = frappe.db.sql(
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
	for att in attendance:
		if att.status in summary:
			summary[att.status] += 1

	return {
		"records": attendance,
		"summary": summary,
		"period": {"start": str(start_date), "end": str(end_date)},
	}
