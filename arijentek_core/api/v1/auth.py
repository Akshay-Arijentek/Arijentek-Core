import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

LOGIN_RATE_LIMIT = 5
LOGIN_RATE_LIMIT_SECONDS = 60


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_csrf_token():
	"""Return the CSRF token for the current session.

	This must be called (via GET) before making any POST requests,
	so that the frontend can include the token in the X-Frappe-CSRF-Token header.
	"""
	return frappe.sessions.get_csrf_token()


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=LOGIN_RATE_LIMIT, seconds=LOGIN_RATE_LIMIT_SECONDS)
def login(usr, pwd):
	usr = _sanitize_input(usr)

	if not usr or not pwd:
		frappe.throw(_("Username and password are required"))

	if len(usr) > 140:
		frappe.throw(_("Invalid username or password"))

	if not frappe.db.exists("User", usr):
		employee_user = frappe.db.get_value("Employee", {"name": usr, "status": "Active"}, "user_id")
		if employee_user:
			usr = employee_user

	try:
		login_manager = frappe.auth.LoginManager()
		login_manager.authenticate(user=usr, pwd=pwd)
		login_manager.post_login()
	except frappe.exceptions.AuthenticationError:
		frappe.clear_messages()
		frappe.throw(_("Invalid username or password"))

	user = frappe.get_doc("User", frappe.session.user)

	csrf_token = frappe.sessions.get_csrf_token()

	return {"message": "Logged In", "user": user.name, "full_name": user.full_name, "csrf_token": csrf_token}


def _sanitize_input(value: str) -> str:
	if not value:
		return ""
	value = str(value).strip()
	dangerous_patterns = ["<", ">", "'", '"', "--", ";", "/*", "*/", "eval(", "exec("]
	for pattern in dangerous_patterns:
		value = value.replace(pattern, "")
	return value[:140]
