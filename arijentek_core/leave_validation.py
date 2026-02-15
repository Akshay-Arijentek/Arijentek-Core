import frappe
from frappe.utils import getdate, today

def validate_leave_date(doc, method):
    """
    Validate that leave is not applied for a past month.
    Rule: Employees can only apply for the current month or future months.
    """
    # Allow HR Managers to bypass this restriction for data correction
    if "HR Manager" in frappe.get_roles() or "System Manager" in frappe.get_roles():
        return

    # Skip validation if status is Rejected or Cancelled
    if doc.status == "Rejected" or doc.docstatus == 2:
        return

    current_date = getdate(today())
    # First day of the current month
    first_day_current_month = getdate(f"{current_date.year}-{current_date.month:02d}-01")
    
    leave_from_date = getdate(doc.from_date)
    
    if leave_from_date < first_day_current_month:
        frappe.throw(
            "You cannot apply for leave for a past month.<br>"
            "Please select a date in the current month or the future."
        )
