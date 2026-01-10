"""
Video and course progress tracking events.
Automatically tracks student activity when they watch videos or complete lessons.
"""

import frappe
from frappe.utils import flt, now_datetime


def on_video_watch(doc, method=None):
    """
    Track video watch activity and update LMS Student Lesson Log.

    Triggered by:
    - LMS Video Watch Duration (after_insert, on_update)
    - LMS Course Progress (after_insert)

    Args:
        doc: The source document (LMS Video Watch Duration or LMS Course Progress)
        method: The hook method name
    """
    try:
        # Determine student and lesson based on doctype
        if doc.doctype == "LMS Video Watch Duration":
            student = doc.owner
            lesson = doc.lesson
            watched_duration = flt(doc.duration) if hasattr(doc, 'duration') else 0
            video_speed = getattr(doc, 'playback_speed', '1x')

        elif doc.doctype == "LMS Course Progress":
            student = doc.member
            lesson = doc.lesson
            watched_duration = 0
            video_speed = None

        else:
            return

        if not lesson or not student:
            return

        # Get course and chapter
        lesson_doc = frappe.get_doc("Course Lesson", lesson)
        course = lesson_doc.course
        chapter = lesson_doc.chapter

        # Get or create student lesson log
        existing_log = frappe.db.exists(
            "LMS Student Lesson Log",
            {"student": student, "lesson": lesson}
        )

        if existing_log:
            log = frappe.get_doc("LMS Student Lesson Log", existing_log)
        else:
            log = frappe.new_doc("LMS Student Lesson Log")
            log.student = student
            log.course = course
            log.chapter = chapter
            log.lesson = lesson

        # Update tracking fields
        if video_speed:
            log.video_speed = video_speed

        if watched_duration > 0:
            log.watched_duration = max(flt(log.watched_duration), watched_duration)

        log.last_watched_timestamp = now_datetime()

        # Check if lesson is completed in standard LMS
        is_completed = frappe.db.exists("LMS Course Progress", {
            "lesson": lesson,
            "member": student,
            "status": "Complete"
        })

        if is_completed:
            log.is_completed = 1
            log.completion_percentage = 100

        log.save(ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        frappe.log_error(
            f"Error tracking video watch: {str(e)}\nDoc: {doc.as_dict()}",
            "Video Tracking Error"
        )
