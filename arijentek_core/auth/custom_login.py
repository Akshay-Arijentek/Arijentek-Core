import frappe
from frappe import _
from frappe.auth import LoginManager

@frappe.whitelist(allow_guest=True)
def login(usr, pwd):
    # Check if login is by Employee ID
    employee_user = frappe.db.get_value("Employee", {"name": usr, "status": "Active"}, "user_id")
    if employee_user:
        usr = employee_user
    
    # Perform standard login
    login_manager = LoginManager()
    login_manager.authenticate(user=usr, pwd=pwd)
    login_manager.post_login()
    
    # Determine the correct home page
    user = frappe.session.user
    roles = frappe.get_roles(user)
    
    # For employees without System Manager role, redirect to portal
    if "Employee" in roles and "System Manager" not in roles:
        home_page = "/employee-portal"
    else:
        # Use default behavior for other users
        from frappe.apps import get_default_path
        home_page = get_default_path() or "/desk"
    
    return {
        "message": "Logged In",
        "home_page": home_page,
        "full_name": frappe.db.get_value("User", user, "full_name")
    }