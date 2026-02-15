import frappe
from frappe import _

BLOCKED_USER_AGENTS = ["sqlmap", "nikto", "nmap", "masscan", "zap", "burp"]
SUSPICIOUS_PATTERNS = ["../", "..\\", "etc/passwd", "cmd.exe", "union select", "drop table"]


def validate_request():
	_check_user_agent()
	_check_suspicious_patterns()
	_enforce_content_type()


def _check_user_agent():
	user_agent = frappe.get_request_header("User-Agent", "")
	if not user_agent:
		return

	user_agent_lower = user_agent.lower()
	for blocked in BLOCKED_USER_AGENTS:
		if blocked in user_agent_lower:
			frappe.log_error(f"Blocked suspicious user agent: {user_agent}", "Security: Blocked Request")
			frappe.throw(_("Request blocked"))


def _check_suspicious_patterns():
	request_data = []
	request_data.extend(frappe.request.args.values())

	if frappe.request.method == "POST":
		try:
			if hasattr(frappe.local, "request_form") and frappe.local.request_form:
				form_data = frappe.local.request_form or {}
				request_data.extend(form_data.values())
		except (AttributeError, TypeError):
			pass

	for data in request_data:
		if not data:
			continue
		data_lower = str(data).lower()
		for pattern in SUSPICIOUS_PATTERNS:
			if pattern in data_lower:
				frappe.log_error(
					f"Suspicious pattern detected: {pattern} in {data[:100]}", "Security: Suspicious Request"
				)
				frappe.throw(_("Invalid request"))


def _enforce_content_type():
	if frappe.request.method == "POST":
		content_type = frappe.get_request_header("Content-Type", "")
		if content_type and "application/json" not in content_type:
			if (
				"multipart/form-data" not in content_type
				and "application/x-www-form-urlencoded" not in content_type
			):
				frappe.log_error(f"Invalid content type: {content_type}", "Security: Invalid Content-Type")
				frappe.throw(_("Invalid content type"))


def log_attendance_event(doc, method):
	frappe.logger("attendance").info(
		{
			"event": method,
			"doctype": doc.doctype,
			"name": doc.name,
			"employee": doc.get("employee"),
			"user": frappe.session.user,
			"ip": frappe.local.request_ip if hasattr(frappe.local, "request_ip") else "system",
			"timestamp": frappe.utils.now_datetime().isoformat(),
		}
	)


def on_session_created(login_manager):
	from arijentek_core.utils import redirect_employee_after_login

	redirect_employee_after_login(login_manager)
