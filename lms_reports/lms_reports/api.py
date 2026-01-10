# Copyright (c) 2026, LMS Reports and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime, flt, cint
from lms.lms.doctype.course_lesson.course_lesson import save_progress


@frappe.whitelist(allow_guest=True)
def get_lesson_from_number(course, lesson_number):
    """
    Get lesson name from lesson number (e.g., '1-1' or '1.1').
    Returns the Course Lesson name.
    """
    if not lesson_number:
        return {"lesson": None}
    
    # Parse lesson number (supports both 1-1 and 1.1 formats)
    parts = lesson_number.replace('.', '-').split('-')
    if len(parts) != 2:
        return {"lesson": None}
    
    try:
        chapter_idx = int(parts[0])
        lesson_idx = int(parts[1])
    except ValueError:
        return {"lesson": None}
    
    # Get chapter by index
    chapter_ref = frappe.db.get_value(
        "Chapter Reference",
        {"parent": course, "idx": chapter_idx},
        "chapter"
    )
    
    if not chapter_ref:
        return {"lesson": None}
    
    # Get lesson by index within chapter
    lesson_ref = frappe.db.get_value(
        "Lesson Reference",
        {"parent": chapter_ref, "idx": lesson_idx},
        "lesson"
    )
    
    return {"lesson": lesson_ref}


@frappe.whitelist()
def track_lesson_watch(course, video_speed="1x", watched_duration=0, 
                       video_total_duration=0, start_time=0, end_time=0,
                       lesson=None, lesson_number=None):
    """
    Track student's lesson watching activity including video speed and duration.
    Creates or updates LMS Student Lesson Log with watch history.
    
    Args:
        course: LMS Course name
        lesson: Course Lesson name (optional if lesson_number is provided)
        lesson_number: Lesson number like '1-1' (optional if lesson is provided)
        video_speed: Playback speed (e.g., '1x', '1.5x', '2x')
        watched_duration: Time watched in seconds
        video_total_duration: Total video duration in seconds
        start_time: Video start position
        end_time: Video end position
    """
    student = frappe.session.user
    
    if student == "Guest":
        frappe.throw(_("Please login to track progress"))
    
    # Resolve lesson from lesson_number if not provided
    if not lesson and lesson_number:
        result = get_lesson_from_number(course, lesson_number)
        lesson = result.get("lesson")
    
    if not lesson:
        frappe.throw(_("Lesson not found"))
    
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
    # Use max of current watched and new position (don't keep adding)
    doc.watched_duration = max(flt(doc.watched_duration), flt(watched_duration))
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
    
    # Get ALL lessons for this course in correct order
    all_lessons = get_course_lessons_ordered(course)
    lesson_count = len(all_lessons)
    
    # Create lesson lookup map
    lesson_titles = {l["lesson"]: l["title"] for l in all_lessons}
    
    summary = {
        "total_students": len(enrollments),
        "lesson_count": lesson_count,
        "students": []
    }
    
    for enrollment in enrollments:
        # Get completion status from standard LMS Course Progress
        lms_completed = frappe.get_all(
            "LMS Course Progress",
            filters={"course": course, "member": enrollment.member, "status": "Complete"},
            fields=["lesson", "creation"]
        )
        lms_completed_map = {c.lesson: c.creation for c in lms_completed}
        
        # Get our custom tracking logs
        custom_logs = frappe.get_all(
            "LMS Student Lesson Log",
            filters={"course": course, "student": enrollment.member},
            fields=["lesson", "completion_percentage", "is_completed", "video_speed", 
                   "last_watched_timestamp", "quiz_attempts", "quiz_best_score", 
                   "quiz_passed_at_attempt", "modified"],
            order_by="last_watched_timestamp desc"
        )
        custom_log_map = {l.lesson: l for l in custom_logs}
        
        # Calculate completed lessons count using BOTH sources
        # A lesson is complete if it's in LMS Course Progress OR custom log with is_completed=1
        completed_count = 0
        lesson_details = []
        
        for lesson_info in all_lessons:
            lesson_name = lesson_info["lesson"]
            lesson_title = lesson_info["title"]
            
            # Check if completed
            is_completed = lesson_name in lms_completed_map
            completion_date = lms_completed_map.get(lesson_name)
            
            # Get custom log info if exists
            custom_log = custom_log_map.get(lesson_name, {})
            if custom_log and custom_log.get("is_completed"):
                is_completed = True
                if not completion_date:
                    completion_date = custom_log.get("last_watched_timestamp") or custom_log.get("modified")
            
            if is_completed:
                completed_count += 1
            
            lesson_detail = {
                "lesson": lesson_name,
                "lesson_title": lesson_title,
                "is_completed": 1 if is_completed else 0,
                "completion_percentage": 100 if is_completed else (custom_log.get("completion_percentage") or 0),
                "completion_date": completion_date,
                "video_speed": custom_log.get("video_speed") or None,
                "last_watched_timestamp": custom_log.get("last_watched_timestamp"),
                "quiz_attempts": custom_log.get("quiz_attempts") or 0,
                "quiz_best_score": custom_log.get("quiz_best_score") or 0,
                "quiz_passed_at_attempt": custom_log.get("quiz_passed_at_attempt") or 0
            }
            lesson_details.append(lesson_detail)
        
        # Calculate overall progress (use max of enrollment progress and our calculation)
        calculated_progress = (completed_count / lesson_count * 100) if lesson_count > 0 else 0
        overall_progress = max(enrollment.progress or 0, calculated_progress)
        
        student_data = {
            "student": enrollment.member,
            "student_name": enrollment.member_name,
            "overall_progress": overall_progress,
            "completed_lessons": completed_count,
            "completion_date": enrollment.modified if overall_progress >= 100 else None,
            "lesson_details": lesson_details
        }
        
        # If specific lesson filter, add that info
        if lesson:
            matching_detail = next((d for d in lesson_details if d["lesson"] == lesson), None)
            if matching_detail:
                student_data["specific_lesson"] = matching_detail
        
        summary["students"].append(student_data)
    
    return summary


def get_course_lessons_ordered(course):
    """Get all lessons for a course in correct order."""
    lessons = []
    chapters = frappe.get_all(
        "Chapter Reference",
        filters={"parent": course},
        fields=["chapter", "idx"],
        order_by="idx"
    )
    
    for chapter in chapters:
        lesson_refs = frappe.get_all(
            "Lesson Reference",
            filters={"parent": chapter.chapter},
            fields=["lesson", "idx"],
            order_by="idx"
        )
        for ref in lesson_refs:
            title = frappe.db.get_value("Course Lesson", ref.lesson, "title") or ref.lesson
            lessons.append({
                "lesson": ref.lesson,
                "title": title,
                "chapter_idx": chapter.idx,
                "lesson_idx": ref.idx
            })
    
    return lessons


@frappe.whitelist()
def check_lesson_access(course, lesson=None, lesson_number=None):
    """
    Check if student can access a lesson.
    Returns True if previous lesson is completed or this is the first lesson.
    """
    student = frappe.session.user
    debug_tag = f"Access Check {student} {course} {lesson_number}"
    debug_logs = []
    
    def log(msg):
        debug_logs.append(msg)
    
    log(f"Starting check for {student}")
    
    # Instructors and Administrators can always access everything
    roles = frappe.get_roles(student)
    log(f"User Roles: {roles}")
    
    if student == "Administrator" or "Instructor" in roles:
        log("Access Granted: Admin/Instructor bypass")
        # frappe.log_error("\n".join(debug_logs), debug_tag)
        return {"can_access": True}

    if student == "Guest":
        log("Access Denied: Guest user")
        frappe.log_error("\n".join(debug_logs), debug_tag)
        return {"can_access": False, "reason": _("Ushbu darsni ko'rish maqsadida tizimga kiring.")}
    
    # Get all chapters and lessons in correct order
    chapters = frappe.get_all("Chapter Reference", 
                             filters={"parent": course}, 
                             fields=["chapter", "idx as chapter_idx"], 
                             order_by="idx",
                             ignore_permissions=True)
    
    ordered_lessons = []
    lesson_map = {}
    
    for c in chapters:
        lessons = frappe.get_all("Lesson Reference", 
                                filters={"parent": c.chapter}, 
                                fields=["lesson", "idx as lesson_idx"], 
                                order_by="idx",
                                ignore_permissions=True)
        for l in lessons:
            ordered_lessons.append(l.lesson)
            # Support both 1-1 and 1.1 formats
            key_dash = f"{c.chapter_idx}-{l.lesson_idx}"
            key_dot = f"{c.chapter_idx}.{l.lesson_idx}"
            lesson_map[key_dash] = l.lesson
            lesson_map[key_dot] = l.lesson

    log(f"Order: {ordered_lessons}")
    log(f"Map: {lesson_map}")

    if not ordered_lessons:
        log("Access Granted: No lessons found in course")
        # frappe.log_error("\n".join(debug_logs), debug_tag)
        return {"can_access": True}

    target_lesson = lesson
    if lesson_number:
        target_lesson = lesson_map.get(lesson_number)
    
    if not target_lesson:
        log(f"Access Denied: Target lesson not found for {lesson_number}")
        frappe.log_error("\n".join(debug_logs), debug_tag)
        return {"can_access": False, "reason": _("Dars topilmadi.")}

    try:
        current_idx = ordered_lessons.index(target_lesson)
    except ValueError:
        log(f"Access Denied: Lesson {target_lesson} not in course {course}")
        frappe.log_error("\n".join(debug_logs), debug_tag)
        return {"can_access": False, "reason": _("Dars ushbu kursga tegishli emas.")}

    log(f"Target Index: {current_idx}")

    # First lesson is always accessible
    if current_idx == 0:
        log("Access Granted: First lesson")
        # frappe.log_error("\n".join(debug_logs), debug_tag)
        return {"can_access": True}

    # Check previous lesson completion
    previous_lesson = ordered_lessons[current_idx - 1]
    log(f"Previous Lesson: {previous_lesson}")
    
    # Check both standard and our custom tracking
    is_completed = frappe.db.get_value("LMS Student Lesson Log", 
                                     {"student": student, "lesson": previous_lesson}, 
                                     "is_completed")
    log(f"Custom Log Completion: {is_completed}")
    
    if not is_completed:
        is_completed = frappe.db.exists("LMS Course Progress", {
            "lesson": previous_lesson,
            "member": student,
            "status": "Complete"
        })
        log(f"Standard Progress Exists: {is_completed}")

    if is_completed:
        log("Access Granted: Previous lesson completed")
        # frappe.log_error("\n".join(debug_logs), debug_tag)
        return {"can_access": True}
    else:
        prev_title = frappe.db.get_value("Course Lesson", previous_lesson, "title")
        log(f"Access Denied: Prerequisite {prev_title} not completed")
        frappe.log_error("\n".join(debug_logs), debug_tag)
        return {
            "can_access": False, 
            "reason": _("Navbatdagi darsga o'tish uchun avvalgi darsni yakunlang: {0}").format(prev_title),
            "previous_lesson": previous_lesson,
            "previous_lesson_title": prev_title
        }
