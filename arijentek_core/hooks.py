app_name = "arijentek_core"
app_title = "Arijentek Solution"
app_publisher = "Arijentek Solution"
app_description = "Unified app for management."
app_email = "akshay@arijentek.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "arijentek_core",
# 		"logo": "/assets/arijentek_core/logo.png",
# 		"title": "Arijentek Solution",
# 		"route": "/arijentek_core",
# 		"has_permission": "arijentek_core.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/arijentek_core/css/arijentek_core.css"
# app_include_js = "/assets/arijentek_core/js/arijentek_core.js"

# include js, css files in header of web template
# web_include_css = "/assets/arijentek_core/css/arijentek_core.css"
web_include_js = "/assets/arijentek_core/js/login_redirect.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "arijentek_core/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "arijentek_core/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "arijentek_core.utils.jinja_methods",
# 	"filters": "arijentek_core.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "arijentek_core.install.before_install"
# after_install = "arijentek_core.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "arijentek_core.uninstall.before_uninstall"
# after_uninstall = "arijentek_core.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "arijentek_core.utils.before_app_install"
# after_app_install = "arijentek_core.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "arijentek_core.utils.before_app_uninstall"
# after_app_uninstall = "arijentek_core.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "arijentek_core.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"arijentek_core.tasks.all"
# 	],
# 	"daily": [
# 		"arijentek_core.tasks.daily"
# 	],
# 	"hourly": [
# 		"arijentek_core.tasks.hourly"
# 	],
# 	"weekly": [
# 		"arijentek_core.tasks.weekly"
# 	],
# 	"monthly": [
# 		"arijentek_core.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "arijentek_core.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "arijentek_core.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "arijentek_core.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "arijentek_core.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["arijentek_core.utils.before_request"]
# after_request = ["arijentek_core.utils.after_request"]

# Job Events
# ----------
# before_job = ["arijentek_core.utils.before_job"]
# after_job = ["arijentek_core.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"arijentek_core.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

# ===========================================
# ARIJENTEK CONFIGURATION
# ===========================================

# --- Login override ---
# Supports Employee ID login + returns CSRF token for SPA.
override_whitelisted_methods = {
	"frappe.auth.login": "arijentek_core.auth.custom_login.login",
}

# --- Request security ---
before_request = ["arijentek_core.security.validate_request"]

# --- Audit logging ---
doc_events = {
	"Employee Checkin": {"on_submit": "arijentek_core.security.log_attendance_event"},
	"Attendance": {"on_submit": "arijentek_core.security.log_attendance_event"},
}

# --- Session ---
on_session_creation = "arijentek_core.security.on_session_created"

# --- Scheduled Tasks ---
scheduler_events = {
	"monthly": [
		"arijentek_core.payroll.automation.run_monthly_payroll_automation",
	],
}

# --- Employee Portal routing ---
# Serve the SPA from www/employee-portal.html at /employee-portal
# The <path:app_path> wildcard ensures all sub-paths render the SPA (HTML5 history mode ready).
website_route_rules = [
	{"from_route": "/employee-portal", "to_route": "employee-portal"},
	{"from_route": "/employee-portal/<path:app_path>", "to_route": "employee-portal"},
]

# --- Website-user redirect ---
# Website users (Employee role, no System Manager) → portal after login.
role_home_page = {
	"Employee": "/employee-portal",
}

get_website_user_home_page = "arijentek_core.utils.get_employee_home_page"

# Redirect employees away from desk if they somehow get there.
boot_session = "arijentek_core.utils.redirect_employee_on_boot"
