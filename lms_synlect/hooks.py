app_name = "lms_synlect"
app_title = "LMS Synlect"
app_publisher = "shilpa@walue.biz"
app_description = "lms-synlect"
app_email = "shilpa@walue.biz"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "lms_synlect",
# 		"logo": "/assets/lms_synlect/logo.png",
# 		"title": "LMS Synlect",
# 		"route": "/lms_synlect",
# 		"has_permission": "lms_synlect.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/lms_synlect/css/lms_synlect.css"
# app_include_js = "/assets/lms_synlect/js/lms_synlect.js"

# include js, css files in header of web template
# web_include_css = "/assets/lms_synlect/css/lms_synlect.css"
# web_include_js = "/assets/lms_synlect/js/lms_synlect.js"

# Include custom JS for LMS batch page (web pages, not desk)
web_include_js = [
    "/assets/lms_synlect/js/lms_batch_button.js"
]

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "lms_synlect/public/scss/website"

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
# app_include_icons = "lms_synlect/public/icons.svg"

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
# 	"methods": "lms_synlect.utils.jinja_methods",
# 	"filters": "lms_synlect.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "lms_synlect.install.before_install"
# after_install = "lms_synlect.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "lms_synlect.uninstall.before_uninstall"
# after_uninstall = "lms_synlect.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "lms_synlect.utils.before_app_install"
# after_app_install = "lms_synlect.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "lms_synlect.utils.before_app_uninstall"
# after_app_uninstall = "lms_synlect.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "lms_synlect.notifications.get_notification_config"

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
# 		"lms_synlect.tasks.all"
# 	],
# 	"daily": [
# 		"lms_synlect.tasks.daily"
# 	],
# 	"hourly": [
# 		"lms_synlect.tasks.hourly"
# 	],
# 	"weekly": [
# 		"lms_synlect.tasks.weekly"
# 	],
# 	"monthly": [
# 		"lms_synlect.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "lms_synlect.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "lms_synlect.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "lms_synlect.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "lms_synlect.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["lms_synlect.utils.before_request"]
# after_request = ["lms_synlect.utils.after_request"]

# Job Events
# ----------
# before_job = ["lms_synlect.utils.before_job"]
# after_job = ["lms_synlect.utils.after_job"]

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
# 	"lms_synlect.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

