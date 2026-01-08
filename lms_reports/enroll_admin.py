import frappe

def enroll_admin():
    frappe.init(site="lms.localhost")
    frappe.connect()
    
    courses = frappe.get_all("LMS Course", filters={"published": 1})
    print(f"Found {len(courses)} published courses")
    
    for course in courses:
        if not frappe.db.exists("LMS Enrollment", {"course": course.name, "member": "Administrator"}):
            enrollment = frappe.new_doc("LMS Enrollment")
            enrollment.course = course.name
            enrollment.member = "Administrator"
            enrollment.member_type = "Student"
            enrollment.insert(ignore_permissions=True)
            print(f"Enrolled Administrator in {course.name}")
        else:
            print(f"Administrator already enrolled in {course.name}")
            
    frappe.db.commit()

if __name__ == "__main__":
    enroll_admin()
