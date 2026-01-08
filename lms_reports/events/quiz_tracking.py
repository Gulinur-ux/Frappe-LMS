"""
Quiz tracking events
Updates course progress when quiz is submitted
"""

import frappe
from lms_reports.progress_tracker import update_course_progress_realtime


def on_quiz_submit(doc, method=None):
	"""
	Called when LMS Quiz Submission is created
	Updates course progress in real-time
	"""
	try:
		# Get quiz
		quiz_id = doc.quiz
		if not quiz_id:
			return

		# Find lesson with this quiz
		lesson = frappe.db.get_value("Course Lesson", {"quiz_id": quiz_id}, "name")
		if not lesson:
			frappe.logger().warning(f"No lesson found for quiz {quiz_id}")
			return

		# Get course from lesson
		course = frappe.db.get_value("Course Lesson", lesson, "course")
		if not course:
			return

		# Update course progress for this student
		progress_data = update_course_progress_realtime(course, doc.member)

		frappe.logger().info(
			f"Updated course progress for {doc.member} in {course}: {progress_data['overall_progress']}%"
		)

	except Exception as e:
		frappe.log_error(f"Error updating quiz progress: {str(e)}", "Quiz Tracking Error")
