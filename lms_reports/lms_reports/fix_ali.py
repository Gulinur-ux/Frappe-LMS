import frappe
from lms.lms.doctype.course_lesson.course_lesson import save_progress

def execute():
    # Check if log exists to avoid duplicate
    if frappe.db.exists("LMS Student Lesson Log", {"student": "ali@example.com", "lesson": "0004 Kontragent hisobot"}):
        print("Log already exists")
    else:
        doc = frappe.new_doc("LMS Student Lesson Log")
        doc.student = "ali@example.com"
        doc.course = "moliya-darslari"
        doc.lesson = "0004 Kontragent hisobot"
        doc.completion_percentage = 100
        doc.is_completed = 1
        doc.video_speed = "1x"
        doc.watched_duration = 100
        doc.video_total_duration = 100
        doc.insert(ignore_permissions=True)
        print("Log created")

    # Trigger progress update
    save_progress("0004 Kontragent hisobot", "moliya-darslari")
    frappe.db.commit()
    print("Progress saved")
