import frappe
import re
from frappe.rate_limiter import rate_limit

def validate_password_policy(password):
	"""
	Enforce strong password policy:
	- Minimum 8 characters
	- At least 1 uppercase letter
	- At least 1 digit
	- At least 1 special character
	"""
	if len(password) < 8:
		return "Password must be at least 8 characters long"
	if not re.search(r"[A-Z]", password):
		return "Password must contain at least one uppercase letter"
	if not re.search(r"\d", password):
		return "Password must contain at least one digit"
	if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
		return "Password must contain at least one special character"
	return None

@frappe.whitelist()
@rate_limit(limit=5, seconds=60)
def change_password(old_password, new_password):
	"""Change current user's password"""
	user = frappe.session.user
	if user == "Guest":
		return {"success": False, "error": "Not logged in"}

	try:
		# Verify old password
		if not frappe.utils.password.check_password(user, old_password):
			return {"success": False, "error": "Incorrect old password"}
		
		# Prevent reuse
		if old_password == new_password:
			return {"success": False, "error": "New password cannot be the same as the old password"}

		# Validate policy
		policy_error = validate_password_policy(new_password)
		if policy_error:
			return {"success": False, "error": policy_error}
		
		from frappe.utils.password import update_password
		update_password(user, new_password)
		
		return {"success": True}
	except Exception as e:
		return {"success": False, "error": str(e)}
