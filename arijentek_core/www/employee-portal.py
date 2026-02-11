import frappe

no_cache = 1


def get_context(context):
	"""Serve the Employee Portal SPA.

	- Guests are redirected to the Frappe login page with a redirect-back.
	- Logged-in non-employees are redirected to the desk.
	- Logged-in employees get the SPA.
	"""
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/employee-portal"
		raise frappe.Redirect

	# Check if the user has an employee record
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if not employee:
		# System user without employee record – send to desk
		frappe.local.flags.redirect_location = "/app"
		raise frappe.Redirect

	context.no_cache = 1
	context.show_sidebar = False
