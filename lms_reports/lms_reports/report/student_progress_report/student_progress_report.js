// Copyright (c) 2026, LMS Reports and contributors

// GLOBAL CLICK EVENT (Bu qism xavfsizlik filtridan o'tadi va hamma uchun ishlaydi)
$(document).on('click', '.toggle-header', function(e) {
    // Agar ichidagi bironta link bosilsa, yopilib ketmasligi uchun
    if ($(e.target).is('a') || $(e.target).closest('a').length) return;

    var $card = $(this).closest('.student-item');
    var $details = $card.find('.details-body');
    
    // Animatsiya bilan ochish/yopish
    $details.slideToggle(200);
    
    // Iconni aylantirish
    $card.toggleClass('is-open');
});

frappe.query_reports["Student Progress Report"] = {
    "filters": [
        {
            "fieldname": "student",
            "label": __("Student"),
            "fieldtype": "Link",
            "options": "User",
            "default": frappe.session.user !== "Administrator" ? frappe.session.user : ""
        },
        {
            "fieldname": "course",
            "label": __("Course"),
            "fieldtype": "Link",
            "options": "LMS Course"
        },
        {
            "fieldname": "lesson",
            "label": __("Lesson"),
            "fieldtype": "Link",
            "options": "Course Lesson",
            "get_query": function () {
                var course = frappe.query_report.get_filter_value("course");
                if (course) return { filters: { "course": course } };
            }
        },
        {
            "fieldname": "is_completed",
            "label": __("Completed Only"),
            "fieldtype": "Check"
        }
    ],
    "onload": function(report) {
        // Template ko'rinishini majburiy qilish
        report.view_name = "Report Template";
    }
};