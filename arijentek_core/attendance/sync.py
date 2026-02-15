import frappe
from frappe import _
from frappe.utils import getdate, add_days, today, get_time
import calendar

# Allowed roles for manual sync operations
_ALLOWED_ROLES = ("HR Manager", "System Manager", "Attendance Manager")

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


def create_or_update_attendance(employee, date, checkins, auto_commit=True):
    """
    Create or update attendance based on checkins.
    
    CRITICAL FIX: Handles submitted documents by cancelling them first.
    """
    # Check for non-cancelled existing attendance
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
        pass  # Calculate via TimeDelta
        working_hours = (last_out.time - first_in.time).total_seconds() / 3600

    status = determine_attendance_status(employee, date, working_hours, first_in)

    # Prepare data for the attendance record
    attendance_data = {
        "employee": employee,
        "attendance_date": date,
        "status": status,
        "working_hours": round(working_hours, 2),
        "in_time": first_in.time,
        "out_time": last_out.time if last_out else None,
        "doctype": "Attendance"
    }

    if existing:
        existing_doc = frappe.get_doc("Attendance", existing)
        
        # BUG FIX 1: Handle Submitted Document
        if existing_doc.docstatus == 1:
            existing_doc.flags.ignore_permissions = True
            existing_doc.cancel()
            # After cancelling, we must create a NEW record
            new_attendance = frappe.new_doc("Attendance")
            new_attendance.update(attendance_data)
            new_attendance.insert(ignore_permissions=True)
            new_attendance.flags.ignore_permissions = True
            new_attendance.submit()
            attendance_name = new_attendance.name
        else:
            # If Draft (0), just update
            existing_doc.update(attendance_data)
            existing_doc.save(ignore_permissions=True)
            # Submit if needed (Auto Attendance usually submits)
            existing_doc.flags.ignore_permissions = True
            existing_doc.submit()
            attendance_name = existing_doc.name
    else:
        # Create New
        attendance = frappe.new_doc("Attendance")
        attendance.update(attendance_data)
        attendance.insert(ignore_permissions=True)
        attendance.flags.ignore_permissions = True
        attendance.submit()
        attendance_name = attendance.name

    if auto_commit:
        frappe.db.commit()

    return attendance_name


def determine_attendance_status(employee, date, working_hours, first_in):
    """
    Determine attendance status based on shift settings and approved leave.
    """
    # Check for approved half-day leave on this date
    has_approved_half_day_leave = frappe.db.exists(
        "Leave Application",
        {
            "employee": employee,
            "half_day": 1,
            "status": "Approved",
            "docstatus": 1,
            "from_date": ["<=", date],
            "to_date": [">=", date],
        },
    )

    shift_type = frappe.db.get_value("Employee", employee, "default_shift")

    if not shift_type:
        # No shift assigned — use simple thresholds
        if has_approved_half_day_leave:
            return "Half Day"
        
        # STRICT THRESHOLDS (User Request):
        # >= 8 hours: Present
        # >= 4 hours: Half Day
        # < 4 hours: Absent
        if working_hours >= 8:
            return "Present"
        elif working_hours >= 4:
            return "Half Day"
        
        return "Absent"

    shift = frappe.get_doc("Shift Type", shift_type)

    # late_entry logic (Reserved for future use)
    # late_entry = False
    # if shift.start_time and first_in:
    #     checkin_time = get_time(first_in.time)
    #     shift_start = get_time(shift.start_time)
    #     grace_minutes = getattr(shift, "late_entry_grace_period", 0) or 0
    #     if ...: late_entry = True

    # STRICT THRESHOLDS (User Request - Permanent Fix):
    # Ignore Shift Type defaults, enforce global policy:
    # >= 8 hours: Present
    # >= 4 hours: Half Day
    # < 4 hours: Absent
    
    if working_hours >= 8:
        return "Present"
    elif working_hours >= 4:
        return "Half Day"
    
    return "Absent"


@frappe.whitelist()
def sync_today_attendance():
    """
    API endpoint to sync today's attendance.
    BUG FIX 3: Added Role Guard.
    """
    if not frappe.has_permission("Attendance", "write"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    try:
        sync_attendance_from_checkins()
        return {"status": "success", "message": "Attendance synced successfully"}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Attendance Sync Error")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def sync_date_range(from_date, to_date, employee=None):
    """
    Sync attendance for a date range.
    BUG FIX 3: Added Role Guard.
    BUG FIX 4: Date Range Limit (DoS protection).
    """
    if not frappe.has_permission("Attendance", "write"):
         # Or check specific roles
         if not any(r in frappe.get_roles() for r in _ALLOWED_ROLES):
             frappe.throw(_("Not permitted"))

    try:
        from_date = getdate(from_date)
        to_date = getdate(to_date)

        # BUG FIX 4: Limit range
        if (to_date - from_date).days > 31:
            frappe.throw(_("Date range cannot exceed 31 days per request"))

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
    Get attendance summary for employee.
    BUG FIX 5: Object Level Permission Check.
    BUG FIX 2: Crash prevention (NameError).
    """
    # BUG FIX 5: Check ownership
    user = frappe.session.user
    emp_user_id = frappe.db.get_value("Employee", employee, "user_id")
    
    # Allow if user is the employee OR user has HR Manager role
    if user != emp_user_id and "HR Manager" not in frappe.get_roles() and "System Manager" not in frappe.get_roles():
        frappe.throw(_("You are not authorized to view this employee's attendance"))

    if not month or not year:
        today_date = getdate()
        month = month or today_date.month
        year = year or today_date.year
    else:
        # Ensure int
        month = int(month)
        year = int(year)

    # BUG FIX 2: Ensure start_date and end_date are defined correctly
    start_date = getdate(f"{year}-{month:02d}-01")
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
