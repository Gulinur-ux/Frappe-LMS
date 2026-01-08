# Copyright (c) 2026, LMS Reports and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "student",
			"label": _("Student"),
			"fieldtype": "Link",
			"options": "User",
			"width": 150
		},
		{
			"fieldname": "student_name",
			"label": _("Student Name"),
			"fieldtype": "Data",
			"width": 180
		},
		{
			"fieldname": "course",
			"label": _("Course"),
			"fieldtype": "Link",
			"options": "LMS Course",
			"width": 150
		},
		{
			"fieldname": "chapter",
			"label": _("Chapter"),
			"fieldtype": "Link",
			"options": "Course Chapter",
			"width": 150
		},
		{
			"fieldname": "lesson",
			"label": _("Lesson"),
			"fieldtype": "Link",
			"options": "Course Lesson",
			"width": 180
		},
		{
			"fieldname": "completion_percentage",
			"label": _("Completion %"),
			"fieldtype": "Percent",
			"width": 110
		},
		{
			"fieldname": "is_completed",
			"label": _("Completed"),
			"fieldtype": "Check",
			"width": 80
		},
		{
			"fieldname": "video_speed",
			"label": _("Speed"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "watched_duration",
			"label": _("Watched (sec)"),
			"fieldtype": "Float",
			"width": 110
		},
		{
			"fieldname": "last_watched_timestamp",
			"label": _("Last Watched"),
			"fieldtype": "Datetime",
			"width": 150
		},
		{
			"fieldname": "quiz_attempts",
			"label": _("Attempts"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "quiz_best_score",
			"label": _("Best Score"),
			"fieldtype": "Percent",
			"width": 100
		},
		{
			"fieldname": "quiz_passed_at_attempt",
			"label": _("Passed At"),
			"fieldtype": "Int",
			"width": 100
		}
	]


def get_data(filters):
	conditions = {}
	if filters.get("student"):
		conditions["student"] = filters.get("student")
	if filters.get("course"):
		conditions["course"] = filters.get("course")
	if filters.get("lesson"):
		conditions["lesson"] = filters.get("lesson")
	if filters.get("is_completed"):
		conditions["is_completed"] = 1

	return frappe.get_all(
		"LMS Student Lesson Log",
		filters=conditions,
		fields=[
			"student", "student_name", "course", "chapter", "lesson",
			"completion_percentage", "is_completed", "video_speed",
			"watched_duration", "last_watched_timestamp",
			"quiz_attempts", "quiz_best_score", "quiz_passed_at_attempt"
		],
		order_by="last_watched_timestamp desc"
	)
