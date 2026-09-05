IAM Access Request & Provisioning Tracker

A Flask and SQLite-based Identity and Access Management (IAM) application for managing employee access requests, approvals, provisioning, directory groups, and access reviews.

Features
Access request ticket creation
Employee directory validation
Manager approval and rejection workflow
Provisioning status tracking
User-to-directory-group assignment
Access removal
Disabled-user access protection
Directory users and groups
User access review
Access assignment timestamps
Dashboard statistics
SQLite database with schema repair/migration logic
Technology Stack
Python
Flask
SQLite
HTML
CSS
Jinja2
Application Workflow
Access Request
      ↓
Manager Approval
      ↓
Provisioning
      ↓
Access Assigned
      ↓
Access Review
      ↓
Access Removal

Example IAM Functions

The application supports:

Employee ID validation
Active/disabled user validation
Access request tracking
Approval decisions
Directory group provisioning
Access review
Access revocation
Assignment history
Running Locally

Clone the repository and navigate into the project directory.

Install dependencies:

pip install -r requirements.txt


Run the application:

python app.py


Open:

http://127.0.0.1:5000/

Project Structure
IAM/
├── app.py
├── requirements.txt
├── README.md
├── templates/
└── static/

Disclaimer

This is a portfolio/demo IAM application. It does not connect to a production identity provider or enterprise directory service.
