import frappe
from frappe import _
from frappe.utils import nowdate, now_datetime, getdate, get_first_day, get_last_day
from datetime import datetime

# ============ EMPLOYEE INFO ============

@frappe.whitelist()
def get_employee_info():
    """Get current employee details"""
    user = frappe.session.user
    employee = frappe.db.get_value("Employee", {"user_id": user}, 
        ["name", "employee_name", "department", "designation"], as_dict=True)
    
    if not employee:
        return {"error": "No employee record found for this user"}
    
    return {
        "employee_id": employee.name,
        "employee_name": employee.employee_name,
        "department": employee.department,
        "designation": employee.designation
    }

# ============ CLOCK IN/OUT ============

@frappe.whitelist()
def get_today_checkin():
    """Get today's check-in status"""
    employee = get_current_employee()
    if not employee:
        return {"error": "Employee not found"}
    
    today = nowdate()
    
    # Get last check-in for today
    checkin = frappe.db.sql("""
        SELECT name, time, log_type
        FROM `tabEmployee Checkin`
        WHERE employee = %s AND DATE(time) = %s
        ORDER BY time DESC
    """, (employee, today), as_dict=True)
    
    clock_in = None
    clock_out = None
    
    for log in reversed(checkin):
        if log.log_type == "IN" and not clock_in:
            clock_in = log.time
        elif log.log_type == "OUT" and clock_in:
            clock_out = log.time
    
    return {
        "clock_in": clock_in.isoformat() if clock_in else None,
        "clock_out": clock_out.isoformat() if clock_out else None
    }

@frappe.whitelist()
def clock_in():
    """Record clock in"""
    employee = get_current_employee()
    if not employee:
        return {"success": False, "error": "Employee not found"}
    
    try:
        checkin = frappe.get_doc({
            "doctype": "Employee Checkin",
            "employee": employee,
            "time": now_datetime(),
            "log_type": "IN"
        })
        checkin.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "time": checkin.time.isoformat()}
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def clock_out():
    """Record clock out"""
    employee = get_current_employee()
    if not employee:
        return {"success": False, "error": "Employee not found"}
    
    try:
        checkin = frappe.get_doc({
            "doctype": "Employee Checkin",
            "employee": employee,
            "time": now_datetime(),
            "log_type": "OUT"
        })
        checkin.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "time": checkin.time.isoformat()}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============ LEAVE MANAGEMENT ============

@frappe.whitelist()
def get_leave_types():
    """Get available leave types"""
    return frappe.get_all("Leave Type", filters={"is_lwp": 0}, pluck="name")

@frappe.whitelist()
def get_leave_balance():
    """Get current leave balance"""
    employee = get_current_employee()
    if not employee:
        return []
    
    from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on
    
    leave_types = frappe.get_all("Leave Type", pluck="name")
    balances = []
    
    for leave_type in leave_types:
        try:
            balance = get_leave_balance_on(employee, leave_type, nowdate())
            if balance > 0:
                balances.append({
                    "leave_type": leave_type,
                    "balance": balance
                })
        except:
            pass
    
    return balances

@frappe.whitelist()
def apply_leave(leave_type, from_date, to_date, half_day=0, reason=""):
    """Submit leave application"""
    employee = get_current_employee()
    if not employee:
        return {"success": False, "error": "Employee not found"}
    
    try:
        leave = frappe.get_doc({
            "doctype": "Leave Application",
            "employee": employee,
            "leave_type": leave_type,
            "from_date": from_date,
            "to_date": to_date,
            "half_day": half_day,
            "description": reason,
            "status": "Open"
        })
        leave.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "name": leave.name}
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_leave_applications():
    """Get employee's leave applications"""
    employee = get_current_employee()
    if not employee:
        return []
    
    return frappe.get_all("Leave Application",
        filters={"employee": employee},
        fields=["name", "leave_type", "from_date", "to_date", "total_leave_days", "status"],
        order_by="creation desc",
        limit=20
    )

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
    
    slips = frappe.get_all("Salary Slip",
        filters={"employee": employee, "docstatus": 1},
        fields=["name", "start_date", "end_date", "net_pay", "gross_pay"],
        order_by="start_date desc",
        limit=12
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

# ============ ATTENDANCE SUMMARY ============

@frappe.whitelist()
def get_attendance_summary():
    """Get attendance summary for current month"""
    employee = get_current_employee()
    if not employee:
        return {}
    
    today = getdate(nowdate())
    first_day = get_first_day(today)
    last_day = get_last_day(today)
    
    summary = frappe.db.sql("""
        SELECT status, COUNT(*) as count
        FROM `tabAttendance`
        WHERE employee = %s
        AND attendance_date BETWEEN %s AND %s
        AND docstatus = 1
        GROUP BY status
    """, (employee, first_day, last_day), as_dict=True)
    
    result = {"present": 0, "absent": 0, "half_day": 0}
    for row in summary:
        if row.status == "Present":
            result["present"] = row.count
        elif row.status == "Absent":
            result["absent"] = row.count
        elif row.status == "Half Day":
            result["half_day"] = row.count
    
    return result

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
        
        doc = frappe.get_doc({
            "doctype": doctype,
            "subject": f"[{issue_type}] Issue from Employee Portal",
            "description": description,
            "raised_by": frappe.session.user
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "ticket": doc.name}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============ HELPERS ============

def get_current_employee():
    """Get employee ID for current user"""
    return frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")