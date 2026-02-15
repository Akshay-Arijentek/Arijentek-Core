"""
Payroll Automation Module
=========================

Handles automated payroll generation with attendance-based calculations.
Integrates with ERPNext's payroll system and extends it with:
- Attendance-based payment days calculation
- LOP (Loss of Pay) deduction
- Statutory deductions (PT, PF, ESI)
"""

import frappe
from frappe import _
from frappe.utils import getdate, add_months, get_first_day, get_last_day, flt
from arijentek_core.payroll.payslip_generator import PayslipGenerator, generate_payroll_for_month
from arijentek_core.payroll.calculator import PayrollCalculator, get_lop_summary


def generate_monthly_payroll(company=None, payroll_period=None, posting_date=None, dry_run=False):
	"""
	Generate payroll entry for all employees with assigned salary structures.
	Uses attendance-based calculation for payment days.

	Called via: bench execute arijentek_core.payroll.automation.generate_monthly_payroll

	Args:
		company: Company name (defaults to user's default)
		payroll_period: Payroll period (optional)
		posting_date: Date to generate payroll for (defaults to current date)
		dry_run: If True, don't submit the payroll

	Returns:
		Dictionary with payroll generation results
	"""
	if not company:
		company = frappe.defaults.get_user_default("company")

	if not posting_date:
		posting_date = getdate()
	else:
		posting_date = getdate(posting_date)

	month_start = get_first_day(posting_date)
	month_end = get_last_day(posting_date)

	# Use our new PayslipGenerator
	generator = PayslipGenerator(company, month_start, month_end)
	employees = generator.get_eligible_employees()

	if not employees:
		frappe.msgprint(_("No eligible employees found for payroll"))
		return None

	# Generate payslips
	result = generator.generate_all_payslips(submit=not dry_run)

	if dry_run:
		return {
			"status": "dry_run",
			"employees": [e.name for e in employees],
			"message": f"Would generate payroll for {len(employees)} employees",
		}

	return {
		"status": "success",
		"created_slips": result["created"],
		"failed_employees": result["failed"],
		"total_created": result["total_created"],
		"total_failed": result["total_failed"],
		"message": f"Generated {result['total_created']} salary slips",
	}


def get_eligible_employees(company, start_date, end_date):
	"""
	Get employees who:
	1. Have a Salary Structure Assignment
	2. Are active
	3. Joined on or before the pay period end date
	"""
	employees = frappe.db.sql(
		"""
		SELECT DISTINCT e.name, e.employee_name, e.department, e.designation,
			e.date_of_joining, e.relieving_date
		FROM `tabEmployee` e
		INNER JOIN `tabSalary Structure Assignment` ssa
			ON ssa.employee = e.name
		INNER JOIN `tabSalary Structure` ss
			ON ss.name = ssa.salary_structure
		WHERE e.company = %s
			AND e.status = 'Active'
			AND ssa.docstatus = 1
			AND ssa.from_date <= %s
			AND (e.date_of_joining IS NULL OR e.date_of_joining <= %s)
			AND (e.relieving_date IS NULL OR e.relieving_date >= %s)
		ORDER BY e.name
		""",
		(company, end_date, end_date, start_date),
		as_dict=True,
	)

	return employees


def create_payroll_entry(company, start_date, end_date, employees, payroll_period=None, dry_run=False):
	"""
	Create Payroll Entry document using ERPNext's standard process.
	This is kept for backward compatibility.
	"""
	employee_list = [{"employee": emp.name} for emp in employees]

	payroll_entry = frappe.new_doc("Payroll Entry")
	payroll_entry.update(
		{
			"company": company,
			"posting_date": end_date,
			"payroll_frequency": "Monthly",
			"start_date": start_date,
			"end_date": end_date,
			"currency": frappe.get_cached_value("Company", company, "default_currency"),
		}
	)

	payroll_entry.set("employees", employee_list)

	payroll_entry.insert()

	if not dry_run:
		payroll_entry.submit()
		frappe.db.commit()

	return payroll_entry


def process_payroll_entry(payroll_entry_name, submit_salary_slips=True):
	"""
	Process Payroll Entry - Generate and optionally submit Salary Slips.
	Uses ERPNext's standard process.
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
	Whitelisted method to run payroll automation.
	Can be called from API or scheduled job.

	Args:
		posting_date: Date to generate payroll for (defaults to current date)

	Returns:
		Dictionary with status and results
	"""
	try:
		posting_date = getdate(posting_date) if posting_date else getdate()

		result = generate_monthly_payroll(posting_date=posting_date, dry_run=False)

		if result:
			return {
				"status": "success",
				"created_slips": result.get("created_slips", []),
				"total_created": result.get("total_created", 0),
				"message": f"Payroll processed for {posting_date.strftime('%B %Y')}",
			}

		return {"status": "error", "message": "No payroll entry created"}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Payroll Automation Error")
		return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_payroll_status(employee, month=None, year=None):
	"""
	Check if salary slip exists for employee for given month/year.
	Also returns attendance summary and LOP details.

	Args:
		employee: Employee ID
		month: Month (1-12)
		year: Year

	Returns:
		Dictionary with salary slip, attendance summary, and LOP details
	"""
	if not month or not year:
		today = getdate()
		month = month or today.month
		year = year or today.year

	start_date = getdate(f"{year}-{month:02d}-01")
	end_date = get_last_day(start_date)

	salary_slip = frappe.db.get_value(
		"Salary Slip",
		{"employee": employee, "start_date": start_date, "end_date": end_date, "docstatus": 1},
		["name", "gross_pay", "net_pay", "total_deduction", "working_days", "payment_days"],
		as_dict=True,
	)

	attendance_summary = get_attendance_summary(employee, start_date, end_date)
	lop_summary = get_lop_summary(employee, start_date, end_date)

	return {
		"salary_slip": salary_slip,
		"attendance_summary": attendance_summary,
		"lop_summary": lop_summary,
		"period": {"start": str(start_date), "end": str(end_date)},
	}


def get_attendance_summary(employee, start_date, end_date):
	"""
	Get attendance counts for the period.

	Args:
		employee: Employee ID
		start_date: Period start date
		end_date: Period end date

	Returns:
		Dictionary with status counts
	"""
	attendance = frappe.db.sql(
		"""
		SELECT status, COUNT(*) as count
		FROM `tabAttendance`
		WHERE employee = %s
			AND attendance_date BETWEEN %s AND %s
			AND docstatus = 1
		GROUP BY status
		""",
		(employee, start_date, end_date),
		as_dict=True,
	)

	return {a.status: a.count for a in attendance}


@frappe.whitelist()
def get_payroll_preview_for_employee(employee, month=None, year=None):
	"""
	Get a preview of payroll calculation for an employee.
	Shows what the salary slip would look like before generation.

	Args:
		employee: Employee ID
		month: Month (1-12)
		year: Year

	Returns:
		Dictionary with complete payroll preview
	"""
	if not month or not year:
		today = getdate()
		month = month or today.month
		year = year or today.year

	start_date = getdate(f"{year}-{month:02d}-01")
	end_date = get_last_day(start_date)

	calculator = PayrollCalculator(employee, start_date, end_date)
	return calculator.calculate_payroll()


@frappe.whitelist()
def recalculate_payroll_for_employee(employee, month, year):
	"""
	Recalculate payroll for an employee after attendance changes.
	This can be used to update a salary slip with new attendance data.

	Args:
		employee: Employee ID
		month: Month (1-12)
		year: Year

	Returns:
		Dictionary with recalculated payroll
	"""
	start_date = getdate(f"{year}-{month:02d}-01")
	end_date = get_last_day(start_date)

	# Check for existing salary slip
	existing_slip = frappe.db.get_value(
		"Salary Slip",
		{
			"employee": employee,
			"start_date": start_date,
			"end_date": end_date,
			"docstatus": ["!=", 2],
		},
		"name",
	)

	if existing_slip:
		# Cancel and delete existing draft slip
		slip = frappe.get_doc("Salary Slip", existing_slip)
		if slip.docstatus == 0:
			frappe.delete_doc("Salary Slip", existing_slip)
		elif slip.docstatus == 1:
			# Submitted slip - need to cancel first
			slip.cancel()
			frappe.delete_doc("Salary Slip", existing_slip)

	# Generate new slip
	generator = PayslipGenerator(
		frappe.db.get_value("Employee", employee, "company"),
		start_date,
		end_date,
	)
	new_slip = generator.generate_payslip(employee, submit=False)

	if new_slip:
		return {
			"success": True,
			"salary_slip": new_slip.name,
			"gross_pay": new_slip.gross_pay,
			"net_pay": new_slip.net_pay,
		}

	return {"success": False, "error": "Failed to generate salary slip"}


@frappe.whitelist()
def get_payroll_summary(company=None, month=None, year=None):
	"""
	Get payroll summary for a company and period.

	Args:
		company: Company name
		month: Month (1-12)
		year: Year

	Returns:
		Dictionary with payroll summary statistics
	"""
	if not company:
		company = frappe.defaults.get_user_default("company")

	if not month or not year:
		today = getdate()
		month = month or today.month
		year = year or today.year

	start_date = getdate(f"{year}-{month:02d}-01")
	end_date = get_last_day(start_date)

	# Get salary slips for the period
	slips = frappe.db.sql(
		"""
		SELECT 
			name, employee, employee_name, department,
			gross_pay, net_pay, total_deduction,
			working_days, payment_days
		FROM `tabSalary Slip`
		WHERE company = %s
			AND start_date = %s
			AND end_date = %s
			AND docstatus = 1
		""",
		(company, start_date, end_date),
		as_dict=True,
	)

	# Calculate totals
	total_gross = sum(flt(s.gross_pay) for s in slips)
	total_net = sum(flt(s.net_pay) for s in slips)
	total_deductions = sum(flt(s.total_deduction) for s in slips)

	# Get department breakdown
	dept_breakdown = {}
	for slip in slips:
		dept = slip.department or "Unassigned"
		if dept not in dept_breakdown:
			dept_breakdown[dept] = {
				"count": 0,
				"gross_pay": 0,
				"net_pay": 0,
				"deductions": 0,
			}
		dept_breakdown[dept]["count"] += 1
		dept_breakdown[dept]["gross_pay"] += flt(slip.gross_pay)
		dept_breakdown[dept]["net_pay"] += flt(slip.net_pay)
		dept_breakdown[dept]["deductions"] += flt(slip.total_deduction)

	return {
		"company": company,
		"period": {"month": month, "year": year, "start": str(start_date), "end": str(end_date)},
		"total_employees": len(slips),
		"total_gross_pay": flt(total_gross, 2),
		"total_net_pay": flt(total_net, 2),
		"total_deductions": flt(total_deductions, 2),
		"department_breakdown": dept_breakdown,
		"slips": slips,
	}
