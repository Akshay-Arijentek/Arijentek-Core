"""
Payroll Setup Module
====================

Creates default salary components for Indian payroll:
- Basic Salary
- House Rent Allowance (HRA)
- Conveyance Allowance
- Medical Allowance
- Special Allowance
- Professional Tax (PT)
- Provident Fund (PF)
- ESI (Employee State Insurance)
- TDS (Tax Deducted at Source)

Run via: bench execute arijentek_core.payroll.setup.create_default_salary_components
"""

import frappe
from frappe import _


def create_default_salary_components(company=None):
	"""
	Create default salary components for Indian payroll.

	Args:
		company: Company to create components for (optional, creates for all if not specified)
	"""
	# Earnings components
	earnings = [
		{
			"salary_component": "Basic",
			"salary_component_abbr": "B",
			"type": "Earning",
			"description": "Basic Salary",
			"depends_on_payment_days": 1,
			"is_tax_applicable": 1,
		},
	]

	# Deduction components
	deductions = [
		{
			"salary_component": "Professional Tax",
			"salary_component_abbr": "PT",
			"type": "Deduction",
			"description": "Professional Tax (State Levy)",
			"component_type": "Professional Tax",
			"depends_on_payment_days": 0,
			"exempted_from_income_tax": 1,
			"amount": 200,  # Fixed amount as per user request
		},
	]

	created_count = 0
	updated_count = 0

	for component in earnings + deductions:
		existing = frappe.db.exists("Salary Component", component["salary_component"])

		if existing:
			# Update existing component
			doc = frappe.get_doc("Salary Component", existing)
			doc.update(component)
			doc.save()
			updated_count += 1
		else:
			# Create new component
			doc = frappe.new_doc("Salary Component")
			doc.update(component)
			doc.insert()
			created_count += 1

		# Set company-specific accounts if company provided
		if company:
			_set_component_account(doc.name, company, component["type"])

	frappe.db.commit()

	return {
		"created": created_count,
		"updated": updated_count,
		"message": f"Created {created_count} new components, updated {updated_count} existing components",
	}


def _set_component_account(component_name, company, component_type):
	"""
	Set default account for a salary component.

	Args:
		component_name: Name of the salary component
		company: Company name
		component_type: "Earning" or "Deduction"
	"""
	# Get default accounts for the company
	if component_type == "Earning":
		account_name = f"Salary - {company}"
		account_type = "Expense Account"
	else:
		account_name = f"Salary Deductions - {company}"
		account_type = "Liability Account"

	# Check if account exists
	account = frappe.db.get_value(
		"Account",
		{"company": company, "account_name": account_name},
		"name"
	)

	if not account:
		return

	# Check if component account already exists
	existing = frappe.db.exists(
		"Salary Component Account",
		{"parent": component_name, "company": company}
	)

	if existing:
		return

	# Add account to component
	component = frappe.get_doc("Salary Component", component_name)
	component.append("accounts", {
		"company": company,
		"account": account,
	})
	component.save()


def create_default_salary_structure(company=None, name="Standard Salary Structure"):
	"""
	Create a default salary structure with common components.

	Args:
		company: Company name
		name: Name for the salary structure
	"""
	if not company:
		company = frappe.defaults.get_user_default("company")

	if not company:
		frappe.throw(_("Please specify a company"))

	# Check if structure already exists
	if frappe.db.exists("Salary Structure", name):
		return {"message": f"Salary Structure '{name}' already exists"}

	# Create salary structure
	structure = frappe.new_doc("Salary Structure")
	structure.update({
		"name": name,
		"company": company,
		"payroll_frequency": "Monthly",
		"is_active": "Yes",
	})

	# Add earnings
	earnings = [
		{"salary_component": "Basic", "formula": "base", "idx": 1},
	]

	for e in earnings:
		structure.append("earnings", {
			"salary_component": e["salary_component"],
			"formula": e["formula"],
			"idx": e["idx"],
			"depends_on_payment_days": 1,
		})

	# Add deductions
	deductions = [
		{"salary_component": "Professional Tax", "amount": 200, "idx": 1},
	]

	for d in deductions:
		structure.append("deductions", {
			"salary_component": d["salary_component"],
			"formula": d.get("formula"),
			"amount": d.get("amount"),
			"idx": d["idx"],
			"depends_on_payment_days": d.get("depends_on_payment_days", 1),
		})

	structure.insert()
	frappe.db.commit()

	return {
		"message": f"Created salary structure '{name}'",
		"structure": structure.name,
	}


@frappe.whitelist()
def setup_payroll_for_company(company=None):
	"""
	Complete payroll setup for a company.

	Creates:
	1. Default salary components
	2. Default salary structure

	Args:
		company: Company name (defaults to user's default company)
	"""
	if not company:
		company = frappe.defaults.get_user_default("company")

	if not company:
		frappe.throw(_("Please specify a company"))

	# Create components
	components_result = create_default_salary_components(company)

	# Create structure
	structure_result = create_default_salary_structure(company)

	return {
		"company": company,
		"components": components_result,
		"structure": structure_result,
		"message": f"Payroll setup completed for {company}",
	}


@frappe.whitelist()
def get_payroll_setup_status(company=None):
	"""
	Check payroll setup status for a company.

	Returns:
		Dictionary with setup status for components and structures
	"""
	if not company:
		company = frappe.defaults.get_user_default("company")

	# Check salary components
	components = frappe.db.sql(
		"""
		SELECT name, type, component_type
		FROM `tabSalary Component`
		WHERE disabled = 0
		""",
		as_dict=True,
	)

	# Check salary structures
	structures = frappe.db.sql(
		"""
		SELECT name, is_active
		FROM `tabSalary Structure`
		WHERE company = %s
		""",
		(company,),
		as_dict=True,
	)

	# Check salary structure assignments
	assignments = frappe.db.sql(
		"""
		SELECT COUNT(*) as count
		FROM `tabSalary Structure Assignment` ssa
		INNER JOIN `tabEmployee` e ON e.name = ssa.employee
		WHERE e.company = %s AND ssa.docstatus = 1
		""",
		(company,),
		as_dict=True,
	)

	has_earnings = any(c.type == "Earning" for c in components)
	has_deductions = any(c.type == "Deduction" for c in components)
	has_pt = any(c.component_type == "Professional Tax" for c in components)
	has_pf = any(c.component_type == "Provident Fund" for c in components)

	return {
		"company": company,
		"components_count": len(components),
		"structures_count": len(structures),
		"assignments_count": assignments[0].count if assignments else 0,
		"has_earnings": has_earnings,
		"has_deductions": has_deductions,
		"has_professional_tax": has_pt,
		"has_provident_fund": has_pf,
		"is_setup_complete": (
			has_earnings and has_deductions and
			len(structures) > 0 and
			assignments[0].count > 0 if assignments else False
		),
		"components": components,
		"structures": structures,
	}
