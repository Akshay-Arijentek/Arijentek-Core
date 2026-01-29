import frappe

def get_employee_home_page(user):
    """
    Frappe v16 hook: get_website_user_home_page
    Called when determining user's home page after login.
    Returns the URL path for the user's landing page.
    """
    if user == "Guest":
        return None
    
    roles = frappe.get_roles(user)
    
    # If user has Employee role but NOT System Manager, go to portal
    if "Employee" in roles and "System Manager" not in roles:
        return "/employee-portal"
    
    # Return None to let Frappe use default behavior for other users
    return None


# Keep old function for backward compatibility (can be removed)
def on_login(login_manager):
    """Legacy hook - kept for backward compatibility"""
    pass

def redirect_employee_after_login(login_manager=None, *args, **kwargs):
    """
    Hook: on_session_creation
    Sets home_page for employees to redirect to portal.
    """
    user = frappe.session.user
    roles = frappe.get_roles(user)
    
    if "Employee" in roles and "System Manager" not in roles:
        # Set flags.home_page - takes HIGHEST priority in get_home_page()
        frappe.local.flags.home_page = "employee-portal"
        # Also set in response directly
        frappe.local.response["home_page"] = "/employee-portal"
        frappe.local.response["redirect_to"] = "/employee-portal"


def redirect_employee_on_boot(bootinfo):
    """
    Hook: boot_session
    Called when desk/app loads bootinfo.
    Redirects employees to portal if they try to access desk.
    """
    user = frappe.session.user
    if user == "Guest":
        return
    
    roles = frappe.get_roles(user)
    
    if "Employee" in roles and "System Manager" not in roles:
        # Override bootinfo.home_page so desk redirects to portal
        bootinfo.home_page = "employee-portal"