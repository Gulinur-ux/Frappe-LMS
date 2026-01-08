# Copyright (c) 2026, LMS Reports and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from lms_reports.lms_reports.api import track_lesson_watch, update_quiz_result, check_lesson_access
from frappe.utils import now_datetime, flt
from unittest.mock import patch

class TestOne(FrappeTestCase):
    def setUp(self):
        super().setUp()
        self.enqueue_patcher = patch('frappe.enqueue')
        self.mock_enqueue = self.enqueue_patcher.start()

    def tearDown(self):
        self.enqueue_patcher.stop()
        super().tearDown()

    def test_video_tracking_api(self):
        """Test video tracking API creates logs and history"""
        lesson_title = "Test Lesson 1"
        course = "Test Course 1"
        
        # Mock student login
        frappe.session.user = "Administrator"
        
        # Create dummy course
        if not frappe.db.exists("LMS Course", course):
            c = frappe.new_doc("LMS Course")
            c.title = course
            # Required fields
            c.published = 1
            c.status = "Approved"
            c.short_introduction = "Test Short Intro"
            c.description = "Test Description"
            c.append("instructors", {"instructor": "Administrator"})
            c.save()
            course_name = c.name
        else:
            course_name = frappe.db.get_value("LMS Course", {"title": course}, "name")

        # Create dummy chapter
        chapter_title = "Test Chapter 1"
        if not frappe.db.exists("Course Chapter", {"title": chapter_title, "course": course_name}):
            ch = frappe.new_doc("Course Chapter")
            ch.title = chapter_title
            ch.course = course_name
            ch.save(ignore_permissions=True)
            chapter_name = ch.name
        else:
            chapter_name = frappe.db.get_value("Course Chapter", {"title": chapter_title, "course": course_name}, "name")

        # Create dummy lesson
        if not frappe.db.exists("Course Lesson", {"title": lesson_title, "course": course_name}):
            l = frappe.new_doc("Course Lesson")
            l.title = lesson_title
            l.course = course_name
            l.chapter = chapter_name
            l.save(ignore_permissions=True)
            lesson_name = l.name
        else:
            lesson_name = frappe.db.get_value("Course Lesson", {"title": lesson_title, "course": course_name}, "name")
            
        # Test API with real lesson name
        track_lesson_watch(
            lesson=lesson_name,
            course=course_name,
            video_speed="1.5x",
            watched_duration=60,
            video_total_duration=120,
            start_time=0,
            end_time=60
        )
        
        # Verify log created
        log = frappe.db.get_value("LMS Student Lesson Log", 
                                {"student": "Administrator", "lesson": lesson_name}, 
                                ["video_speed", "watched_duration", "completion_percentage", "name"], 
                                as_dict=1)
        
        self.assertEqual(log.video_speed, "1.5x")
        self.assertEqual(flt(log.watched_duration), 60.0)
        self.assertEqual(flt(log.completion_percentage), 50.0)
        
        # Verify history
        doc = frappe.get_doc("LMS Student Lesson Log", log.name)
        self.assertTrue(len(doc.watch_history) > 0)
        self.assertEqual(doc.watch_history[0].video_speed, "1.5x")

    def test_lesson_access_control(self):
        """Test lesson access control logic"""
        course_title = "Test Access Course"
        lesson1_title = "Lesson 1"
        lesson2_title = "Lesson 2"
        
        frappe.session.user = "Administrator"
        
        # Setup course
        if not frappe.db.exists("LMS Course", course_title):
            c = frappe.new_doc("LMS Course")
            c.title = course_title
            c.published = 1
            c.status = "Approved"
            c.short_introduction = "Test Short Intro"
            c.description = "Test Description"
            c.append("instructors", {"instructor": "Administrator"})
            c.save()
            course_name = c.name
        else:
            course_name = frappe.db.get_value("LMS Course", {"title": course_title}, "name")

        # Setup chapter
        chapter_title = "Test Chapter 1"
        if not frappe.db.exists("Course Chapter", {"title": chapter_title, "course": course_name}):
            ch = frappe.new_doc("Course Chapter")
            ch.title = chapter_title
            ch.course = course_name
            ch.save(ignore_permissions=True)
            chapter_name = ch.name
        else:
            chapter_name = frappe.db.get_value("Course Chapter", {"title": chapter_title, "course": course_name}, "name")
            
        # Setup lessons
        if not frappe.db.exists("Course Lesson", {"title": lesson1_title, "course": course_name}):
            l1 = frappe.new_doc("Course Lesson")
            l1.title = lesson1_title
            l1.course = course_name
            l1.chapter = chapter_name
            l1.save(ignore_permissions=True)
            lesson1_name = l1.name
        else:
            lesson1_name = frappe.db.get_value("Course Lesson", {"title": lesson1_title, "course": course_name}, "name")

        if not frappe.db.exists("Course Lesson", {"title": lesson2_title, "course": course_name}):
            l2 = frappe.new_doc("Course Lesson")
            l2.title = lesson2_title
            l2.course = course_name
            l2.chapter = chapter_name
            l2.save(ignore_permissions=True)
            lesson2_name = l2.name
        else:
            lesson2_name = frappe.db.get_value("Course Lesson", {"title": lesson2_title, "course": course_name}, "name")
            
        # Enroll student
        if not frappe.db.exists("LMS Enrollment", {"course": course_name, "member": "Administrator"}):
            enrollment = frappe.new_doc("LMS Enrollment")
            enrollment.course = course_name
            enrollment.member = "Administrator"
            enrollment.save(ignore_permissions=True)

        # Clear logs
        frappe.db.delete("LMS Student Lesson Log", {"student": "Administrator", "course": course_name})
        
        # Test access to Lesson 2 (should be denied)
        access = check_lesson_access(course_name, lesson2_name)
        self.assertFalse(access.get("can_access"), f"Should fail because {lesson1_name} is not complete. Reason: {access.get('reason')}")
        
        # Complete Lesson 1
        track_lesson_watch(
            lesson=lesson1_name,
            course=course_name,
            video_speed="1x",
            watched_duration=100,
            video_total_duration=100
        )
        
        # Test access to Lesson 2 (should be allowed)
        access = check_lesson_access(course_name, lesson2_name)
        self.assertTrue(access.get("can_access"), f"Should pass because {lesson1_name} is complete. Access info: {access}")

    def test_quiz_tracking(self):
        """Test quiz submission updates lesson log"""
        lesson_title = "Test Quiz Lesson"
        course_title = "Test Quiz Course"
        quiz_title = "Test Quiz 1"
        
        frappe.session.user = "Administrator"
        
        # Setup course
        if not frappe.db.exists("LMS Course", course_title):
            c = frappe.new_doc("LMS Course")
            c.title = course_title
            c.published = 1
            c.status = "Approved"
            c.short_introduction = "Test Short Intro"
            c.description = "Test Description"
            c.append("instructors", {"instructor": "Administrator"})
            c.save()
            course_name = c.name
        else:
            course_name = frappe.db.get_value("LMS Course", {"title": course_title}, "name")

        # Setup chapter
        chapter_title = "Test Quiz Chapter"
        if not frappe.db.exists("Course Chapter", {"title": chapter_title, "course": course_name}):
            ch = frappe.new_doc("Course Chapter")
            ch.title = chapter_title
            ch.course = course_name
            ch.save(ignore_permissions=True)
            chapter_name = ch.name
        else:
            chapter_name = frappe.db.get_value("Course Chapter", {"title": chapter_title, "course": course_name}, "name")

        # Setup lesson
        if not frappe.db.exists("Course Lesson", {"title": lesson_title, "course": course_name}):
            l = frappe.new_doc("Course Lesson")
            l.title = lesson_title
            l.course = course_name
            l.chapter = chapter_name
            l.save(ignore_permissions=True)
            lesson_name = l.name
        else:
            lesson_name = frappe.db.get_value("Course Lesson", {"title": lesson_title, "course": course_name}, "name")

        # Setup Quiz
        if not frappe.db.exists("LMS Quiz", {"title": quiz_title}):
            q = frappe.new_doc("LMS Quiz")
            q.title = quiz_title
            q.lesson = lesson_name
            q.passing_percentage = 50
            q.total_marks = 100
            q.save(ignore_permissions=True)
            quiz_name = q.name
        else:
            quiz_name = frappe.db.get_value("LMS Quiz", {"title": quiz_title}, "name")
            
        # Enroll student to test save_progress
        if not frappe.db.exists("LMS Enrollment", {"course": course_name, "member": "Administrator"}):
            enrollment = frappe.new_doc("LMS Enrollment")
            enrollment.course = course_name
            enrollment.member = "Administrator"
            enrollment.save(ignore_permissions=True)

        # Create Quiz Submission (passing score)
        qs = frappe.new_doc("LMS Quiz Submission")
        qs.quiz = quiz_name
        qs.member = "Administrator"
        qs.score = 100
        qs.percentage = 100
        qs.passing_percentage = 50
        qs.save(ignore_permissions=True)
        
        # Verify Log Updated
        log = frappe.db.get_value("LMS Student Lesson Log",
            {"student": "Administrator", "lesson": lesson_name},
            ["quiz_attempts", "quiz_best_score", "name", "last_watched_timestamp"],
            as_dict=1
        )
        
        self.assertTrue(log, "Log should exist after quiz submission")
        self.assertEqual(log.quiz_attempts, 1)
        self.assertEqual(flt(log.quiz_best_score), 100.0)

        # Verify Timestamp
        self.assertIsNotNone(log.last_watched_timestamp, "Quiz submission should update last_watched_timestamp")
        
        # Verify Standard LMS Progress Updated
        progress_exists = frappe.db.exists("LMS Course Progress", {
            "lesson": lesson_name, 
            "member": "Administrator",
            "status": "Complete"
        })
        self.assertTrue(progress_exists, "Standard LMS Course Progress should be created")
