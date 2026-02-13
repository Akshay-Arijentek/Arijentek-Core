import frappe

PORTAL_PATH = "/employee-portal"


# ---------- Hook: get_website_user_home_page ----------
# Everyone lands on Employee Portal first. System Users can go to desk via "Open Desk" button.


def get_employee_home_page(user: str):
	"""Frappe hook – returns the home page URL. ALL users land on portal first."""
	if user == "Guest":
		return None
	return PORTAL_PATH


# ---------- Hook: on_session_creation (called from security.py) ----------


def redirect_employee_after_login(login_manager=None, *args, **kwargs):
	"""Set redirect so ALL users land on Employee Portal after login."""
	frappe.local.flags.home_page = PORTAL_PATH.lstrip("/")
	frappe.local.response["home_page"] = PORTAL_PATH
	frappe.local.response["redirect_to"] = PORTAL_PATH


# ---------- Hook: boot_session ----------


def redirect_employee_on_boot(bootinfo):
	"""Do NOT set home_page here. It would make the desk try to load
	'employee-portal' as a desk workspace, causing 'Page employee-portal not found'.
	Login redirect (custom_login + redirect_employee_after_login) already sends
	everyone to the portal first. When System Users click 'Open Desk', the desk
	should use its normal default (apps grid), not try to load the portal.
	"""
	pass


# ---------- Permission check for add_to_apps_screen ----------


def has_portal_permission():
	"""Return True for any logged-in System User (for apps screen tile)."""
	user = frappe.session.user
	if user == "Guest":
		return False
	user_type = frappe.db.get_value("User", user, "user_type")
	return user_type == "System User"
