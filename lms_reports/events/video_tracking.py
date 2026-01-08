"""
Video tracking events
Updates course progress when video watch duration is recorded
"""

import frappe
from lms_reports.progress_tracker import update_course_progress_realtime


def on_video_watch(doc, method=None):
	"""
	Called when LMS Video Watch Duration is created/updated
	Updates course progress in real-time
	"""
	try:
		# Get lesson from video watch duration
		lesson = doc.lesson
		if not lesson:
			return

		# Get course from lesson
		course = frappe.db.get_value("Course Lesson", lesson, "course")
		if not course:
			return

		# Update course progress for this student
		update_course_progress_realtime(course, doc.owner)

		frappe.logger().info(f"Updated course progress for {doc.owner} in {course}")

	except Exception as e:
		frappe.log_error(f"Error updating video progress: {str(e)}", "Video Tracking Error")
