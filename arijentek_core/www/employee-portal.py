import frappe

no_cache = 1


def get_context(context):
	"""Serve the Employee Portal SPA.

	Only guests are redirected to login. ALL logged-in users can view the
	portal — the Vue SPA handles role-based display internally.
	"""
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/employee-portal"
		raise frappe.Redirect

	context.no_cache = 1
	context.show_sidebar = False
