import frappe
import json
import os

def execute():
    try:
        path = frappe.get_app_path("lms", "lms", "workspace", "lms", "lms.json")
    except:
        path = "/home/gulinur/frappe-bench/apps/lms/lms/lms/workspace/lms/lms.json"
        
    print(f"Modifying {path}")
    
    with open(path, 'r') as f:
        data = json.load(f)

    # Check if exists
    for link in data.get('links', []):
        if link.get('link_to') == 'student-progress-dashboard':
            print("Link already exists")
            return

    new_link = {
       "hidden": 0,
       "is_query_report": 0,
       "label": "Student Progress Dashboard",
       "link_count": 0,
       "link_to": "student-progress-dashboard",
       "link_type": "Page",
       "onboard": 0,
       "type": "Link"
    }

    insert_idx = -1
    for i, link in enumerate(data.get('links', [])):
        if link.get('label') == 'Course Stats' and link.get('type') == 'Card Break':
             insert_idx = i + 1
             break

    if insert_idx != -1:
        data['links'].insert(insert_idx, new_link)
        print(f"Inserted link at index {insert_idx}")
    else:
        data['links'].append(new_link)
        print("Appended link")

    with open(path, 'w') as f:
        json.dump(data, f, indent=1, sort_keys=True)
        f.write('\n')
    
    print("Done")
