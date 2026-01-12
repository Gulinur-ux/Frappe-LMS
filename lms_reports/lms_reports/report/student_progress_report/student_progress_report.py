# Copyright (c) 2026, LMS Reports and contributors
import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    raw_data = get_data(filters)
    
    grouped_data = {}
    for row in raw_data:
        # dict access fix
        student = row.get("student")
        if not student:
            continue
            
        if student not in grouped_data:
            grouped_data[student] = {
                "student": student,
                "student_name": row.get("student_name") or student,
                "student_email": frappe.db.get_value("User", student, "email") or student,
                "total_lessons": 0,
                "completed_count": 0,
                "progress": 0,
                "last_activity": None,
                "lessons": []
            }
        
        grouped_data[student]["lessons"].append(row)
        grouped_data[student]["total_lessons"] += 1
        
        if row.get("is_completed"):
            grouped_data[student]["completed_count"] += 1
            
        # Mantiqiy tuzatish: Faqat completion emas, har qanday faollikni kuzatamiz
        ts = row.get("last_watched_timestamp")
        if ts:
            if not grouped_data[student]["last_activity"] or ts > grouped_data[student]["last_activity"]:
                grouped_data[student]["last_activity"] = ts

    final_data = []
    for st_id, info in grouped_data.items():
        if info["total_lessons"] > 0:
            info["progress"] = round((info["completed_count"] / info["total_lessons"]) * 100, 1)
        
        # Datetime formatlash
        if info["last_activity"]:
            info["last_activity_display"] = frappe.utils.format_datetime(info["last_activity"], "dd-MM-yyyy HH:mm:ss")
        else:
            info["last_activity_display"] = _("Never")
            
        final_data.append(info)

    return columns, final_data

def get_data(filters):
    conditions = {}
    if filters.get("student"):
        conditions["student"] = filters.get("student")
    if filters.get("course"):
        conditions["course"] = filters.get("course")
    if filters.get("lesson"):
        conditions["lesson"] = filters.get("lesson")
    
    # Filtr tuzatish
    if filters.get("is_completed") == 1:
        conditions["is_completed"] = 1

    return frappe.get_all(
        "LMS Student Lesson Log",
        filters=conditions,
        fields=[
            "student", "student_name", "course", "chapter", "lesson",
            "completion_percentage", "is_completed", "video_speed",
            "watched_duration", "last_watched_timestamp",
            "quiz_attempts", "quiz_best_score"
        ],
        order_by="last_watched_timestamp desc"
    )

def get_columns():
    return [
        {"fieldname": "student", "label": _("Student"), "fieldtype": "Link", "options": "User", "width": 150},
        {"fieldname": "student_name", "label": _("Student Name"), "fieldtype": "Data", "width": 150},
        {"fieldname": "progress", "label": _("Total Progress %"), "fieldtype": "Percent", "width": 120}
    ]