"""
Lesson Unlock Logic
Prevents students from accessing next lessons until previous lessons are completed
"""

import frappe
from frappe import _


@frappe.whitelist()
def check_lesson_access(lesson, course=None, member=None):
	"""
	Check if student can access this lesson

	Rules:
	1. Must complete previous lesson (video 95%+ watched)
	2. If previous lesson has quiz, must pass quiz (>= passing %)
	3. Instructors can always access

	Returns:
		dict: {
			'can_access': bool,
			'reason': str,  # If can_access=False
			'previous_lesson': str  # Name of lesson to complete
		}
	"""
	if not member:
		member = frappe.session.user

	# Check if user is instructor
	if is_instructor(course, member):
		return {
			'can_access': True,
			'reason': 'Instructor access'
		}

	# Get lesson details
	lesson_doc = frappe.get_doc("Course Lesson", lesson)
	if not course:
		course = lesson_doc.course

	# Get all lessons in this course (ordered by idx)
	all_lessons = frappe.get_all(
		"Course Lesson",
		filters={"course": course},
		fields=["name", "title", "idx", "quiz_id", "chapter"],
		order_by="idx asc"
	)

	# Find current lesson index
	current_idx = None
	for i, l in enumerate(all_lessons):
		if l.name == lesson:
			current_idx = i
			break

	if current_idx is None:
		return {
			'can_access': False,
			'reason': _('Lesson not found in course')
		}

	# First lesson is always accessible
	if current_idx == 0:
		return {
			'can_access': True,
			'reason': 'First lesson'
		}

	# Check if previous lesson is completed
	previous_lesson = all_lessons[current_idx - 1]
	previous_status = get_lesson_completion_status(previous_lesson.name, member)

	if not previous_status['is_completed']:
		return {
			'can_access': False,
			'reason': _('You must complete the previous lesson first'),
			'previous_lesson': previous_lesson.name,
			'previous_lesson_title': previous_lesson.title,
			'missing': previous_status['missing']
		}

	# All checks passed
	return {
		'can_access': True,
		'reason': 'All requirements met'
	}


def get_lesson_completion_status(lesson, member):
	"""
	Check if lesson is completed

	Completion criteria:
	- Video: 95%+ watched OR marked as complete
	- Quiz: If quiz exists, must pass (score >= passing_percentage)

	Returns:
		dict: {
			'is_completed': bool,
			'video_completed': bool,
			'quiz_completed': bool or None,
			'missing': list  # What's missing to complete
		}
	"""
	missing = []

	# Check video progress
	video_progress = frappe.db.get_value(
		"LMS Student Lesson Log",
		{
			"lesson": lesson,
			"student": member
		},
		["completion_percentage", "is_completed"],
		as_dict=True
	)

	video_completed = False
	if video_progress:
		completion = video_progress.get('completion_percentage', 0)
		video_completed = completion >= 95 or video_progress.get('is_completed')

	if not video_completed:
		missing.append('Watch video to 95%+')

	# Check quiz (if exists)
	lesson_doc = frappe.get_doc("Course Lesson", lesson)
	quiz_completed = None

	if lesson_doc.quiz_id:
		# Quiz exists, must pass it
		passing_percentage = frappe.db.get_value(
			"LMS Quiz",
			lesson_doc.quiz_id,
			"passing_percentage"
		) or 70

		quiz_result = frappe.db.get_value(
			"LMS Quiz Submission",
			{
				"quiz": lesson_doc.quiz_id,
				"member": member
			},
			["percentage", "score"],
			as_dict=True,
			order_by="creation desc"
		)

		if quiz_result:
			quiz_score = quiz_result.get('percentage', 0)
			quiz_completed = quiz_score >= passing_percentage
		else:
			quiz_completed = False

		if not quiz_completed:
			missing.append(f'Pass quiz ({passing_percentage}%+)')

	# Lesson is completed if video is done AND quiz is done (if quiz exists)
	is_completed = video_completed and (quiz_completed if lesson_doc.quiz_id else True)

	return {
		'is_completed': is_completed,
		'video_completed': video_completed,
		'quiz_completed': quiz_completed,
		'missing': missing
	}


def is_instructor(course, member):
	"""Check if member is instructor of this course"""
	if not course or not member:
		return False

	# Check if user has instructor role
	has_role = frappe.db.exists(
		"Has Role",
		{
			"parent": member,
			"role": ["in", ["Course Creator", "Moderator", "System Manager"]]
		}
	)

	if has_role:
		# Check if they're assigned to this course
		is_course_instructor = frappe.db.exists(
			"LMS Course Instructor",
			{
				"parent": course,
				"instructor": member
			}
		)

		if is_course_instructor:
			return True

		# System Manager can access all
		if "System Manager" in frappe.get_roles(member):
			return True

	return False


@frappe.whitelist()
def get_course_lesson_lock_status(course, member=None):
	"""
	Get lock status for all lessons in a course

	Returns:
		dict: {
			'lesson-name': {
				'can_access': bool,
				'reason': str,
				'is_completed': bool
			}
		}
	"""
	if not member:
		member = frappe.session.user

	# Get all lessons
	lessons = frappe.get_all(
		"Course Lesson",
		filters={"course": course},
		fields=["name", "title", "idx"],
		order_by="idx asc"
	)

	result = {}
	for lesson in lessons:
		access_check = check_lesson_access(lesson.name, course, member)
		completion = get_lesson_completion_status(lesson.name, member)

		result[lesson.name] = {
			'can_access': access_check['can_access'],
			'reason': access_check.get('reason', ''),
			'is_completed': completion['is_completed'],
			'video_completed': completion['video_completed'],
			'quiz_completed': completion['quiz_completed']
		}

	return result
