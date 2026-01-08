// Copyright (c) 2026, LMS Reports and contributors
// For license information, please see license.txt

frappe.query_reports["Student Progress Report"] = {
    "filters": [
        {
            "fieldname": "student",
            "label": __("Student"),
            "fieldtype": "Link",
            "options": "User",
            "default": frappe.session.user if frappe.session.user != "Administrator" else ""
        },
        {
            "fieldname": "course",
            "label": __("Course"),
            "fieldtype": "Link",
            "options": "LMS Course"
        },
        {
            "fieldname": "lesson",
            "label": __("Lesson"),
            "fieldtype": "Link",
            "options": "Course Lesson",
            "get_query": function () {
                var course = frappe.query_report.get_filter_value("course");
                if (course) {
                    return {
                        filters: {
                            "course": course
                        }
                    };
                }
            }
        },
        {
            "fieldname": "is_completed",
            "label": __("Completed Only"),
            "fieldtype": "Check"
        }
    ]
};
