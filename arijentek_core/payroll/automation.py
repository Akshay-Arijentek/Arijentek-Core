import frappe
from frappe import _
from frappe.utils import getdate, add_months, get_first_day, get_last_day

def generate_monthly_payroll(company=None, payroll_period=None, posting_date=None, dry_run=False):
    """
    Generate payroll entry for all employees with assigned salary structures.
    Called via: bench execute arijentek_core.payroll.automation.generate_monthly_payroll
    """
    if not company:
        company = frappe.defaults.get_user_default("company")
        
    if not posting_date:
        posting_date = getdate()
        
    month_start = get_first_day(posting_date)
    month_end = get_last_day(posting_date)
    
    employees = get_eligible_employees(company, month_start, month_end)
    
    if not employees:
        frappe.msgprint(_("No eligible employees found for payroll"))
        return None
        
    payroll_entry = create_payroll_entry(
        company=company,
        start_date=month_start,
        end_date=month_end,
        employees=employees,
        payroll_period=payroll_period,
        dry_run=dry_run
    )
    
    return payroll_entry

def get_eligible_employees(company, start_date, end_date):
    """
    Get employees who:
    1. Have a Salary Structure Assignment
    2. Are active
    """
    employees = frappe.db.sql("""
        SELECT DISTINCT e.name, e.employee_name, e.department
        FROM `tabEmployee` e
        INNER JOIN `tabSalary Structure Assignment` ssa
            ON ssa.employee = e.name
        INNER JOIN `tabSalary Structure` ss
            ON ss.name = ssa.salary_structure
        WHERE e.company = %s
            AND e.status = 'Active'
            AND ssa.docstatus = 1
            AND ssa.from_date <= %s
        ORDER BY e.name
    """, (company, end_date), as_dict=True)
    
    return employees

def create_payroll_entry(company, start_date, end_date, employees, payroll_period=None, dry_run=False):
    """
    Create Payroll Entry document
    """
    employee_list = [{"employee": emp.name} for emp in employees]
    
    payroll_entry = frappe.new_doc("Payroll Entry")
    payroll_entry.update({
        "company": company,
        "posting_date": end_date,
        "payroll_frequency": "Monthly",
        "start_date": start_date,
        "end_date": end_date,
        "currency": frappe.get_cached_value("Company", company, "default_currency"),
        "payroll_frequency": "Monthly"
    })
    
    payroll_entry.set("employees", employee_list)
    
    payroll_entry.insert()
    
    if not dry_run:
        payroll_entry.submit()
        frappe.db.commit()
    
    return payroll_entry

def process_payroll_entry(payroll_entry_name, submit_salary_slips=True):
    """
    Process Payroll Entry - Generate and optionally submit Salary Slips
    """
    payroll_entry = frappe.get_doc("Payroll Entry", payroll_entry_name)
    
    payroll_entry.create_salary_slips()
    frappe.db.commit()
    
    if submit_salary_slips:
        payroll_entry.submit_salary_slips()
        frappe.db.commit()
        
    return payroll_entry

@frappe.whitelist()
def run_monthly_payroll_automation(posting_date=None):
    """
    Whitelisted method to run payroll automation
    Can be called from API or scheduled job
    """
    try:
        posting_date = getdate(posting_date) if posting_date else getdate()
        
        payroll_entry = generate_monthly_payroll(
            posting_date=posting_date,
            dry_run=False
        )
        
        if payroll_entry:
            process_payroll_entry(payroll_entry.name, submit_salary_slips=True)
            
            return {
                "status": "success",
                "payroll_entry": payroll_entry.name,
                "message": f"Payroll processed for {posting_date.strftime('%B %Y')}"
            }
            
        return {"status": "error", "message": "No payroll entry created"}
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Payroll Automation Error")
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def get_payroll_status(employee, month=None, year=None):
    """
    Check if salary slip exists for employee for given month/year
    """
    if not month or not year:
        today = getdate()
        month = month or today.month
        year = year or today.year
        
    start_date = getdate(f"{year}-{month:02d}-01")
    end_date = get_last_day(start_date)
    
    salary_slip = frappe.db.get_value(
        "Salary Slip",
        {
            "employee": employee,
            "start_date": start_date,
            "end_date": end_date,
            "docstatus": 1
        },
        ["name", "gross_pay", "net_pay", "total_deduction"],
        as_dict=True
    )
    
    attendance_summary = get_attendance_summary(employee, start_date, end_date)
    
    return {
        "salary_slip": salary_slip,
        "attendance_summary": attendance_summary,
        "period": {
            "start": str(start_date),
            "end": str(end_date)
        }
    }

def get_attendance_summary(employee, start_date, end_date):
    """
    Get attendance counts for the period
    """
    attendance = frappe.db.sql("""
        SELECT status, COUNT(*) as count
        FROM `tabAttendance`
        WHERE employee = %s
            AND attendance_date BETWEEN %s AND %s
            AND docstatus = 1
        GROUP BY status
    """, (employee, start_date, end_date), as_dict=True)
    
    return {a.status: a.count for a in attendance}
