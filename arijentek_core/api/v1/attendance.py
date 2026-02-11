import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe.rate_limiter import rate_limit

ATTENDANCE_RATE_LIMIT = 10
ATTENDANCE_RATE_LIMIT_SECONDS = 60


@frappe.whitelist()
@rate_limit(limit=ATTENDANCE_RATE_LIMIT, seconds=ATTENDANCE_RATE_LIMIT_SECONDS)
def punch(employee=None, timestamp=None):
	employee = _validate_and_get_employee(employee)
	timestamp = _validate_timestamp(timestamp)

	last_checkin = frappe.db.get_all(
		"Employee Checkin", filters={"employee": employee}, fields=["log_type"], order_by="time desc", limit=1
	)

	log_type = "IN"
	if last_checkin and last_checkin[0].get("log_type") == "IN":
		log_type = "OUT"

	checkin = frappe.get_doc(
		{
			"doctype": "Employee Checkin",
			"employee": employee,
			"time": timestamp,
			"log_type": log_type,
			"device_id": "Web/Manual",
		}
	)
	checkin.insert()
	frappe.db.commit()

	return {"status": "success", "log_type": log_type, "time": str(timestamp), "employee": employee}


@frappe.whitelist()
@rate_limit(limit=ATTENDANCE_RATE_LIMIT, seconds=ATTENDANCE_RATE_LIMIT_SECONDS)
def get_status(employee=None):
	employee = _validate_and_get_employee(employee)

	last_checkin = frappe.db.get_all(
		"Employee Checkin",
		filters={"employee": employee},
		fields=["log_type", "time"],
		order_by="time desc",
		limit=1,
	)

	return {
		"last_log": {"log_type": last_checkin[0].get("log_type"), "time": str(last_checkin[0].get("time"))}
		if last_checkin
		else None
	}


def _validate_and_get_employee(employee=None):
	if employee:
		employee = str(employee).strip()[:50]
		if not frappe.db.exists("Employee", employee):
			frappe.throw(_("Invalid employee"))
		return employee

	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if not employee:
		frappe.throw(_("Employee not found for this user"))
	return employee


def _validate_timestamp(timestamp=None):
	if timestamp:
		try:
			if isinstance(timestamp, str):
				from frappe.utils import get_datetime

				timestamp = get_datetime(timestamp)
			now = now_datetime()
			max_future_seconds = 5
			if (timestamp - now).total_seconds() > max_future_seconds:
				timestamp = now
			return timestamp
		except Exception:
			return now_datetime()
	return now_datetime()


@frappe.whitelist()
def get_dashboard_data():
	"""Get dashboard data for employee"""
	employee = _validate_and_get_employee()

	today = frappe.utils.nowdate()
	month_start = frappe.utils.get_first_day(frappe.utils.nowdate())

	attendance_summary = frappe.db.sql(
		"""
		SELECT status, COUNT(*) as count
		FROM `tabAttendance`
		WHERE employee = %s
			AND attendance_date BETWEEN %s AND %s
			AND docstatus = 1
		GROUP BY status
	""",
		(employee, month_start, today),
		as_dict=True,
	)

	summary = {"Present": 0, "Absent": 0, "Half Day": 0, "On Leave": 0}
	for att in attendance_summary:
		summary[att.status] = att.count

	last_punch = frappe.db.get_all(
		"Employee Checkin",
		filters={"employee": employee},
		fields=["log_type", "time"],
		order_by="time desc",
		limit=1,
	)

	last_punch_data = None
	if last_punch:
		last_punch_data = {"log_type": last_punch[0].log_type, "time": str(last_punch[0].time)}

	return {
		"employee": employee,
		"attendance_summary": summary,
		"last_punch": last_punch_data,
		"current_month": frappe.utils.now_datetime().strftime("%B"),
		"year": frappe.utils.now_datetime().year,
	}


@frappe.whitelist()
def get_attendance_records(month=None, year=None):
	"""Get attendance records for current month"""
	employee = _validate_and_get_employee()

	if not month or not year:
		today = frappe.utils.nowdate()
		month = today.month
		year = today.year

	import calendar

	last_day = calendar.monthrange(year, month)[1]
	start_date = frappe.utils.getdate(f"{year}-{month:02d}-01")
	end_date = frappe.utils.getdate(f"{year}-{month:02d}-{last_day}")

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

	return {
		"records": [
			{"date": str(r.attendance_date), "status": r.status, "hours": r.working_hours or 0}
			for r in records
		],
		"period": {"start": str(start_date), "end": str(end_date)},
	}
