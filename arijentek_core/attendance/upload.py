"""
Custom Upload Attendance for v16 workaround.

The standard HRMS Upload Attendance tool uses FileUploader + upload_file handler.
In some v16 setups this can fail silently. This module provides:

1. upload_attendance_csv(content) - API that accepts file content directly
2. Bench command: bench --site <site> upload-attendance <file.csv>
"""

import frappe
from frappe import _
from frappe.utils import cstr


def _import_attendance_rows(rows):
	"""Process CSV rows and create/update Attendance records. Same logic as HRMS upload_attendance."""
	from frappe.modules import scrub
	from frappe.utils.csvutils import check_record, import_doc

	rows = list(filter(lambda x: x and any(x), rows))
	if len(rows) < 6:
		frappe.throw(_("CSV must have header row (row 5) and at least one data row"))

	columns = [scrub(f) for f in rows[4]]
	columns[0] = "name"
	columns[3] = "attendance_date"
	data_rows = rows[5:]

	# Remove holiday rows and rows with empty Status (weekends, unmarked days, etc.)
	def has_valid_status(row):
		if not row or len(row) <= 4:
			return False
		status = (row[4] or "").strip()
		return status and status != "Holiday"

	data_rows = [row for row in data_rows if has_valid_status(row)]

	ret = []
	error = False

	for i, row in enumerate(data_rows):
		if not row:
			continue
		row_idx = i + 6
		d = frappe._dict(zip(columns, row, strict=False))

		d["doctype"] = "Attendance"
		if d.get("name"):
			d["docstatus"] = frappe.db.get_value("Attendance", d.name, "docstatus") or 0

		try:
			check_record(d)
			ret.append(import_doc(d, "Attendance", 1, row_idx, submit=True))
		except AttributeError:
			pass
		except Exception as e:
			error = True
			ret.append("Error for row (#%d) %s : %s" % (row_idx, len(row) > 1 and row[1] or "", cstr(e)))
			frappe.errprint(frappe.get_traceback())

	if error:
		frappe.db.rollback()
	else:
		frappe.db.commit()

	return {"messages": ret, "error": error}


@frappe.whitelist()
def upload_attendance_csv(file_content=None):
	"""
	Upload attendance from CSV content. v16 workaround when standard Upload Attendance fails.

	Accepts:
	- file_content: base64-encoded CSV string (when called from JS with file content)
	- Or uses frappe.local.uploaded_file when called via upload_file with method=

	Requires Attendance create permission.
	"""
	if not frappe.has_permission("Attendance", "create"):
		raise frappe.PermissionError

	import base64

	from frappe.utils.csvutils import read_csv_content

	content = None
	if file_content:
		if isinstance(file_content, str):
			content = base64.b64decode(file_content)
		else:
			content = file_content
	else:
		content = getattr(frappe.local, "uploaded_file", None)

	if not content:
		frappe.throw(_("Please provide file content or upload a file"))

	rows = read_csv_content(content)
	if not rows:
		frappe.throw(_("No valid CSV content"))

	result = _import_attendance_rows(rows)
	return result
