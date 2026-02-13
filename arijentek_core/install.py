"""
Arijentek Core – Post-install / Post-migrate setup.

Creates the "Employee Portal" workspace in the Frappe Desk sidebar with
shortcuts to the portal and related DocTypes (Holiday List, Leave
Application, Salary Slip).

Runs both:
  - after_install  → first-time setup
  - after_migrate  → re-create if Frappe's orphan cleanup removed it
"""

import frappe


# ── Public hooks ──────────────────────────────────────────────────────


def after_install():
	"""Called once after `bench install-app arijentek_core`."""
	_setup_employee_portal()


def after_migrate():
	"""Called after every `bench migrate` (runs *after* orphan cleanup)."""
	_setup_employee_portal()


# ── Internal helpers ──────────────────────────────────────────────────


def _setup_employee_portal():
	"""Orchestrate all setup steps."""
	_ensure_employee_role()
	_ensure_module_def()
	_create_workspace()
	frappe.db.commit()


def _ensure_employee_role():
	"""Make sure the Employee role exists and Website Users with it are
	properly restricted (desk_access=0 for Website Users via role config
	is irrelevant – Frappe blocks them by user_type).

	We do NOT set desk_access=1 here because Website Users should NOT
	reach the desk.  System Users already have desk access via their
	user_type."""
	pass  # No role modifications needed; Frappe handles access by user_type.


def _ensure_module_def():
	"""Create 'Employee Portal' Module Def so it appears as its own tile on /app."""
	module_name = "Employee Portal"
	if frappe.db.exists("Module Def", module_name):
		return

	doc = frappe.new_doc("Module Def")
	doc.update(
		{
			"module_name": module_name,
			"app_name": "arijentek_core",
			"category": "Modules",
			"color": "#14b8a6",
			"icon": "users",
			"custom": 0,
		}
	)
	doc.insert(ignore_permissions=True)


def _create_workspace():
	"""Create or update the 'Employee Portal' workspace with shortcuts."""
	ws_name = "Employee Portal"

	# Use our own module so it shows as a separate tile
	module = "Employee Portal"

	if frappe.db.exists("Workspace", ws_name):
		# Update existing workspace shortcuts
		_sync_workspace_shortcuts(ws_name)
		return

	doc = frappe.new_doc("Workspace")
	doc.update(
		{
			"title": "Employee Portal",
			"label": ws_name,
			"icon": "users",
			"module": module,
			"app": "arijentek_core",
			"type": "Workspace",
			"public": 1,
		}
	)
	doc.insert(ignore_permissions=True)

	_add_shortcuts(doc)
	doc.save(ignore_permissions=True)


def _sync_workspace_shortcuts(ws_name):
	"""Ensure the workspace has all expected shortcuts."""
	doc = frappe.get_doc("Workspace", ws_name)

	existing_labels = {s.label for s in doc.get("shortcuts", [])}
	expected = _expected_shortcuts()

	changed = False
	for sc in expected:
		if sc["label"] not in existing_labels:
			doc.append("shortcuts", sc)
			changed = True

	if changed:
		doc.save(ignore_permissions=True)


def _add_shortcuts(doc):
	"""Append all expected shortcuts to a workspace doc."""
	for sc in _expected_shortcuts():
		doc.append("shortcuts", sc)


def _expected_shortcuts():
	"""Return the list of shortcut dicts for the Employee Portal workspace."""
	shortcuts = [
		# ── Portal access ──
		{
			"type": "URL",
			"label": "Open Employee Portal",
			"url": "/employee-portal",
			"color": "#14b8a6",
		},
		# ── Portal sub-pages ──
		{
			"type": "URL",
			"label": "Clock In / Out",
			"url": "/employee-portal",
			"color": "#3b82f6",
		},
		{
			"type": "URL",
			"label": "Leave Management",
			"url": "/employee-portal#/leave",
			"color": "#f59e0b",
		},
		{
			"type": "URL",
			"label": "Payroll & Salary Slip",
			"url": "/employee-portal#/payroll",
			"color": "#8b5cf6",
		},
	]

	# ── DocType links (only if the DocType exists) ──
	doctype_links = [
		("Holiday List", "#ef4444"),
		("Leave Application", "#f59e0b"),
		("Salary Slip", "#8b5cf6"),
	]
	for dt, color in doctype_links:
		if frappe.db.exists("DocType", dt):
			shortcuts.append(
				{
					"type": "DocType",
					"label": dt,
					"link_to": dt,
					"color": color,
				}
			)

	return shortcuts
