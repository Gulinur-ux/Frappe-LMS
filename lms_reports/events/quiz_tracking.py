"""
Quiz submission tracking events.
Automatically tracks quiz attempts and scores.
"""

import frappe
from frappe.utils import flt, cint, now_datetime


def on_quiz_submit(doc, method=None):
    """
    Track quiz submission and update LMS Student Lesson Log.

    Triggered by:
    - LMS Quiz Submission (after_insert)

    Args:
        doc: The LMS Quiz Submission document
        method: The hook method name
    """
    try:
        student = doc.member
        quiz = doc.quiz
        score = flt(doc.score)
        percentage = flt(doc.percentage) if hasattr(doc, 'percentage') else 0

        if not quiz or not student:
            return

        # Get lesson from quiz
        lesson = frappe.db.get_value("LMS Quiz", quiz, "lesson")
        if not lesson:
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

        # Update quiz tracking
        log.quiz_attempts = cint(log.quiz_attempts) + 1

        # Update best score if this is better
        if percentage > flt(log.quiz_best_score):
            log.quiz_best_score = percentage

        # Track first time reaching 100%
        if percentage >= 100 and not log.quiz_passed_at_attempt:
            log.quiz_passed_at_attempt = log.quiz_attempts

        log.last_watched_timestamp = now_datetime()

        # Check if lesson is completed
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
            f"Error tracking quiz submission: {str(e)}\nDoc: {doc.as_dict()}",
            "Quiz Tracking Error"
        )
