import frappe
from frappe.utils import now_datetime, flt
from lms.lms.doctype.course_lesson.course_lesson import save_progress
from lms_reports.lms_reports.api import check_and_update_log_completion


def on_video_watch(doc, method):
    """
    Hook called when LMS Video Watch Duration is created or updated.
    Updates LMS Student Lesson Log with video tracking data.
    """
    try:
        student = doc.member
        lesson = doc.lesson
        course = doc.course
        
        if not student or not lesson:
            return
        
        # Get chapter from lesson
        chapter = frappe.db.get_value("Course Lesson", lesson, "chapter")
        
        # Check if log exists
        existing_log = frappe.db.exists(
            "LMS Student Lesson Log",
            {"student": student, "lesson": lesson}
        )
        
        if existing_log:
            log_doc = frappe.get_doc("LMS Student Lesson Log", existing_log)
        else:
            log_doc = frappe.new_doc("LMS Student Lesson Log")
            log_doc.student = student
            log_doc.course = course
            log_doc.chapter = chapter
            log_doc.lesson = lesson
        
        # Update watched duration
        log_doc.watched_duration = flt(doc.watch_time)
        log_doc.last_watched_timestamp = now_datetime()
        
        # Get video total duration from lesson content if available
        if doc.source:
            # If there's a total duration, calculate completion
            if log_doc.video_total_duration and flt(log_doc.video_total_duration) > 0:
                completion = min(100, (flt(doc.watch_time) / log_doc.video_total_duration) * 100)
                log_doc.completion_percentage = completion
        
        # Add watch history entry
        log_doc.append("watch_history", {
            "watched_at": now_datetime(),
            "video_speed": log_doc.video_speed or "1x",
            "start_time": 0,
            "end_time": flt(doc.watch_time),
            "duration_watched": flt(doc.watch_time)
        })
        
        log_doc.save(ignore_permissions=True)

        # Sync with standard LMS
        if flt(log_doc.completion_percentage) >= 100:
            try:
                save_progress(lesson, course)
                check_and_update_log_completion(log_doc, student, lesson)
            except Exception:
                frappe.log_error("Failed to update standard LMS progress")
        
    except Exception as e:
        frappe.log_error(f"Video tracking error: {str(e)}", "LMS Reports - Video Tracking")
