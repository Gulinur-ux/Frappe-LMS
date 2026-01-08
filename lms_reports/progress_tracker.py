"""
Real-time Course Progress Tracker for LMS
Calculates progress based on:
- Video watch completion (from LMS Video Watch Duration)
- Quiz completion (from LMS Quiz Submission)
- Lesson completion (from LMS Course Progress)
"""

import frappe
from frappe.utils import flt, cint


def get_enhanced_course_progress(course, member=None):
	"""
	Calculate real-time course progress including video and quiz completion

	Args:
		course: Course name
		member: Student email (defaults to current user)

	Returns:
		dict: {
			'overall_progress': float,  # 0-100
			'lessons_completed': int,
			'total_lessons': int,
			'videos_watched': int,
			'quizzes_completed': int
		}
	"""
	if not member:
		member = frappe.session.user

	# Get all lessons in course
	lessons = frappe.db.get_all(
		"Course Lesson",
		filters={"course": course},
		fields=["name", "quiz_id"]
	)

	if not lessons:
		return {
			'overall_progress': 0,
			'lessons_completed': 0,
			'total_lessons': 0,
			'videos_watched': 0,
			'quizzes_completed': 0
		}

	total_lessons = len(lessons)
	completed_lessons = 0
	videos_watched = 0
	quizzes_completed = 0
	total_progress_points = 0

	for lesson in lessons:
		lesson_progress = get_lesson_progress(lesson.name, member)
		total_progress_points += lesson_progress['progress_percentage']

		if lesson_progress['is_completed']:
			completed_lessons += 1

		if lesson_progress['video_watched']:
			videos_watched += 1

		if lesson_progress['quiz_completed']:
			quizzes_completed += 1

	# Calculate overall progress (average of all lesson progress)
	overall_progress = flt(total_progress_points / total_lessons, 2) if total_lessons > 0 else 0

	return {
		'overall_progress': overall_progress,
		'lessons_completed': completed_lessons,
		'total_lessons': total_lessons,
		'videos_watched': videos_watched,
		'quizzes_completed': quizzes_completed
	}


def get_lesson_progress(lesson, member):
	"""
	Calculate progress for a single lesson

	Progress calculation:
	- Video: 60% weight
	- Quiz: 40% weight
	- Lesson marked complete: 100%

	Returns:
		dict: {
			'progress_percentage': float (0-100),
			'is_completed': bool,
			'video_watched': bool,
			'quiz_completed': bool
		}
	"""
	# Check if lesson is marked as complete
	is_complete = frappe.db.exists(
		"LMS Course Progress",
		{
			"lesson": lesson,
			"member": member,
			"status": "Complete"
		}
	)

	if is_complete:
		return {
			'progress_percentage': 100,
			'is_completed': True,
			'video_watched': True,
			'quiz_completed': True
		}

	# Get video watch progress from LMS Student Lesson Log
	video_progress = frappe.db.get_value(
		"LMS Student Lesson Log",
		{
			"lesson": lesson,
			"student": member
		},
		["completion_percentage", "is_completed"],
		as_dict=True
	) or {}

	video_completion = flt(video_progress.get('completion_percentage', 0))
	video_watched = video_completion >= 95  # Consider 95%+ as watched

	# Get quiz completion
	lesson_doc = frappe.get_doc("Course Lesson", lesson)
	quiz_completed = False
	quiz_score = 0

	if lesson_doc.quiz_id:
		quiz_result = frappe.db.get_value(
			"LMS Quiz Submission",
			{
				"quiz": lesson_doc.quiz_id,
				"member": member
			},
			["score", "percentage"],
			as_dict=True
		)

		if quiz_result:
			quiz_score = flt(quiz_result.get('percentage', 0))
			# Get passing percentage from quiz
			passing_percentage = frappe.db.get_value(
				"LMS Quiz",
				lesson_doc.quiz_id,
				"passing_percentage"
			) or 70

			quiz_completed = quiz_score >= passing_percentage

	# Calculate weighted progress
	# Video: 60%, Quiz: 40%
	if lesson_doc.quiz_id:
		# Lesson has both video and quiz
		progress = (video_completion * 0.6) + (quiz_score * 0.4)
	else:
		# Lesson only has video
		progress = video_completion

	return {
		'progress_percentage': flt(progress, 2),
		'is_completed': video_watched and (quiz_completed if lesson_doc.quiz_id else True),
		'video_watched': video_watched,
		'quiz_completed': quiz_completed if lesson_doc.quiz_id else None
	}


@frappe.whitelist()
def get_my_course_progress(course):
	"""
	API endpoint to get current user's course progress
	"""
	return get_enhanced_course_progress(course, frappe.session.user)


@frappe.whitelist()
def update_course_progress_realtime(course, member=None):
	"""
	Update LMS Enrollment progress with real-time calculation
	Called after video watch or quiz completion
	"""
	if not member:
		member = frappe.session.user

	progress_data = get_enhanced_course_progress(course, member)

	# Update LMS Enrollment
	enrollment = frappe.db.get_value(
		"LMS Enrollment",
		{
			"course": course,
			"member": member
		},
		"name"
	)

	if enrollment:
		frappe.db.set_value(
			"LMS Enrollment",
			enrollment,
			"progress",
			progress_data['overall_progress']
		)
		frappe.db.commit()

	return progress_data


@frappe.whitelist()
def get_bulk_course_progress(courses):
	"""
	Fetch progress for multiple courses at once.
	courses: List of course names or a JSON string of course names.
	"""
	import json
	if isinstance(courses, str):
		courses = json.loads(courses)
	
	results = {}
	member = frappe.session.user
	
	if member == "Guest":
		return results

	for course in courses:
		results[course] = get_enhanced_course_progress(course, member)
		frappe.errprint(f"[DEBUG] Progress for {course}: {results[course]}")
	
	frappe.log_error(title="Progress Tracker Debug", message=f"User: {member}, Courses: {courses}, Results: {results}")
	
	return results
