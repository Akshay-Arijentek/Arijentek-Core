no_cache = 1

def get_context(context):
    import frappe
    
    # Require login - redirect guests to login page
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/employee-portal"
        raise frappe.Redirect
    
    # Check if user is an employee
    employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    if not employee:
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect
    
    context.no_cache = 1
    context.show_sidebar = False
