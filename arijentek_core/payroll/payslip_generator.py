"""
Payslip Generator Module
========================

Generates salary slips for employees based on:
1. Attendance data (clock in/out or manual)
2. Salary structure assignments
3. Statutory deductions

This module creates Salary Slip documents in ERPNext with proper
attendance-based calculations.
"""

import frappe
from frappe import _
from frappe.utils import getdate, get_first_day, get_last_day, flt, cint, now_datetime, money_in_words
import calendar
from arijentek_core.payroll.calculator import PayrollCalculator, get_lop_summary


class PayslipGenerator:
	"""
	Generates salary slips for employees with attendance-based calculations.
	"""

	def __init__(self, company, start_date, end_date):
		self.company = company
		self.start_date = getdate(start_date)
		self.end_date = getdate(end_date)
		self.created_slips = []
		self.failed_employees = []

	def get_eligible_employees(self):
		"""
		Get employees eligible for payroll:
		1. Active employees
		2. With salary structure assignment
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
			(self.company, self.end_date, self.end_date, self.start_date),
			as_dict=True,
		)

		return employees

	def generate_payslip(self, employee, submit=False):
		"""
		Generate a salary slip for an employee.

		Args:
			employee: Employee ID
			submit: Whether to submit the salary slip after creation

		Returns:
			Salary Slip document or None if failed
		"""
		try:
			# Check if salary slip already exists
			existing = frappe.db.exists(
				"Salary Slip",
				{
					"employee": employee,
					"start_date": self.start_date,
					"end_date": self.end_date,
					"docstatus": ["!=", 2],
				},
			)

			if existing:
				frappe.msgprint(
					_("Salary Slip already exists for {0}: {1}").format(employee, existing)
				)
				return frappe.get_doc("Salary Slip", existing)

			# Calculate payroll using our calculator
			calculator = PayrollCalculator(employee, self.start_date, self.end_date)
			payroll_data = calculator.calculate_payroll()

			# Create Salary Slip
			salary_slip = frappe.new_doc("Salary Slip")
			salary_slip.update(
				{
					"employee": employee,
					"employee_name": payroll_data["employee_name"],
					"department": payroll_data["department"],
					"designation": payroll_data["designation"],
					"salary_structure": payroll_data.get("salary_structure"),
					"salary_structure_assignment": payroll_data.get("salary_structure_assignment"),
					"company": self.company,
					"start_date": self.start_date,
					"end_date": self.end_date,
					"posting_date": self.end_date,
					"payroll_frequency": "Monthly",
					"working_days": payroll_data["working_days"],
					"payment_days": payroll_data["payment_days"],
					"lop_days": payroll_data["lop_days"],
					"half_days": payroll_data["half_days"],
				}
			)

			# Add earnings
			for earning in payroll_data["earnings"]:
				salary_slip.append(
					"earnings",
					{
						"salary_component": earning["salary_component"],
						"abbr": earning["abbr"],
						"amount": earning["amount"],
					},
				)

			# Add deductions
			for deduction in payroll_data["deductions"]:
				salary_slip.append(
					"deductions",
					{
						"salary_component": deduction["salary_component"],
						"abbr": deduction["abbr"],
						"amount": deduction["amount"],
					},
				)

			# Set totals
			salary_slip.gross_pay = payroll_data["gross_pay"]
			salary_slip.total_deduction = payroll_data["total_deduction"]
			salary_slip.net_pay = payroll_data["net_pay"]

			# Insert
			salary_slip.insert(ignore_permissions=True)

			# Submit if requested
			if submit:
				salary_slip.submit()
				frappe.db.commit()

			self.created_slips.append(salary_slip.name)
			return salary_slip

		except Exception as e:
			self.failed_employees.append({"employee": employee, "error": str(e)})
			frappe.log_error(
				frappe.get_traceback(),
				_("Payslip Generation Error - {0}").format(employee),
			)
			return None

	def generate_all_payslips(self, employees=None, submit=False):
		"""
		Generate salary slips for all eligible employees.

		Args:
			employees: List of employee IDs (optional, defaults to all eligible)
			submit: Whether to submit the salary slips

		Returns:
			Dictionary with created and failed slips
		"""
		if not employees:
			employees = self.get_eligible_employees()
			employees = [e.name for e in employees]

		for employee in employees:
			self.generate_payslip(employee, submit=submit)

		return {
			"created": self.created_slips,
			"failed": self.failed_employees,
			"total_created": len(self.created_slips),
			"total_failed": len(self.failed_employees),
		}


@frappe.whitelist()
def generate_payslip_for_employee(employee, month=None, year=None, submit=False):
	"""
	Generate a salary slip for a single employee.

	Args:
		employee: Employee ID
		month: Month (1-12), defaults to previous month
		year: Year, defaults to current year
		submit: Whether to submit the salary slip

	Returns:
		Dictionary with result
	"""
	month, year = _get_month_year(month, year)
	start_date, end_date = _get_pay_period(month, year)

	company = frappe.db.get_value("Employee", employee, "company")
	if not company:
		company = frappe.defaults.get_user_default("company")

	generator = PayslipGenerator(company, start_date, end_date)
	slip = generator.generate_payslip(employee, submit=cint(submit))

	if slip:
		return {
			"success": True,
			"salary_slip": slip.name,
			"gross_pay": slip.gross_pay,
			"net_pay": slip.net_pay,
			"message": _("Salary Slip created successfully"),
		}
		return {
			"success": False,
			"error": generator.failed_employees[0]["error"] if generator.failed_employees else "Unknown error",
		}


@frappe.whitelist()
def delete_my_payslip(name):
	"""
	Delete a user's payslip.
	
	Args:
		name: Salary Slip name
	"""
	if not name:
		return {"success": False, "error": "Name is required"}
		
	try:
		if not frappe.db.exists("Salary Slip", name):
			return {"success": False, "error": "Salary Slip not found"}
			
		slip = frappe.get_doc("Salary Slip", name)
		
		# Verify ownership
		employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
		if not employee or slip.employee != employee:
			return {"success": False, "error": "Not authorized to delete this payslip"}
			
		# Cancel if submitted
		if slip.docstatus == 1:
			slip.cancel()
			
		# Delete
		frappe.delete_doc("Salary Slip", name)
		
		return {"success": True, "message": "Payslip deleted successfully"}
		
	except Exception as e:
		frappe.log_error(f"Error deleting payslip {name}: {e}", "Payslip Delete Error")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def generate_payroll_for_month(month=None, year=None, company=None, submit=False):
	"""
	Generate salary slips for all eligible employees for a month.

	Args:
		month: Month (1-12), defaults to previous month
		year: Year, defaults to current year
		company: Company, defaults to user's default company
		submit: Whether to submit the salary slips

	Returns:
		Dictionary with generation results
	"""
	month, year = _get_month_year(month, year)
	start_date, end_date = _get_pay_period(month, year)

	if not company:
		company = frappe.defaults.get_user_default("company")

	generator = PayslipGenerator(company, start_date, end_date)
	result = generator.generate_all_payslips(submit=cint(submit))

	return {
		"success": True,
		"month": month,
		"year": year,
		"period": {"start": str(start_date), "end": str(end_date)},
		"created_slips": result["created"],
		"failed_employees": result["failed"],
		"total_created": result["total_created"],
		"total_failed": result["total_failed"],
		"message": _("Generated {0} salary slips for {1}/{2}").format(
			result["total_created"], month, year
		),
	}


@frappe.whitelist()
def get_payslip_details(name):
	"""
	Get detailed payslip information for display.

	Args:
		name: Salary Slip name

	Returns:
		Dictionary with complete payslip details
	"""
	slip = frappe.get_doc("Salary Slip", name)

	# Get attendance summary for the period
	attendance_summary = _get_attendance_summary_for_slip(slip)

	# Get LOP breakdown
	lop_summary = get_lop_summary(slip.employee, slip.start_date, slip.end_date)

	# Format earnings and deductions
	earnings = []
	for e in slip.earnings:
		earnings.append({
			"component": e.salary_component,
			"abbr": e.abbr,
			"amount": flt(e.amount, 2),
		})

	deductions = []
	for d in slip.deductions:
		deductions.append({
			"component": d.salary_component,
			"abbr": d.abbr,
			"amount": flt(d.amount, 2),
		})

	return {
		"name": slip.name,
		"employee": slip.employee,
		"employee_name": slip.employee_name,
		"department": slip.department,
		"designation": slip.designation,
		"company": slip.company,
		"start_date": str(slip.start_date),
		"end_date": str(slip.end_date),
		"posting_date": str(slip.posting_date),
		"month": getdate(slip.start_date).strftime("%B"),
		"year": getdate(slip.start_date).year,
		"working_days": slip.working_days,
		"payment_days": slip.payment_days,
		"lop_days": slip.lop_days if hasattr(slip, "lop_days") else lop_summary["lop_days"],
		"half_days": slip.half_days if hasattr(slip, "half_days") else 0,
		"earnings": earnings,
		"deductions": deductions,
		"gross_pay": flt(slip.gross_pay, 2),
		"total_deduction": flt(slip.total_deduction, 2),
		"net_pay": flt(slip.net_pay, 2),
		"attendance_summary": attendance_summary,
		"lop_summary": lop_summary,
		"status": "Submitted" if slip.docstatus == 1 else "Draft" if slip.docstatus == 0 else "Cancelled",
	}


def _get_month_year(month, year):
	"""Get month and year, defaulting to previous month."""
	today = getdate()

	if month:
		month = cint(month)
	else:
		month = today.month - 1
		if month < 1:
			month = 12

	if year:
		year = cint(year)
	else:
		if today.month == 1:
			year = today.year - 1
		else:
			year = today.year

	# Validation: Cannot generate for current or future months
	requested_date = getdate(f"{year}-{month:02d}-01")
	current_month_start = getdate(f"{today.year}-{today.month:02d}-01")
	
	if requested_date >= current_month_start:
		frappe.throw(_("Payslips can only be generated for completed previous months."))

	return month, year


def _get_pay_period(month, year):
	"""Get start and end date for a pay period."""
	start_date = getdate(f"{year}-{month:02d}-01")
	last_day = calendar.monthrange(year, month)[1]
	end_date = getdate(f"{year}-{month:02d}-{last_day}")
	return start_date, end_date


def _get_attendance_summary_for_slip(slip):
	"""Get attendance summary for the salary slip period."""
	summary = frappe.db.sql(
		"""
		SELECT status, COUNT(*) as count
		FROM `tabAttendance`
		WHERE employee = %s
			AND attendance_date BETWEEN %s AND %s
			AND docstatus = 1
		GROUP BY status
		""",
		(slip.employee, slip.start_date, slip.end_date),
		as_dict=True,
	)

	result = {"Present": 0, "Absent": 0, "Half Day": 0, "On Leave": 0}
	for row in summary:
		if row.status in result:
			result[row.status] = row.count

	return result


@frappe.whitelist()
def get_employee_payslips(employee, limit=12):
	"""
	Get list of salary slips for an employee.

	Args:
		employee: Employee ID
		limit: Maximum number of slips to return

	Returns:
		List of salary slips with basic details
	"""
	slips = frappe.db.sql(
		"""
		SELECT name, start_date, end_date, gross_pay, net_pay, total_deduction, docstatus
		FROM `tabSalary Slip`
		WHERE employee = %s
			AND docstatus != 2
		ORDER BY start_date DESC
		LIMIT %s
		""",
		(employee, cint(limit)),
		as_dict=True,
	)

	result = []
	for slip in slips:
		result.append({
			"name": slip.name,
			"start_date": str(slip.start_date),
			"end_date": str(slip.end_date),
			"month": getdate(slip.start_date).strftime("%B"),
			"year": getdate(slip.start_date).year,
			"gross_pay": flt(slip.gross_pay, 2),
			"net_pay": flt(slip.net_pay, 2),
			"total_deduction": flt(slip.total_deduction, 2),
			"status": "Submitted" if slip.docstatus == 1 else "Draft",
		})

	return result


@frappe.whitelist()
def download_payslip_pdf(name):
	"""
	Generate and download PDF for a salary slip.

	Args:
		name: Salary Slip name

	Returns:
		PDF file response
	"""
	slip = frappe.get_doc("Salary Slip", name)

	# Verify access
	employee = frappe.db.get_value(
		"Employee", {"user_id": frappe.session.user}, "name"
	)
	if not employee or (slip.employee != employee and not frappe.has_permission("Salary Slip", "read")):
		frappe.throw(_("Not authorized to view this payslip"))

	# Generate PDF
	from frappe.utils.pdf import get_pdf
	from frappe.utils import formatdate, money_in_words

	# Prepare Context
	company_doc = frappe.get_doc("Company", slip.company)
	company_logo = company_doc.company_logo
	
	# Handle logo URL if relative
	if company_logo and company_logo.startswith("/"):
		# In PDF generation, sometimes we need full URL or file path. 
		# But usually get_pdf handles relative paths if host is set.
		# Let's assume standard behavior.
		pass

	context = {
		"doc": slip,
		"company_logo": company_logo,
		"month_name": getdate(slip.start_date).strftime("%B"),
		"now_date": formatdate(now_datetime()),
		"currency_symbol": frappe.db.get_value("Currency", slip.currency, "symbol") or "₹",
	}
	
	# Add amount in words to doc (monkey patch for template)
	slip.net_pay_in_words = money_in_words(slip.net_pay, slip.currency)

	html = frappe.render_template("arijentek_core/templates/simple_payslip.html", context)
	
	# PDF Kit Options - Minimal set for unpatched wkhtmltopdf
	options = {
		"page-size": "A4",
		"margin-top": "15mm",
		"margin-right": "15mm",
		"margin-bottom": "15mm",
		"margin-left": "15mm",
		"encoding": "UTF-8",
		"quiet": "",
		"no-outline": None,
		"disable-smart-shrinking": None, # Sometimes causes issues, but standard
	}
	
	# Try-catch specifically for PDF generation to return clearer error
	try:
		pdf = get_pdf(html, options=options)
	except Exception as e:
		# Fallback without options if failed
		frappe.log_error(f"PDF Gen Error: {e}", "Payslip PDF Error")
		try:
			pdf = get_pdf(html)
		except Exception as e2:
			raise e2

	frappe.local.response.filename = f"Payslip_{slip.start_date}_{slip.employee}.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "pdf"


@frappe.whitelist()
def get_payroll_dashboard_data(employee):
	"""
	Get payroll dashboard data for an employee.

	Returns:
		Dictionary with YTD totals, latest slip, and monthly breakdown
	"""
	today = getdate()
	year_start = getdate(f"{today.year}-01-01")
	year_end = getdate(f"{today.year}-12-31")

	# YTD totals
	ytd_data = frappe.db.sql(
		"""
		SELECT 
			COALESCE(SUM(gross_pay), 0) as gross_pay,
			COALESCE(SUM(net_pay), 0) as net_pay,
			COALESCE(SUM(total_deduction), 0) as total_deduction,
			COUNT(*) as slip_count
		FROM `tabSalary Slip`
		WHERE employee = %s
			AND start_date >= %s
			AND end_date <= %s
			AND docstatus = 1
		""",
		(employee, year_start, year_end),
		as_dict=True,
	)

	ytd = ytd_data[0] if ytd_data else {"gross_pay": 0, "net_pay": 0, "total_deduction": 0, "slip_count": 0}

	# Latest slip
	latest_slip = frappe.db.sql(
		"""
		SELECT name, start_date, end_date, gross_pay, net_pay
		FROM `tabSalary Slip`
		WHERE employee = %s AND docstatus = 1
		ORDER BY start_date DESC
		LIMIT 1
		""",
		(employee,),
		as_dict=True,
	)

	# Monthly breakdown for the year
	monthly_breakdown = frappe.db.sql(
		"""
		SELECT 
			MONTH(start_date) as month,
			YEAR(start_date) as year,
			gross_pay,
			net_pay,
			total_deduction
		FROM `tabSalary Slip`
		WHERE employee = %s
			AND YEAR(start_date) = %s
			AND docstatus = 1
		ORDER BY start_date
		""",
		(employee, today.year),
		as_dict=True,
	)

	month_names = ["", "January", "February", "March", "April", "May", "June",
				   "July", "August", "September", "October", "November", "December"]

	monthly_data = []
	for m in monthly_breakdown:
		monthly_data.append({
			"month": month_names[m.month],
			"year": m.year,
			"gross_pay": flt(m.gross_pay, 2),
			"net_pay": flt(m.net_pay, 2),
			"total_deduction": flt(m.total_deduction, 2),
		})

	return {
		"ytd": {
			"gross_pay": flt(ytd.gross_pay, 2),
			"net_pay": flt(ytd.net_pay, 2),
			"total_deduction": flt(ytd.total_deduction, 2),
			"slip_count": ytd.slip_count,
		},
		"latest_slip": {
			"name": latest_slip[0].name,
			"month": getdate(latest_slip[0].start_date).strftime("%B"),
			"year": getdate(latest_slip[0].start_date).year,
			"gross_pay": flt(latest_slip[0].gross_pay, 2),
			"net_pay": flt(latest_slip[0].net_pay, 2),
		} if latest_slip else None,
		"monthly_breakdown": monthly_data,
	}
