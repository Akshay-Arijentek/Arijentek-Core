import frappe

PORTAL_PATH = "/employee-portal"


def _is_portal_employee(user: str) -> bool:
	"""Return True if the user is an Employee WITHOUT System Manager role."""
	if user == "Guest":
		return False
	roles = frappe.get_roles(user)
	return "Employee" in roles and "System Manager" not in roles


# ---------- Hook: get_website_user_home_page ----------


def get_employee_home_page(user: str):
	"""Frappe hook – returns the home page URL for website users."""
	if _is_portal_employee(user):
		return PORTAL_PATH
	return None  # let Frappe decide


# ---------- Hook: on_session_creation (called from security.py) ----------


def redirect_employee_after_login(login_manager=None, *args, **kwargs):
	"""Set redirect flags so Frappe sends the employee to the portal."""
	user = frappe.session.user
	if _is_portal_employee(user):
		frappe.local.flags.home_page = PORTAL_PATH.lstrip("/")
		frappe.local.response["home_page"] = PORTAL_PATH
		frappe.local.response["redirect_to"] = PORTAL_PATH


# ---------- Hook: boot_session ----------


def redirect_employee_on_boot(bootinfo):
	"""If a portal-only employee somehow loads the desk, redirect them."""
	user = frappe.session.user
	if user == "Guest":
		return
	if _is_portal_employee(user):
		bootinfo.home_page = PORTAL_PATH.lstrip("/")
