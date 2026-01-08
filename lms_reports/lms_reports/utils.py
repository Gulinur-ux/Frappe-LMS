import frappe

def create_demo_users():
    users = [
        {"first_name": "Ali", "email": "ali@example.com", "password": "Student123!"},
        {"first_name": "Vali", "email": "vali@example.com", "password": "Student123!"}
    ]

    for u in users:
        if frappe.db.exists("User", u["email"]):
            user = frappe.get_doc("User", u["email"])
        else:
            user = frappe.new_doc("User")
            user.email = u["email"]
            user.first_name = u["first_name"]
            user.enabled = 1
            user.send_welcome_email = 0
            user.insert(ignore_permissions=True)

        # Set Password
        user.new_password = u["password"]
        user.save(ignore_permissions=True)
        
        # Add Role
        user.add_roles("LMS Student")
        
        frappe.db.commit()
        print(f"User {u['first_name']} created/updated with email {u['email']}")

