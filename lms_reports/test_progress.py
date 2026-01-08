import frappe
import json
from lms_reports.progress_tracker import get_bulk_course_progress

def test_progress():
    frappe.init(site="lms.localhost")
    frappe.connect()
    
    # Simulate Administrator session
    frappe.set_user("Administrator")
    
    courses = ["moliya-darslari", "dbr-darsliklari"]
    progress = get_bulk_course_progress(courses)
    
    print(json.dumps(progress, indent=2))

if __name__ == "__main__":
    test_progress()
