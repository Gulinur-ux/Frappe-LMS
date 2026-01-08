import frappe

@frappe.whitelist()
def update_lesson_progress(course, lesson, progress, video_speed, watched_duration):
    student = frappe.session.user
    if student == "Guest":
        return {"status": "ignored", "reason": "Guest User"}

    log_name = frappe.db.get_value("LMS Student Lesson Log", 
        {"student": student, "course": course, "lesson": lesson}, "name")

    data = {
        "student": student,
        "course": course,
        "lesson": lesson,
        "completion_percentage": float(progress),
        "video_speed": video_speed,
        "watched_duration": float(watched_duration),
        "last_watched_timestamp": frappe.utils.now_datetime(),
        "is_completed": 1 if float(progress) >= 95 else 0
    }

    if log_name:
        frappe.db.set_value("LMS Student Lesson Log", log_name, data)
    else:
        doc = frappe.get_doc({"doctype": "LMS Student Lesson Log", **data})
        doc.insert(ignore_permissions=True)
    
    frappe.db.commit()
    return {"status": "success", "progress": progress}
