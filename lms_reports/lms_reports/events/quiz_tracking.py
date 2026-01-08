# Copyright (c) 2026, LMS Reports and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime, flt, cint
from lms.lms.doctype.course_lesson.course_lesson import save_progress
from lms_reports.lms_reports.api import check_and_update_log_completion


def on_quiz_submit(doc, method):
    """
    Hook called when LMS Quiz Submission is created.
    Updates LMS Student Lesson Log with quiz performance data.
    """
    try:
        student = doc.member
        quiz = doc.quiz
        course = doc.course
        percentage = flt(doc.percentage)
        
        if not student or not quiz:
            return
        
        # Get lesson from quiz
        lesson = frappe.db.get_value("LMS Quiz", quiz, "lesson")
        
        if not lesson:
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
        
        # Update quiz attempts
        log_doc.quiz_attempts = cint(log_doc.quiz_attempts) + 1
        
        # Update best score if this attempt is better
        if percentage > flt(log_doc.quiz_best_score):
            log_doc.quiz_best_score = percentage
        
        # Record attempt number when 100% achieved
        if percentage >= 100 and not log_doc.quiz_passed_at_attempt:
            log_doc.quiz_passed_at_attempt = log_doc.quiz_attempts
        
        log_doc.last_watched_timestamp = now_datetime()
        log_doc.save(ignore_permissions=True)

        # Sync with standard LMS progress
        if percentage >= 100:
            try:
                save_progress(lesson, course)
                check_and_update_log_completion(log_doc, student, lesson)
            except Exception as e:
                frappe.log_error(f"Failed to sync LMS progress: {str(e)}", "LMS Reports - Quiz Tracking")
        
    except Exception as e:
        frappe.log_error(f"Quiz tracking error: {str(e)}", "LMS Reports - Quiz Tracking")
