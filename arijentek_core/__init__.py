__version__ = "0.0.1"


def _patch_hrms_app_permission():
    """
    Monkey-patch HRMS's check_app_permission to return False for Website Users.
    
    This fixes a design issue where Website Users with Employee role get redirected
    to /desk/people after login, but can't access it (403 Forbidden).
    
    The patch makes HRMS invisible in the apps screen for Website Users,
    so get_default_path() won't return /desk/people for them.
    """
    try:
        import frappe
        from hrms.hr import utils as hrms_utils
        
        # Store original function for reference
        _original_check_app_permission = hrms_utils.check_app_permission
        
        def patched_check_app_permission():
            """
            Override: Return False for Website Users to prevent desk redirect.
            Website Users should use the employee-portal, not /desk/people.
            """
            # Early return for guest
            if frappe.session.user == "Guest":
                return False
            
            # Check if user is a Website User
            user_type = frappe.get_cached_value("User", frappe.session.user, "user_type")
            if user_type == "Website User":
                # Website Users cannot access desk, so don't show HRMS app
                return False
            
            # For System Users, use original logic
            return _original_check_app_permission()
        
        # Apply the patch
        hrms_utils.check_app_permission = patched_check_app_permission
        
    except ImportError:
        # HRMS not installed, no need to patch
        pass
    except Exception:
        # Silently fail - don't break app loading
        pass

# Apply patch when module loads
_patch_hrms_app_permission()
