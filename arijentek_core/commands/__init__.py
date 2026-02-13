# Copyright (c) 2025, Arijentek Solution
# License: MIT

import click

from frappe.commands import get_site, pass_context
from frappe.utils.bench_helper import CliCtxObj


@click.command("upload-attendance")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@pass_context
def upload_attendance(context: CliCtxObj, file_path: str):
	"""
	Upload attendance from CSV file. v16 workaround when standard Upload Attendance fails.

	Use the template from HRMS > Upload Attendance > Get Template, then run:

	  bench --site your-site upload-attendance /path/to/Attendance.csv
	"""
	from arijentek_core.attendance.upload import _import_attendance_rows
	from frappe.utils.csvutils import read_csv_content

	site = get_site(context)

	with open(file_path, "rb") as f:
		content = f.read()

	rows = read_csv_content(content)
	if not rows:
		click.echo("No valid CSV content", err=True)
		raise SystemExit(1)

	import frappe
	frappe.init(site)
	frappe.connect()

	try:
		result = _import_attendance_rows(rows)
		if result["error"]:
			click.echo("Import completed with errors:", err=True)
			for msg in result["messages"]:
				if "Error" in str(msg):
					click.echo(f"  {msg}", err=True)
			raise SystemExit(1)
		else:
			click.echo(f"Import successful. Processed {len(result['messages'])} attendance records.")
	finally:
		frappe.destroy()


commands = [upload_attendance]
