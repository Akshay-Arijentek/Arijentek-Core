import frappe
from arijentek_core.api import get_current_employee
from frappe.utils import flt, nowdate

@frappe.whitelist()
def get_expense_types():
    """Get all Expense Claim Types"""
    return frappe.get_all("Expense Claim Type", pluck="name")

@frappe.whitelist()
def get_my_expenses():
    """Get current employee's expense claims"""
    employee = get_current_employee()
    if not employee:
        return []
    
    expenses = frappe.get_all(
        "Expense Claim",
        filters={"employee": employee},
        fields=["name", "posting_date", "total_claimed_amount", "approval_status", "status"],
        order_by="posting_date desc"
    )
    return expenses

@frappe.whitelist()
def submit_expense_claim(expense_type, amount, description, proof=None):
    """Submit a new Expense Claim"""
    employee = get_current_employee()
    if not employee:
        return {"success": False, "error": "Employee not found"}

    try:
        doc = frappe.new_doc("Expense Claim")
        doc.employee = employee
        doc.posting_date = nowdate()
        doc.expenses = []
        
        # Add expense item
        doc.append("expenses", {
            "expense_type": expense_type,
            "amount": flt(amount),
            "description": description,
            "claim_date": nowdate()
        })

        if proof:
            # Handle base64 or uploaded file logic via frappe.get_doc logic if needed
            # But usually frontend uploads file and sends file_url, OR we use dedicated upload API.
            # For simplicity, if proof is a file_url (uploaded via /api/method/upload_file), attach it.
            pass

        doc.insert(ignore_permissions=True)
        doc.submit()
        
        # Attach proof if provided (as file_url)
        if proof:
             # If proof is a file URL, we link it.
             # Ideally frontend uploads first, gets file URL, then passes it.
             # We can add an attachment.
             file_doc = frappe.get_doc("File", {"file_url": proof})
             file_doc.attached_to_doctype = "Expense Claim"
             file_doc.attached_to_name = doc.name
             file_doc.save(ignore_permissions=True)

        return {"success": True, "name": doc.name}

    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_team_expenses():
    """Get pending expenses for team"""
    employee = get_current_employee()
    if not employee:
        return []
        
    # Get direct reports
    reports = frappe.get_all("Employee", filters={"reports_to": employee, "status": "Active"}, pluck="name")
    if not reports:
        return []

    expenses = frappe.get_all(
        "Expense Claim",
        filters={
            "employee": ["in", reports],
            "docstatus": 1,  # Submitted claims awaiting approval
        },
        fields=["name", "employee_name", "total_claimed_amount", "posting_date", "status", "approval_status"],
        order_by="posting_date asc"
    )
    
    # Only return those that haven't been processed yet
    return [e for e in expenses if e.approval_status not in ["Approved", "Rejected"]]

@frappe.whitelist()
def process_expense(name, action):
    """Approve or Reject expense"""
    if action not in ["Approve", "Reject"]:
        return {"success": False, "error": "Invalid action"}
        
    employee = get_current_employee()
    if not employee:
        return {"success": False, "error": "Unauthorized"}

    try:
        doc = frappe.get_doc("Expense Claim", name)
        
        # Verify manager
        applicant = frappe.db.get_value("Employee", doc.employee, "reports_to")
        if applicant != employee and "System Manager" not in frappe.get_roles():
             return {"success": False, "error": "Unauthorized"}
             
        if action == "Approve":
            doc.approval_status = "Approved"
            doc.status = "Approved" # Sync status
            # doc.submit() # Already submitted?
            doc.save(ignore_permissions=True)
        else:
            doc.approval_status = "Rejected"
            doc.status = "Rejected"
            doc.save(ignore_permissions=True)
            
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
