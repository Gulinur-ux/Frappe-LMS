# Copyright (c) 2026, LMS Reports and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime, flt, cint
from lms.lms.doctype.course_lesson.course_lesson import save_progress


@frappe.whitelist()
def track_lesson_watch(lesson, course, video_speed="1x", watched_duration=0, 
                       video_total_duration=0, start_time=0, end_time=0):
    """
    Track student's lesson watching activity including video speed and duration.
    Creates or updates LMS Student Lesson Log with watch history.
    """
    student = frappe.session.user
    
    if student == "Guest":
        frappe.throw(_("Please login to track progress"))
    
    # Check if log exists
    existing_log = frappe.db.exists(
        "LMS Student Lesson Log",
        {"student": student, "lesson": lesson}
    )
    
    chapter = frappe.db.get_value("Course Lesson", lesson, "chapter")
    
    if existing_log:
        doc = frappe.get_doc("LMS Student Lesson Log", existing_log)
    else:
        doc = frappe.new_doc("LMS Student Lesson Log")
        doc.student = student
        doc.course = course
        doc.chapter = chapter
        doc.lesson = lesson

    doc.video_speed = video_speed
    doc.watched_duration = flt(doc.watched_duration) + flt(watched_duration)
    doc.video_total_duration = flt(video_total_duration)
    doc.last_watched_timestamp = now_datetime()
    
    # Calculate video completion percentage
    if flt(video_total_duration) > 0:
        completion = min(100, (doc.watched_duration / video_total_duration) * 100)
        doc.completion_percentage = completion

    # Add watch history entry
    doc.append("watch_history", {
        "watched_at": now_datetime(),
        "video_speed": video_speed,
        "start_time": flt(start_time),
        "end_time": flt(end_time),
        "duration_watched": flt(watched_duration)
    })
    
    doc.save(ignore_permissions=True)

    # Sync with standard LMS
    if flt(doc.completion_percentage) >= 100:
        try:
            save_progress(lesson, course)
            check_and_update_log_completion(doc, student, lesson)
        except Exception:
            frappe.log_error("Failed to update standard LMS progress")
    
    return {
        "success": True,
        "completion_percentage": doc.completion_percentage,
        "is_completed": doc.is_completed
    }


@frappe.whitelist()
def update_quiz_result(lesson, course, quiz, score, total_score, percentage):
    """
    Update quiz results in student lesson log.
    Consolidated logic to use DocType events via mock submission if needed, 
    but here we handle it directly for efficiency while keeping it in sync.
    """
    student = frappe.session.user
    
    if student == "Guest":
        frappe.throw(_("Please login to track progress"))
    
    # Actually, it's better to create an LMS Quiz Submission and let its hook handle it.
    # But if the frontend calls this directly, we ensure it's recorded.
    
    existing_log = frappe.db.exists(
        "LMS Student Lesson Log",
        {"student": student, "lesson": lesson}
    )
    
    chapter = frappe.db.get_value("Course Lesson", lesson, "chapter")
    
    if existing_log:
        doc = frappe.get_doc("LMS Student Lesson Log", existing_log)
    else:
        doc = frappe.new_doc("LMS Student Lesson Log")
        doc.student = student
        doc.course = course
        doc.chapter = chapter
        doc.lesson = lesson
    
    doc.quiz_attempts = cint(doc.quiz_attempts) + 1
    if flt(percentage) > flt(doc.quiz_best_score):
        doc.quiz_best_score = flt(percentage)
    
    if flt(percentage) >= 100 and not doc.quiz_passed_at_attempt:
        doc.quiz_passed_at_attempt = doc.quiz_attempts
    
    doc.last_watched_timestamp = now_datetime()
    doc.save(ignore_permissions=True)

    # Sync with standard LMS
    if flt(percentage) >= 100:
        try:
            save_progress(lesson, course)
            check_and_update_log_completion(doc, student, lesson)
        except Exception:
            frappe.log_error("Failed to update standard LMS progress")
    
    return {
        "success": True,
        "quiz_attempts": doc.quiz_attempts,
        "quiz_best_score": doc.quiz_best_score,
        "quiz_passed_at_attempt": doc.quiz_passed_at_attempt
    }


def check_and_update_log_completion(log_doc, student, lesson):
    """
    Helper to check if lesson is complete in standard LMS 
    and update our custom log accordingly.
    """
    # Check if lesson is marked as complete in standard LMS
    # Standard LMS uses 'LMS Course Progress'
    lms_complete = frappe.db.exists("LMS Course Progress", {
        "lesson": lesson,
        "member": student,
        "status": "Complete"
    })
    
    if lms_complete and not log_doc.is_completed:
        log_doc.is_completed = 1
        log_doc.completion_percentage = 100
        log_doc.save(ignore_permissions=True)


@frappe.whitelist()
def get_student_progress(course=None, lesson=None, student=None):
    """
    Get student progress data for reporting.
    Can filter by course, lesson, or student.
    
    Args:
        course: Optional LMS Course filter
        lesson: Optional Course Lesson filter
        student: Optional Student (User) filter
    """
    filters = {}
    
    if course:
        filters["course"] = course
    if lesson:
        filters["lesson"] = lesson
    if student:
        filters["student"] = student
    
    logs = frappe.get_all(
        "LMS Student Lesson Log",
        filters=filters,
        fields=[
            "name", "student", "student_name", "course", "chapter", "lesson",
            "completion_percentage", "is_completed", "video_speed",
            "watched_duration", "video_total_duration", "last_watched_timestamp",
            "quiz_attempts", "quiz_best_score", "quiz_passed_at_attempt"
        ],
        order_by="last_watched_timestamp desc"
    )
    
    # Enrich with course and lesson titles
    for log in logs:
        log.course_title = frappe.db.get_value("LMS Course", log.course, "title")
        log.lesson_title = frappe.db.get_value("Course Lesson", log.lesson, "title")
    
    return logs


@frappe.whitelist()
def get_course_progress_summary(course, student=None, lesson=None):
    """
    Get summary of all students' progress in a course.
    Useful for admin dashboard.
    
    Args:
        course: LMS Course name
        student: Optional Student (User) filter
        lesson: Optional Course Lesson filter
    """
    # Filter enrollments
    filters = {"course": course}
    if student:
        filters["member"] = student
        
    enrollments = frappe.get_all(
        "LMS Enrollment",
        filters=filters,
        fields=["member", "member_name", "progress", "modified"]
    )
    
    # Get lesson count
    lesson_count = frappe.db.count("Course Lesson", {"course": course})
    
    summary = {
        "total_students": len(enrollments),
        "lesson_count": lesson_count,
        "students": []
    }
    
    for enrollment in enrollments:
        student_data = {
            "student": enrollment.member,
            "student_name": enrollment.member_name,
            "overall_progress": enrollment.progress,
            "completion_date": enrollment.modified if enrollment.progress >= 100 else None,
            "completed_lessons": 0,
            "lesson_details": []
        }

        # If lesson filter is active, get specific lesson log
        if lesson:
            log = frappe.db.get_value(
                "LMS Student Lesson Log",
                {"course": course, "student": enrollment.member, "lesson": lesson},
                ["completion_percentage", "is_completed", "video_speed", "last_watched_timestamp"],
                as_dict=True
            )
            
            completion_date = None
            if log and log.is_completed:
                completion_date = frappe.db.get_value("LMS Course Progress", 
                    {"lesson": lesson, "member": enrollment.member, "status": "Complete"}, "creation")

            student_data["specific_lesson"] = {
                "name": lesson,
                "completion_percentage": log.completion_percentage if log else 0,
                "is_completed": log.is_completed if log else 0,
                "last_watched": log.last_watched_timestamp if log else None,
                "completion_date": completion_date
            }
            
            logs = frappe.get_all("LMS Student Lesson Log", filters={"course": course, "student": enrollment.member, "is_completed": 1})
            student_data["completed_lessons"] = len(logs)
            
        else:
            # Get all lesson logs for this student, ordered by most recent activity
            logs = frappe.get_all(
                "LMS Student Lesson Log",
                filters={"course": course, "student": enrollment.member},
                fields=["lesson", "completion_percentage", "is_completed", "video_speed", 
                       "last_watched_timestamp", "quiz_attempts", "quiz_best_score", "modified"],
                order_by="last_watched_timestamp desc"
            )
            
            # Sync with standard LMS if our logs are missing completion
            # This handles cases where lesson was completed but our log didn't catch it
            lms_completed_lessons = frappe.get_all("LMS Course Progress", 
                filters={"course": course, "member": enrollment.member, "status": "Complete"},
                fields=["lesson", "creation"]
            )
            
            for lms_l in lms_completed_lessons:
                # Check if we have a log for this
                matched_log = next((l for l in logs if l.lesson == lms_l.lesson), None)
                if not matched_log or not matched_log.is_completed:
                    # Update or create log
                    if matched_log:
                        log_doc = frappe.get_doc("LMS Student Lesson Log", 
                            {"student": enrollment.member, "lesson": lms_l.lesson})
                    else:
                        log_doc = frappe.new_doc("LMS Student Lesson Log")
                        log_doc.student = enrollment.member
                        log_doc.course = course
                        log_doc.lesson = lms_l.lesson
                        log_doc.chapter = frappe.db.get_value("Course Lesson", lms_l.lesson, "chapter")
                    
                    log_doc.is_completed = 1
                    log_doc.completion_percentage = 100
                    if not log_doc.last_watched_timestamp:
                        log_doc.last_watched_timestamp = lms_l.creation
                    log_doc.save(ignore_permissions=True)
                    
                    # Refresh logs list for this student
                    logs = frappe.get_all(
                        "LMS Student Lesson Log",
                        filters={"course": course, "student": enrollment.member},
                        fields=["lesson", "completion_percentage", "is_completed", "video_speed", 
                               "last_watched_timestamp", "quiz_attempts", "quiz_best_score", "modified"],
                        order_by="last_watched_timestamp desc"
                    )
            
            for log in logs:
                if log.is_completed:
                    cdate = frappe.db.get_value("LMS Course Progress", 
                        {"lesson": log.lesson, "member": enrollment.member, "status": "Complete"}, "creation")
                    # Fallback to last activity or modified if creation is missing
                    log["completion_date"] = cdate or log.last_watched_timestamp or log.modified
                else:
                    log["completion_date"] = None

            student_data["completed_lessons"] = len([l for l in logs if l.is_completed])
            student_data["lesson_details"] = logs
        
        # Fallback for legacy data: if 100% completed but 0 lessons tracked, assume all lessons completed
        if student_data["overall_progress"] >= 100 and student_data["completed_lessons"] == 0:
            student_data["completed_lessons"] = lesson_count
            
        summary["students"].append(student_data)
    
    return summary


@frappe.whitelist()
def check_lesson_access(course, lesson):
    """
    Check if student can access a lesson.
    Returns True if previous lesson is completed or this is the first lesson.
    
    Args:
        course: LMS Course name
        lesson: Course Lesson name to check access for
    """
    student = frappe.session.user
    
    if student == "Guest":
        return {"can_access": False, "reason": "Please login"}
    
    # Get all lessons in order
    lessons = frappe.get_all(
        "Course Lesson",
        filters={"course": course},
        fields=["name", "chapter"],
        order_by="creation"
    )
    
    if not lessons:
        return {"can_access": True}
    
    # Find current lesson index
    lesson_index = -1
    for i, l in enumerate(lessons):
        if l.name == lesson:
            lesson_index = i
            break
    
    if lesson_index == -1:
        return {"can_access": False, "reason": "Lesson not found"}
    
    # First lesson is always accessible
    if lesson_index == 0:
        return {"can_access": True}
    
    # Check if previous lesson is completed
    previous_lesson = lessons[lesson_index - 1].name
    
    is_completed = frappe.db.get_value(
        "LMS Student Lesson Log",
        {"student": student, "lesson": previous_lesson},
        "is_completed"
    )
    
    if is_completed:
        return {"can_access": True}
    else:
        return {
            "can_access": False, 
            "reason": f"Please complete the previous lesson first",
            "previous_lesson": previous_lesson
        }
