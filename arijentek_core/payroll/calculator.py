"""
Payroll Calculator Module
=========================

Handles intelligent payroll calculation based on:
1. Attendance data (daily clock in/out or manual updates)
2. Salary structure assignments
3. Statutory deductions (Professional Tax, PF, ESI, etc.)
4. LOP (Loss of Pay) calculations

This module integrates with ERPNext's payroll system and extends it
with attendance-based calculations.
"""

import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, get_first_day, get_last_day, add_days
import calendar

from datetime import date


class PayrollCalculator:
	"""
	Calculates payroll for an employee based on attendance and salary structure.
	"""

	def __init__(self, employee, start_date, end_date):
		self.employee = employee
		self.start_date = getdate(start_date)
		self.end_date = getdate(end_date)
		self.employee_doc = frappe.get_doc("Employee", employee)
		self.salary_structure_assignment = None
		self.salary_structure = None
		self.attendance_data = []
		self.holidays = []
		self.working_days = 0
		self.days_worked = 0
		self.lop_days = 0
		self.half_days = 0

	def load_data(self):
		"""Load all required data for payroll calculation."""
		self._load_salary_structure()
		self._load_attendance()
		self._load_holidays()
		self._calculate_working_days()

	def _load_salary_structure(self):
		"""Load employee's salary structure assignment and structure."""
		ssa = frappe.db.get_value(
			"Salary Structure Assignment",
			{
				"employee": self.employee,
				"from_date": ["<=", self.end_date],
				"docstatus": 1,
			},
			["name", "salary_structure", "base", "variable"],
			as_dict=True,
			order_by="from_date desc",
		)

		if not ssa:
			frappe.throw(
				_("No Salary Structure Assignment found for employee {0}").format(self.employee)
			)

		self.salary_structure_assignment = ssa
		self.salary_structure = frappe.get_doc("Salary Structure", ssa.salary_structure)

	def _load_attendance(self):
		"""Load attendance records for the period."""
		self.attendance_data = frappe.db.sql(
			"""
			SELECT attendance_date, status, working_hours, leave_type
			FROM `tabAttendance`
			WHERE employee = %s
				AND attendance_date BETWEEN %s AND %s
				AND docstatus = 1
			ORDER BY attendance_date
			""",
			(self.employee, self.start_date, self.end_date),
			as_dict=True,
		)

	def _load_holidays(self):
		"""Load holidays for the employee's holiday list."""
		try:
			from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
			holiday_list = get_holiday_list_for_employee(self.employee, raise_exception=False)
		except Exception:
			holiday_list = self.employee_doc.holiday_list

		if not holiday_list:
			return

		self.holidays = frappe.db.sql_list(
			"""
			SELECT holiday_date
			FROM `tabHoliday`
			WHERE parent = %s
				AND holiday_date BETWEEN %s AND %s
			""",
			(holiday_list, self.start_date, self.end_date),
		)

	def _calculate_working_days(self):
		"""Calculate working days, days worked, and LOP days."""
		# Total days in month
		total_days = calendar.monthrange(self.start_date.year, self.start_date.month)[1]

		# Count holidays
		holiday_count = len(self.holidays)

		# Working days = Total days - Sundays - Holidays
		sundays = sum(
			1 for d in range(total_days)
			if date(self.start_date.year, self.start_date.month, d + 1).weekday() == 6
		)

		self.working_days = total_days - sundays - holiday_count

		# Calculate days worked and LOP from attendance
		present_days = 0
		self.half_days = 0
		self.lop_days = 0
		paid_leave_days = 0

		# Get LOP leave types
		lop_leave_types = frappe.db.sql_list(
			"""SELECT name FROM `tabLeave Type` WHERE is_lwp = 1"""
		)

		for att in self.attendance_data:
			if att.status == "Present":
				present_days += 1
			elif att.status == "Half Day":
				self.half_days += 1
				# Check if half day is due to LOP leave
				if att.leave_type and att.leave_type in lop_leave_types:
					self.lop_days += 0.5
			elif att.status == "On Leave":
				# Check if it's LOP
				if att.leave_type and att.leave_type in lop_leave_types:
					self.lop_days += 1
				else:
					paid_leave_days += 1
			elif att.status == "Absent":
				self.lop_days += 1

		# Days worked = Present + Half Days (0.5 each)
		self.days_worked = present_days + (self.half_days * 0.5)

	def get_payment_days(self):
		"""
		Get the number of payment days for the period.
		Payment days = Days worked (excluding LOP) - Inactive Days (before joining / after relieving)
		"""
		inactive_days = self._calculate_inactive_days()
		return max(0, self.working_days - self.lop_days - inactive_days)

	def _calculate_inactive_days(self):
		"""Calculate days the employee was not active in the month (before joining or after relieving)."""
		total_days = calendar.monthrange(self.start_date.year, self.start_date.month)[1]
		inactive = 0
		
		# Pro-rate for joining mid-month
		if self.employee_doc.date_of_joining and self.employee_doc.date_of_joining > self.start_date:
			# Count days from start_date to date_of_joining - 1
			# BUT only subtract if they are "Working Days" (not holidays/weekends), 
			# otherwise we double subtract if working_days already excluded them.
			# Actually, standard practice: Payment Days = Total Active Days - LOP.
			# So we need "Active Working Days".
			
			# Let's count "Active Days" in the month
			joining_date = self.employee_doc.date_of_joining
			relieving_date = self.employee_doc.relieving_date or self.end_date
			
			# Intersection of [start_date, end_date] and [joining_date, relieving_date]
			active_start = max(self.start_date, joining_date)
			active_end = min(self.end_date, relieving_date)
			
			if active_start > active_end:
				return self.working_days # Total inactive
				
			# Calculate working days in the ACTIVE period
			# This is better than subtracting inactive.
			# Refactoring _calculate_working_days might be cleaner, but let's do it here to minimize impact.
			
			# Re-calculate working days for the ACTIVE period only?
			# No, self.working_days is currently "Total Days in Month - Weekends - Holidays".
			# We want to subtract "Working Days that fell in the inactive period".
			
			# Inactive Period 1: start_date to active_start - 1
			if active_start > self.start_date:
				curr = self.start_date
				while curr < active_start:
					if not self._is_holiday_or_weekend(curr):
						inactive += 1
					curr = add_days(curr, 1)

			# Inactive Period 2: active_end + 1 to end_date
			if active_end < self.end_date:
				curr = add_days(active_end, 1)
				while curr <= self.end_date:
					if not self._is_holiday_or_weekend(curr):
						inactive += 1
					curr = add_days(curr, 1)
					
		return inactive

	def _is_holiday_or_weekend(self, date_obj):
		"""Check if a date is a weekend (Sunday) or Holiday."""
		if date_obj.weekday() == 6: # Sunday
			return True
		
		if str(date_obj) in [str(h) for h in self.holidays]:
			return True
			
		return False

	def calculate_earnings(self):
		"""Calculate earnings based on salary structure and payment days."""
		earnings = []
		payment_days = self.get_payment_days()

		if not self.salary_structure:
			return earnings

		for earning in self.salary_structure.earnings:
			amount = self._calculate_component_amount(earning, payment_days)
			if amount > 0:
				earnings.append({
					"salary_component": earning.salary_component,
					"abbr": earning.abbr,
					"amount": flt(amount, 2),
					"type": "Earning",
				})

		return earnings

	def calculate_deductions(self):
		"""Calculate all deductions including statutory deductions."""
		deductions = []
		payment_days = self.get_payment_days()
		gross_pay = self._get_gross_pay_for_deductions()

		# Process salary structure deductions
		if self.salary_structure:
			for deduction in self.salary_structure.deductions:
				amount = self._calculate_component_amount(deduction, payment_days, gross_pay)
				if amount > 0:
					deductions.append({
						"salary_component": deduction.salary_component,
						"abbr": deduction.abbr,
						"amount": flt(amount, 2),
						"type": "Deduction",
					})

		# Add statutory deductions
		# User requested strict structure (Basic + PT 200 only).
		# Disabling automatic statutory logic to prevent duplication and unwanted PF/ESI.
		# statutory_deductions = self._calculate_statutory_deductions(gross_pay, payment_days)
		# deductions.extend(statutory_deductions)

		return deductions

	def _calculate_component_amount(self, component, payment_days, gross_pay=0):
		"""
		Calculate amount for a salary component.
		Handles formula-based and fixed amounts.
		"""
		base = flt(self.salary_structure_assignment.base) if self.salary_structure_assignment else 0

		# Check if amount depends on payment days
		depends_on_payment_days = component.get("depends_on_payment_days", 1)

		if component.amount:
			amount = flt(component.amount)
		elif component.formula:
			amount = self._evaluate_formula(component.formula, base, gross_pay, payment_days)
		else:
			# Get default amount from salary component
			default_amount = frappe.db.get_value(
				"Salary Component", component.salary_component, "amount"
			) or 0
			amount = flt(default_amount)

		# Prorate based on payment days if applicable
		if depends_on_payment_days and self.working_days > 0:
			amount = (amount / self.working_days) * payment_days

		return flt(amount, 2)

	def _evaluate_formula(self, formula, base, gross_pay, payment_days):
		"""Evaluate a salary component formula."""
		# Common variables available in formulas
		context = {
			"base": base,
			"BASE": base,
			"gross_pay": gross_pay,
			"GROSS_PAY": gross_pay,
			"payment_days": payment_days,
			"PAYMENT_DAYS": payment_days,
			"working_days": self.working_days,
			"WORKING_DAYS": self.working_days,
			"lop_days": self.lop_days,
			"LOP_DAYS": self.lop_days,
		}

		try:
			# Ensure 'base' is float
			context["base"] = flt(context["base"])

			amount = frappe.safe_eval(formula, eval_globals={"flt": flt, "int": int, "cint": cint}, eval_locals=context)
			return flt(amount, 2)
		except Exception as e:
			frappe.log_error(f"Formula Error: {formula} | Context: {context} | Error: {e}", "Payroll Formula Error")
			return 0

	def _get_gross_pay_for_deductions(self):
		"""Get gross pay for calculating percentage-based deductions."""
		gross = 0
		for earning in self.calculate_earnings():
			gross += earning["amount"]
		return gross

	def _calculate_statutory_deductions(self, gross_pay, payment_days):
		"""
		Calculate statutory deductions:
		- Professional Tax (PT)
		- Provident Fund (PF)
		- ESI (Employee State Insurance)
		"""
		deductions = []

		# Professional Tax - State-wise fixed amount
		pt_deduction = self._calculate_professional_tax(gross_pay)
		if pt_deduction:
			deductions.append(pt_deduction)

		# Provident Fund - 12% of Basic (employee contribution)
		pf_deduction = self._calculate_provident_fund(gross_pay)
		if pf_deduction:
			deductions.append(pf_deduction)

		# ESI - 0.75% of gross if applicable
		esi_deduction = self._calculate_esi(gross_pay)
		if esi_deduction:
			deductions.append(esi_deduction)

		return deductions

	def _calculate_professional_tax(self, gross_pay):
		"""
		Calculate Professional Tax based on state rules.
		PT is a state-level tax with fixed slabs.
		"""
		# Check if PT component exists in salary structure
		pt_component = frappe.db.get_value(
			"Salary Component",
			{"component_type": "Professional Tax", "disabled": 0},
			["name", "salary_component_abbr", "amount"],
			as_dict=True,
		)

		if not pt_component:
			# Create default PT deduction based on common slabs
			# Most states have PT between ₹150-200 per month
			pt_amount = self._get_pt_amount_by_state(gross_pay)
			if pt_amount > 0:
				return {
					"salary_component": "Professional Tax",
					"abbr": "PT",
					"amount": pt_amount,
					"type": "Deduction",
				}
			return None

		# Use configured PT amount
		pt_amount = flt(pt_component.amount) if pt_component.amount else self._get_pt_amount_by_state(gross_pay)

		if pt_amount > 0:
			return {
				"salary_component": pt_component.name,
				"abbr": pt_component.salary_component_abbr,
				"amount": pt_amount,
				"type": "Deduction",
			}

		return None

	def _get_pt_amount_by_state(self, gross_pay):
		"""
		Get Professional Tax amount based on employee's state and gross pay.
		Common PT slabs in India:
		- Up to ₹15,000: ₹0
		- ₹15,001 to ₹25,000: ₹150
		- Above ₹25,000: ₹200
		"""
		# Get employee's state from address
		state = self._get_employee_state()

		# Default slabs (can be customized per state)
		if gross_pay <= 15000:
			return 0
		elif gross_pay <= 25000:
			return 150
		else:
			return 200

	def _get_employee_state(self):
		"""Get employee's state from permanent address."""
		return self.employee_doc.get("permanent_address") or ""

	def _calculate_provident_fund(self, gross_pay):
		"""
		Calculate Provident Fund (PF) deduction.
		Standard: 12% of Basic Salary (employee contribution)
		"""
		# Check if PF is applicable
		if not self._is_pf_applicable():
			return None

		# Get Basic salary component
		basic_amount = self._get_basic_salary()

		if basic_amount <= 0:
			return None

		# PF rate (12% standard, can be configured)
		pf_rate = self._get_pf_rate()
		pf_amount = basic_amount * (pf_rate / 100)

		# Check for PF wage ceiling (₹15,000 as of 2024)
		pf_wage_ceiling = 15000
		if basic_amount > pf_wage_ceiling:
			# Option 1: PF on actual basic
			# Option 2: PF on ceiling amount
			# Using actual basic as most companies prefer this
			pass

		# Check if PF component exists
		pf_component = frappe.db.get_value(
			"Salary Component",
			{"component_type": ["in", ["Provident Fund", "PF"]], "disabled": 0},
			["name", "salary_component_abbr"],
			as_dict=True,
		)

		component_name = pf_component.name if pf_component else "Provident Fund"
		abbr = pf_component.salary_component_abbr if pf_component else "PF"

		return {
			"salary_component": component_name,
			"abbr": abbr,
			"amount": flt(pf_amount, 2),
			"type": "Deduction",
		}

	def _is_pf_applicable(self):
		"""Check if PF is applicable for the employee."""
		# Check employee's PF Applicable flag
		pf_applicable = self.employee_doc.get("pf_applicable")
		if pf_applicable is not None:
			return cint(pf_applicable)

		# Default: PF applicable if Basic + DA <= 15000 or company is covered under EPF
		return True  # Default to applicable

	def _get_pf_rate(self):
		"""Get PF contribution rate."""
		# Standard rate is 12%
		try:
			return frappe.db.get_single_value("Payroll Settings", "pf_rate") or 12
		except Exception:
			return 12

	def _get_basic_salary(self):
		"""Get Basic salary amount from earnings."""
		for earning in self.salary_structure.earnings if self.salary_structure else []:
			if earning.salary_component == "Basic" or earning.abbr == "B":
				if earning.amount:
					return flt(earning.amount)
				elif earning.formula:
					base = flt(self.salary_structure_assignment.base) if self.salary_structure_assignment else 0
					return self._evaluate_formula(earning.formula, base, 0, self.working_days)

		# If no Basic component, use base salary
		return flt(self.salary_structure_assignment.base) if self.salary_structure_assignment else 0

	def _calculate_esi(self, gross_pay):
		"""
		Calculate ESI (Employee State Insurance) deduction.
		Rate: 0.75% of gross pay (employee contribution)
		Applicable if gross monthly salary <= ₹21,000
		"""
		esi_ceiling = 21000

		if gross_pay > esi_ceiling:
			return None

		# Check if ESI is applicable for employee
		if not self._is_esi_applicable():
			return None

		esi_rate = 0.75  # Employee contribution rate
		esi_amount = gross_pay * (esi_rate / 100)

		# Check if ESI component exists (by name since component_type doesn't support ESI)
		esi_component = frappe.db.get_value(
			"Salary Component",
			{"salary_component": "ESI", "disabled": 0},
			["name", "salary_component_abbr"],
			as_dict=True,
		)

		component_name = esi_component.name if esi_component else "ESI"
		abbr = esi_component.salary_component_abbr if esi_component else "ESI"

		return {
			"salary_component": component_name,
			"abbr": abbr,
			"amount": flt(esi_amount, 2),
			"type": "Deduction",
		}

	def _is_esi_applicable(self):
		"""Check if ESI is applicable for the employee."""
		esi_applicable = self.employee_doc.get("esi_applicable")
		if esi_applicable is not None:
			return cint(esi_applicable)

		# Default: Check company's ESI applicability
		return False  # Default to not applicable

	def calculate_payroll(self):
		"""
		Main method to calculate complete payroll.
		Returns a dictionary with all payroll details.
		"""
		self.load_data()

		earnings = self.calculate_earnings()
		deductions = self.calculate_deductions()

		gross_pay = sum(e["amount"] for e in earnings)
		total_deduction = sum(d["amount"] for d in deductions)
		net_pay = gross_pay - total_deduction

		return {
			"employee": self.employee,
			"employee_name": self.employee_doc.employee_name,
			"department": self.employee_doc.department,
			"designation": self.employee_doc.designation,
			"salary_structure": self.salary_structure.name if self.salary_structure else None,
			"salary_structure_assignment": self.salary_structure_assignment.name if self.salary_structure_assignment else None,
			"start_date": str(self.start_date),
			"end_date": str(self.end_date),
			"working_days": self.working_days,
			"payment_days": self.get_payment_days(),
			"lop_days": self.lop_days,
			"half_days": self.half_days,
			"earnings": earnings,
			"deductions": deductions,
			"gross_pay": flt(gross_pay, 2),
			"total_deduction": flt(total_deduction, 2),
			"net_pay": flt(net_pay, 2),
		}


@frappe.whitelist()
def calculate_employee_payroll(employee, start_date, end_date):
	"""
	API endpoint to calculate payroll for an employee.

	Args:
		employee: Employee ID
		start_date: Pay period start date
		end_date: Pay period end date

	Returns:
		Dictionary with complete payroll breakdown
	"""
	calculator = PayrollCalculator(employee, start_date, end_date)
	return calculator.calculate_payroll()


@frappe.whitelist()
def get_payroll_preview(employee, month, year):
	"""
	Get a preview of payroll calculation for an employee.

	Args:
		employee: Employee ID
		month: Month (1-12)
		year: Year (e.g., 2024)

	Returns:
		Dictionary with payroll preview
	"""
	month = cint(month)
	year = cint(year)

	start_date = getdate(f"{year}-{month:02d}-01")
	end_date = getdate(f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]}")

	return calculate_employee_payroll(employee, start_date, end_date)


def get_lop_summary(employee, start_date, end_date):
	"""
	Get LOP (Loss of Pay) summary for an employee.

	Returns:
		Dictionary with LOP days, half day LOP, and total LOP equivalent
	"""
	lop_leave_types = frappe.db.sql_list(
		"""SELECT name FROM `tabLeave Type` WHERE is_lwp = 1"""
	)

	attendance = frappe.db.sql(
		"""
		SELECT status, leave_type, COUNT(*) as count
		FROM `tabAttendance`
		WHERE employee = %s
			AND attendance_date BETWEEN %s AND %s
			AND docstatus = 1
		GROUP BY status, leave_type
		""",
		(employee, start_date, end_date),
		as_dict=True,
	)

	lop_days = 0
	half_day_lop = 0

	for att in attendance:
		if att.status == "Absent":
			lop_days += att.count
		elif att.status == "On Leave" and att.leave_type in lop_leave_types:
			lop_days += att.count
		elif att.status == "Half Day":
			if att.leave_type in lop_leave_types:
				half_day_lop += att.count
				lop_days += 0.5 * att.count

	return {
		"lop_days": lop_days,
		"half_day_lop": half_day_lop,
		"total_lop_equivalent": lop_days,
	}
