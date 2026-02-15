import frappe
from frappe import _

def notify_leave_application(doc):
	"""Notify manager about new leave application"""
	if not doc.employee:
		return

	employee = frappe.get_doc("Employee", doc.employee)
	if not employee.reports_to:
		return

	manager_user = frappe.db.get_value("Employee", employee.reports_to, "user_id")
	if not manager_user:
		return

	subject = _("New Leave Application: {0}").format(employee.employee_name)
	message = _("{0} has applied for {1} from {2} to {3}.").format(
		employee.employee_name, doc.leave_type, doc.from_date, doc.to_date
	)
	
	# System Notification
	create_system_notification(manager_user, subject, message, "Leave Application", doc.name)

	# Email (if configured)
	# frappe.sendmail(recipients=[manager_user], subject=subject, message=message)


def notify_leave_status(doc):
	"""Notify employee about leave status change"""
	employee = frappe.get_doc("Employee", doc.employee)
	if not employee.user_id:
		return

	status = doc.status
	subject = _("Leave Application {0}").format(status)
	message = _("Your leave application for {0} to {1} has been {2}.").format(
		doc.from_date, doc.to_date, status
	)

	create_system_notification(employee.user_id, subject, message, "Leave Application", doc.name)


def create_system_notification(user, subject, message, ref_doctype, ref_docname):
	"""Create a standard Frappe Notification Log"""
	notification = frappe.get_doc(
		{
			"doctype": "Notification Log",
			"subject": subject,
			"email_content": message,
			"for_user": user,
			"document_type": ref_doctype,
			"document_name": ref_docname,
			"type": "Alert",
		}
	)
	notification.insert(ignore_permissions=True)
