import frappe
from frappe import _
from frappe.auth import LoginManager
from frappe.utils import get_site_url


@frappe.whitelist(allow_guest=True)
def login(usr, pwd):
	"""
	Custom Login Logic:
	1. Supports login by Employee ID.
	2. Returns CSRF Token for SPA dev server.
	3. Bypasses CSRF check for guest login endpoint.
	"""

	# Skip CSRF validation for this guest endpoint
	frappe.local.flags.ignore_csrf = True

	# 1. Check if username is actually an Employee ID
	employee_doc = frappe.db.get_value("Employee", {"name": usr, "status": "Active"}, "user_id")
	actual_usr = employee_doc if employee_doc else usr

	# 2. Perform Standard Frappe Authentication
	login_manager = LoginManager()
	login_manager.authenticate(user=actual_usr, pwd=pwd)
	login_manager.post_login()

	# 3. Post-Login Redirect: EVERY user lands on Employee Portal first
	home_page = "/employee-portal"

	# 4. Generate response with CSRF Token for subsequent requests
	csrf_token = frappe.sessions.get_csrf_token()

	# Get site URL for proper origins
	site_url = get_site_url(frappe.local.site)

	return {
		"message": "Logged In",
		"home_page": home_page,
		"full_name": frappe.utils.get_fullname(user),
		"csrf_token": csrf_token,
		"sid": frappe.session.sid,
		"site_url": site_url,
	}
