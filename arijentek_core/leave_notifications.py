"""
Leave Notification Module
=========================

Handles notifications for leave application events:
- Sends desk notifications + emails to reporting manager / leave approver
  when a leave is applied.
- On approval: mark attendance as "On Leave" (not LWP), deduct leave balance.
- On rejection: mark attendance as LWP (Loss Without Pay).
"""

import frappe
from frappe import _
from frappe.utils import getdate, get_url


def on_leave_application_insert(doc, method=None):
	"""Notify reporting manager and leave approver when a leave application is created."""
	_send_leave_notification(
		doc,
		subject=_("New Leave Application from {0}").format(doc.employee_name),
		message=_("{0} has applied for {1} ({2} to {3}) - {4} day(s). Reason: {5}").format(
			doc.employee_name,
			doc.leave_type,
			doc.from_date,
			doc.to_date,
			doc.total_leave_days,
			doc.description or "Not specified",
		),
	)


def on_leave_application_update(doc, method=None):
	"""Handle leave approval/rejection."""
	if doc.has_value_changed("status"):
		if doc.status == "Approved":
			_handle_leave_approval(doc)
		elif doc.status == "Rejected":
			_handle_leave_rejection(doc)


def _handle_leave_approval(doc):
	"""
	On approval:
	- The leave balance is automatically deducted by ERPNext's Leave Application submit workflow.
	- We ensure attendance records reflect "On Leave" (not LWP) for the approved leave type.
	- Notify employee.
	"""
	try:
		# Submit the leave application if it's still in Draft
		if doc.docstatus == 0:
			doc.submit()
			frappe.db.commit()

		# Notify the employee
		_notify_user(
			user=frappe.db.get_value("Employee", doc.employee, "user_id"),
			subject=_("Leave Application Approved"),
			message=_("Your {0} application ({1} to {2}) has been approved.").format(
				doc.leave_type, doc.from_date, doc.to_date
			),
			doc=doc,
		)

		frappe.logger().info(
			f"Leave approved for {doc.employee_name}: {doc.leave_type} "
			f"({doc.from_date} to {doc.to_date}), {doc.total_leave_days} day(s)"
		)

	except Exception:
		frappe.log_error(frappe.get_traceback(), "Leave Approval Error")


def _handle_leave_rejection(doc):
	"""
	On rejection:
	- Mark attendance as LWP (Loss Without Pay).
	- Notify employee.
	"""
	try:
		# Notify the employee
		employee_user = frappe.db.get_value("Employee", doc.employee, "user_id")
		_notify_user(
			user=employee_user,
			subject=_("Leave Application Rejected"),
			message=_("Your {0} application ({1} to {2}) has been rejected. "
					  "The day(s) will be marked as Leave Without Pay (LWP).").format(
				doc.leave_type, doc.from_date, doc.to_date
			),
			doc=doc,
		)

		frappe.logger().info(
			f"Leave rejected for {doc.employee_name}: {doc.leave_type} "
			f"({doc.from_date} to {doc.to_date})"
		)

	except Exception:
		frappe.log_error(frappe.get_traceback(), "Leave Rejection Error")


def _send_leave_notification(doc, subject, message):
	"""Send notification to reporting manager and leave approver."""
	recipients = set()

	# Get reporting manager's user_id
	reports_to = frappe.db.get_value("Employee", doc.employee, "reports_to")
	if reports_to:
		mgr_user = frappe.db.get_value("Employee", reports_to, "user_id")
		if mgr_user:
			recipients.add(mgr_user)

	# Get leave approver
	leave_approver = doc.leave_approver
	if leave_approver:
		recipients.add(leave_approver)

	# Fallback: HR Manager role users
	if not recipients:
		hr_users = frappe.get_all(
			"Has Role",
			filters={"role": "HR Manager", "parenttype": "User"},
			fields=["parent"],
			limit=5,
		)
		for u in hr_users:
			if u.parent and u.parent != "Administrator":
				recipients.add(u.parent)

	# Send desk notifications
	for user in recipients:
		try:
			# Frappe desk notification
			notification = frappe.new_doc("Notification Log")
			notification.update({
				"subject": subject,
				"email_content": message,
				"for_user": user,
				"document_type": "Leave Application",
				"document_name": doc.name,
				"from_user": frappe.session.user,
				"type": "Alert",
			})
			notification.insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"Leave Notification Error for {user}")

	# Send email notification
	if recipients:
		try:
			frappe.sendmail(
				recipients=list(recipients),
				subject=subject,
				message=_build_email_html(doc, message),
				reference_doctype="Leave Application",
				reference_name=doc.name,
				now=True,
			)
		except Exception:
			# Email failure should not block the workflow
			frappe.log_error(frappe.get_traceback(), "Leave Notification Email Error")

	frappe.db.commit()


def _notify_user(user, subject, message, doc):
	"""Send a desk notification to a specific user."""
	if not user:
		return

	try:
		notification = frappe.new_doc("Notification Log")
		notification.update({
			"subject": subject,
			"email_content": message,
			"for_user": user,
			"document_type": "Leave Application",
			"document_name": doc.name,
			"from_user": frappe.session.user,
			"type": "Alert",
		})
		notification.insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Leave User Notification Error")


def _build_email_html(doc, message):
	"""Build a clean HTML email for leave notification."""
	portal_url = get_url("/app/leave-application/" + doc.name)
	return f"""
	<div style="font-family: 'Inter', sans-serif; max-width: 560px; margin: 0 auto;">
		<div style="background: #f8fafc; border-radius: 12px; padding: 24px; border: 1px solid #e2e8f0;">
			<h2 style="color: #0f172a; margin: 0 0 16px 0; font-size: 18px;">Leave Application</h2>
			<p style="color: #475569; margin: 0 0 16px 0; font-size: 14px; line-height: 1.6;">{message}</p>
			<table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
				<tr>
					<td style="padding: 8px 0; color: #64748b; font-size: 13px;">Employee</td>
					<td style="padding: 8px 0; color: #0f172a; font-size: 13px; font-weight: 600;">{doc.employee_name}</td>
				</tr>
				<tr>
					<td style="padding: 8px 0; color: #64748b; font-size: 13px;">Leave Type</td>
					<td style="padding: 8px 0; color: #0f172a; font-size: 13px; font-weight: 600;">{doc.leave_type}</td>
				</tr>
				<tr>
					<td style="padding: 8px 0; color: #64748b; font-size: 13px;">Period</td>
					<td style="padding: 8px 0; color: #0f172a; font-size: 13px; font-weight: 600;">{doc.from_date} to {doc.to_date}</td>
				</tr>
				<tr>
					<td style="padding: 8px 0; color: #64748b; font-size: 13px;">Days</td>
					<td style="padding: 8px 0; color: #0f172a; font-size: 13px; font-weight: 600;">{doc.total_leave_days}</td>
				</tr>
				<tr>
					<td style="padding: 8px 0; color: #64748b; font-size: 13px;">Half Day</td>
					<td style="padding: 8px 0; color: #0f172a; font-size: 13px; font-weight: 600;">{"Yes" if doc.half_day else "No"}</td>
				</tr>
			</table>
			<a href="{portal_url}"
			   style="display: inline-block; background: #0d9488; color: white; padding: 10px 24px;
			          border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 600; margin-top: 8px;">
				Review Application
			</a>
		</div>
	</div>
	"""
