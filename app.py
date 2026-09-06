from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os

app = Flask(__name__)

app.secret_key = "iam-tracker-secret-key"

DATABASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "iam_tracker.db"
)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():

    connection = get_db_connection()

    # =====================================================
    # ACCESS REQUEST TICKETS
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT UNIQUE NOT NULL,
            employee_name TEXT NOT NULL,
            employee_id TEXT NOT NULL,
            application TEXT NOT NULL,
            access_requested TEXT NOT NULL,
            business_reason TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # MANAGER APPROVALS
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT NOT NULL,
            approver_name TEXT NOT NULL,
            approval_status TEXT NOT NULL,
            approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # PROVISIONING RECORDS
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS provisioning (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT NOT NULL,
            provisioned_by TEXT NOT NULL,
            provisioning_status TEXT NOT NULL,
            provisioned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # DIRECTORY USERS
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE NOT NULL,
            employee_name TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    # =====================================================
    # DIRECTORY GROUPS
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT UNIQUE NOT NULL
        )
    """)

    # =====================================================
    # USER GROUP ASSIGNMENTS
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS user_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            group_name TEXT NOT NULL,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(employee_id, group_name)
        )
    """)

    # =====================================================
    # REPAIR OLD USER_GROUPS TABLE
    # =====================================================

    columns = connection.execute("""
        PRAGMA table_info(user_groups)
    """).fetchall()

    column_names = [
        column["name"]
        for column in columns
    ]

    if "assigned_at" not in column_names:

        connection.execute("""
            ALTER TABLE user_groups
            ADD COLUMN assigned_at TIMESTAMP
        """)

        # Give old assignments a timestamp
        connection.execute("""
            UPDATE user_groups
            SET assigned_at = CURRENT_TIMESTAMP
            WHERE assigned_at IS NULL
        """)

    else:

        # Repair existing rows where assigned_at is NULL
        connection.execute("""
            UPDATE user_groups
            SET assigned_at = CURRENT_TIMESTAMP
            WHERE assigned_at IS NULL
        """)

    # =====================================================
    # SAMPLE USERS
    # =====================================================

    sample_users = [
        ("EMP001", "Rahul Kumar", "Active"),
        ("EMP002", "Priya Sharma", "Active"),
        ("EMP003", "Arjun Reddy", "Disabled")
    ]

    connection.executemany("""
        INSERT OR IGNORE INTO users
        (
            employee_id,
            employee_name,
            status
        )
        VALUES (?, ?, ?)
    """, sample_users)

    # =====================================================
    # SAMPLE GROUPS
    # =====================================================

    sample_groups = [
        ("Finance-Users",),
        ("HR-Users",),
        ("IT-Users",)
    ]

    connection.executemany("""
        INSERT OR IGNORE INTO groups
        (
            group_name
        )
        VALUES (?)
    """, sample_groups)

    connection.commit()
    connection.close()


# =========================================================
# HOME / DASHBOARD
# =========================================================

@app.route("/")
def home():

    connection = get_db_connection()

    tickets = connection.execute("""
        SELECT *
        FROM tickets
        ORDER BY id DESC
    """).fetchall()

    total_tickets = connection.execute("""
        SELECT COUNT(*)
        FROM tickets
    """).fetchone()[0]

    new_tickets = connection.execute("""
        SELECT COUNT(*)
        FROM tickets
        WHERE status = 'New'
    """).fetchone()[0]

    approved_tickets = connection.execute("""
        SELECT COUNT(*)
        FROM tickets
        WHERE status = 'Approved'
    """).fetchone()[0]

    provisioning_tickets = connection.execute("""
        SELECT COUNT(*)
        FROM tickets
        WHERE status = 'Provisioning'
    """).fetchone()[0]

    resolved_tickets = connection.execute("""
        SELECT COUNT(*)
        FROM tickets
        WHERE status = 'Resolved'
    """).fetchone()[0]

    active_users = connection.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE status = 'Active'
    """).fetchone()[0]

    total_groups = connection.execute("""
        SELECT COUNT(*)
        FROM groups
    """).fetchone()[0]

    total_assignments = connection.execute("""
        SELECT COUNT(*)
        FROM user_groups
    """).fetchone()[0]

    connection.close()

    return render_template(
        "index.html",
        tickets=tickets,
        total_tickets=total_tickets,
        new_tickets=new_tickets,
        approved_tickets=approved_tickets,
        provisioning_tickets=provisioning_tickets,
        resolved_tickets=resolved_tickets,
        active_users=active_users,
        total_groups=total_groups,
        total_assignments=total_assignments
    )


# =========================================================
# CREATE ACCESS REQUEST
# =========================================================

@app.route("/create-ticket", methods=["GET", "POST"])
def create_ticket():

    if request.method == "POST":

        employee_name = request.form.get(
            "employee_name",
            ""
        ).strip()

        employee_id = request.form.get(
            "employee_id",
            ""
        ).strip()

        application = request.form.get(
            "application",
            ""
        ).strip()

        access_requested = request.form.get(
            "access_requested",
            ""
        ).strip()

        business_reason = request.form.get(
            "business_reason",
            ""
        ).strip()

        if (
            not employee_name
            or not employee_id
            or not application
        ):

            flash(
                "Please fill in all required fields.",
                "error"
            )

            return redirect(
                url_for("create_ticket")
            )

        connection = get_db_connection()

        user = connection.execute("""
            SELECT *
            FROM users
            WHERE employee_id = ?
        """, (
            employee_id,
        )).fetchone()

        if user is None:

            connection.close()

            flash(
                "Employee ID does not exist in the directory.",
                "error"
            )

            return redirect(
                url_for("create_ticket")
            )

        if user["status"] != "Active":

            connection.close()

            flash(
                "Access request cannot be created for a disabled user.",
                "error"
            )

            return redirect(
                url_for("create_ticket")
            )

        last_ticket = connection.execute("""
            SELECT ticket_id
            FROM tickets
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

        if last_ticket:

            try:

                last_number = int(
                    last_ticket["ticket_id"].replace(
                        "IAM-",
                        ""
                    )
                )

                ticket_number = last_number + 1

            except ValueError:

                ticket_number = 1001

        else:

            ticket_number = 1001

        ticket_id = f"IAM-{ticket_number}"

        connection.execute("""
            INSERT INTO tickets
            (
                ticket_id,
                employee_name,
                employee_id,
                application,
                access_requested,
                business_reason,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket_id,
            employee_name,
            employee_id,
            application,
            access_requested,
            business_reason,
            "New"
        ))

        connection.commit()
        connection.close()

        flash(
            f"Access request {ticket_id} created successfully.",
            "success"
        )

        return redirect(
            url_for(
                "ticket",
                ticket_id=ticket_id
            )
        )

    return render_template(
        "create_ticket.html"
    )


# =========================================================
# VIEW / UPDATE TICKET
# =========================================================

@app.route(
    "/ticket/<ticket_id>",
    methods=["GET", "POST"]
)
def ticket(ticket_id):

    connection = get_db_connection()

    if request.method == "POST":

        new_status = request.form.get(
            "status",
            ""
        ).strip()

        allowed_statuses = [
            "New",
            "Pending Approval",
            "Approved",
            "Provisioning",
            "Resolved",
            "Closed",
            "Rejected"
        ]

        if new_status not in allowed_statuses:

            connection.close()

            flash(
                "Invalid ticket status.",
                "error"
            )

            return redirect(
                url_for(
                    "ticket",
                    ticket_id=ticket_id
                )
            )

        connection.execute("""
            UPDATE tickets
            SET status = ?
            WHERE ticket_id = ?
        """, (
            new_status,
            ticket_id
        ))

        connection.commit()

        flash(
            "Ticket status updated successfully.",
            "success"
        )

    ticket_data = connection.execute("""
        SELECT *
        FROM tickets
        WHERE ticket_id = ?
    """, (
        ticket_id,
    )).fetchone()

    if ticket_data is None:

        connection.close()

        return "Ticket not found.", 404

    approvals = connection.execute("""
        SELECT *
        FROM approvals
        WHERE ticket_id = ?
        ORDER BY id DESC
    """, (
        ticket_id,
    )).fetchall()

    provisioning_records = connection.execute("""
        SELECT *
        FROM provisioning
        WHERE ticket_id = ?
        ORDER BY id DESC
    """, (
        ticket_id,
    )).fetchall()

    connection.close()

    return render_template(
        "ticket.html",
        ticket=ticket_data,
        approvals=approvals,
        provisioning_records=provisioning_records
    )


# =========================================================
# MANAGER APPROVAL
# =========================================================

@app.route(
    "/ticket/<ticket_id>/approval",
    methods=["POST"]
)
def approval(ticket_id):

    approver_name = request.form.get(
        "approver_name",
        ""
    ).strip()

    approval_status = request.form.get(
        "approval_status",
        ""
    ).strip()

    if not approver_name:

        flash(
            "Approver name is required.",
            "error"
        )

        return redirect(
            url_for(
                "ticket",
                ticket_id=ticket_id
            )
        )

    if approval_status not in [
        "Approved",
        "Rejected"
    ]:

        flash(
            "Invalid approval decision.",
            "error"
        )

        return redirect(
            url_for(
                "ticket",
                ticket_id=ticket_id
            )
        )

    connection = get_db_connection()

    ticket_data = connection.execute("""
        SELECT *
        FROM tickets
        WHERE ticket_id = ?
    """, (
        ticket_id,
    )).fetchone()

    if ticket_data is None:

        connection.close()

        return "Ticket not found.", 404

    connection.execute("""
        INSERT INTO approvals
        (
            ticket_id,
            approver_name,
            approval_status
        )
        VALUES (?, ?, ?)
    """, (
        ticket_id,
        approver_name,
        approval_status
    ))

    connection.execute("""
        UPDATE tickets
        SET status = ?
        WHERE ticket_id = ?
    """, (
        approval_status,
        ticket_id
    ))

    connection.commit()
    connection.close()

    flash(
        f"Ticket {ticket_id} marked as {approval_status}.",
        "success"
    )

    return redirect(
        url_for(
            "ticket",
            ticket_id=ticket_id
        )
    )


# =========================================================
# TICKET PROVISIONING
# =========================================================

@app.route(
    "/ticket/<ticket_id>/provision",
    methods=["POST"]
)
def provision(ticket_id):

    provisioned_by = request.form.get(
        "provisioned_by",
        ""
    ).strip()

    provisioning_status = request.form.get(
        "provisioning_status",
        ""
    ).strip()

    if not provisioned_by:

        flash(
            "Provisioned by name is required.",
            "error"
        )

        return redirect(
            url_for(
                "ticket",
                ticket_id=ticket_id
            )
        )

    if provisioning_status not in [
        "Started",
        "Completed",
        "Failed"
    ]:

        flash(
            "Invalid provisioning status.",
            "error"
        )

        return redirect(
            url_for(
                "ticket",
                ticket_id=ticket_id
            )
        )

    connection = get_db_connection()

    ticket_data = connection.execute("""
        SELECT *
        FROM tickets
        WHERE ticket_id = ?
    """, (
        ticket_id,
    )).fetchone()

    if ticket_data is None:

        connection.close()

        return "Ticket not found.", 404

    connection.execute("""
        INSERT INTO provisioning
        (
            ticket_id,
            provisioned_by,
            provisioning_status
        )
        VALUES (?, ?, ?)
    """, (
        ticket_id,
        provisioned_by,
        provisioning_status
    ))

    if provisioning_status == "Started":

        ticket_status = "Provisioning"

    elif provisioning_status == "Completed":

        ticket_status = "Resolved"

    else:

        ticket_status = "Provisioning"

    connection.execute("""
        UPDATE tickets
        SET status = ?
        WHERE ticket_id = ?
    """, (
        ticket_status,
        ticket_id
    ))

    connection.commit()
    connection.close()

    flash(
        f"Provisioning status updated to {provisioning_status}.",
        "success"
    )

    return redirect(
        url_for(
            "ticket",
            ticket_id=ticket_id
        )
    )


# =========================================================
# USER PROVISIONING
# =========================================================

@app.route(
    "/provision-user",
    methods=["GET", "POST"]
)
def provision_user():

    connection = get_db_connection()

    if request.method == "POST":

        employee_id = request.form.get(
            "employee_id",
            ""
        ).strip()

        group_name = request.form.get(
            "group_name",
            ""
        ).strip()

        if not employee_id or not group_name:

            connection.close()

            flash(
                "Please select both an employee and a directory group.",
                "error"
            )

            return redirect(
                url_for("provision_user")
            )

        user = connection.execute("""
            SELECT *
            FROM users
            WHERE employee_id = ?
        """, (
            employee_id,
        )).fetchone()

        if user is None:

            connection.close()

            flash(
                "User not found in the directory.",
                "error"
            )

            return redirect(
                url_for("provision_user")
            )

        if user["status"] != "Active":

            connection.close()

            flash(
                "Access cannot be provisioned to a disabled user.",
                "error"
            )

            return redirect(
                url_for("provision_user")
            )

        group = connection.execute("""
            SELECT *
            FROM groups
            WHERE group_name = ?
        """, (
            group_name,
        )).fetchone()

        if group is None:

            connection.close()

            flash(
                "Directory group not found.",
                "error"
            )

            return redirect(
                url_for("provision_user")
            )

        existing_assignment = connection.execute("""
            SELECT *
            FROM user_groups
            WHERE employee_id = ?
            AND group_name = ?
        """, (
            employee_id,
            group_name
        )).fetchone()

        if existing_assignment:

            connection.close()

            flash(
                f"{user['employee_name']} already has "
                f"{group_name} access.",
                "warning"
            )

            return redirect(
                url_for(
                    "user_access",
                    employee_id=employee_id
                )
            )

        try:

            connection.execute("""
                INSERT INTO user_groups
                (
                    employee_id,
                    group_name,
                    assigned_at
                )
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (
                employee_id,
                group_name
            ))

            connection.commit()

        except sqlite3.IntegrityError:

            connection.rollback()
            connection.close()

            flash(
                "This access assignment already exists.",
                "warning"
            )

            return redirect(
                url_for(
                    "user_access",
                    employee_id=employee_id
                )
            )

        connection.close()

        flash(
            f"{group_name} successfully assigned to "
            f"{user['employee_name']}.",
            "success"
        )

        return redirect(
            url_for(
                "user_access",
                employee_id=employee_id
            )
        )

    users = connection.execute("""
        SELECT *
        FROM users
        WHERE status = 'Active'
        ORDER BY employee_name
    """).fetchall()

    groups = connection.execute("""
        SELECT *
        FROM groups
        ORDER BY group_name
    """).fetchall()

    active_user_count = connection.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE status = 'Active'
    """).fetchone()[0]

    group_count = connection.execute("""
        SELECT COUNT(*)
        FROM groups
    """).fetchone()[0]

    connection.close()

    return render_template(
        "provision_user.html",
        users=users,
        groups=groups,
        active_user_count=active_user_count,
        group_count=group_count
    )


# =========================================================
# USER ACCESS
# =========================================================

@app.route(
    "/user/<employee_id>/access"
)
def user_access(employee_id):

    connection = get_db_connection()

    user = connection.execute("""
        SELECT *
        FROM users
        WHERE employee_id = ?
    """, (
        employee_id,
    )).fetchone()

    if user is None:

        connection.close()

        return "User not found.", 404

    assignments = connection.execute("""
        SELECT
            id,
            employee_id,
            group_name,
            assigned_at
        FROM user_groups
        WHERE employee_id = ?
        ORDER BY group_name
    """, (
        employee_id,
    )).fetchall()

    access_count = connection.execute("""
        SELECT COUNT(*)
        FROM user_groups
        WHERE employee_id = ?
    """, (
        employee_id,
    )).fetchone()[0]

    connection.close()

    return render_template(
        "user_access.html",
        user=user,
        assignments=assignments,
        access_count=access_count
    )


# =========================================================
# REMOVE USER ACCESS
# =========================================================

@app.route(
    "/user/<employee_id>/remove-access",
    methods=["POST"]
)
def remove_access(employee_id):

    group_name = request.form.get(
        "group_name",
        ""
    ).strip()

    if not group_name:

        flash(
            "Group name is required.",
            "error"
        )

        return redirect(
            url_for(
                "user_access",
                employee_id=employee_id
            )
        )

    connection = get_db_connection()

    user = connection.execute("""
        SELECT *
        FROM users
        WHERE employee_id = ?
    """, (
        employee_id,
    )).fetchone()

    if user is None:

        connection.close()

        return "User not found.", 404

    assignment = connection.execute("""
        SELECT *
        FROM user_groups
        WHERE employee_id = ?
        AND group_name = ?
    """, (
        employee_id,
        group_name
    )).fetchone()

    if assignment is None:

        connection.close()

        flash(
            "Access assignment not found.",
            "error"
        )

        return redirect(
            url_for(
                "user_access",
                employee_id=employee_id
            )
        )

    connection.execute("""
        DELETE FROM user_groups
        WHERE employee_id = ?
        AND group_name = ?
    """, (
        employee_id,
        group_name
    ))

    connection.commit()
    connection.close()

    flash(
        f"{group_name} access removed from "
        f"{user['employee_name']}.",
        "success"
    )

    return redirect(
        url_for(
            "user_access",
            employee_id=employee_id
        )
    )


# =========================================================
# DIRECTORY USERS
# =========================================================

@app.route("/directory-users")
def directory_users():

    connection = get_db_connection()

    users = connection.execute("""
        SELECT
            u.id,
            u.employee_id,
            u.employee_name,
            u.status,
            COUNT(ug.id) AS access_count
        FROM users u
        LEFT JOIN user_groups ug
            ON u.employee_id = ug.employee_id
        GROUP BY
            u.id,
            u.employee_id,
            u.employee_name,
            u.status
        ORDER BY u.employee_name
    """).fetchall()

    connection.close()

    return render_template(
        "directory_users.html",
        users=users
    )


# =========================================================
# DIRECTORY GROUPS
# =========================================================

@app.route("/directory-groups")
def directory_groups():

    connection = get_db_connection()

    groups = connection.execute("""
        SELECT
            g.id,
            g.group_name,
            COUNT(ug.id) AS member_count
        FROM groups g
        LEFT JOIN user_groups ug
            ON g.group_name = ug.group_name
        GROUP BY
            g.id,
            g.group_name
        ORDER BY g.group_name
    """).fetchall()

    connection.close()

    return render_template(
        "directory_groups.html",
        groups=groups
    )


# =========================================================
# ACCESS REVIEW
# =========================================================

@app.route("/access-review")
def access_review():

    connection = get_db_connection()

    # -----------------------------------------------------
    # DIRECTORY STATISTICS
    # -----------------------------------------------------

    active_user_count = connection.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE status = 'Active'
    """).fetchone()[0]

    group_count = connection.execute("""
        SELECT COUNT(*)
        FROM groups
    """).fetchone()[0]

    assignment_count = connection.execute("""
        SELECT COUNT(*)
        FROM user_groups
    """).fetchone()[0]

    # -----------------------------------------------------
    # ACCESS REVIEW DATA
    #
    # LEFT JOIN ensures users with no access
    # are also displayed.
    # -----------------------------------------------------

    access_review_data = connection.execute("""
        SELECT
            u.employee_id,
            u.employee_name,
            u.status,
            ug.group_name,
            ug.assigned_at
        FROM users u
        LEFT JOIN user_groups ug
            ON u.employee_id = ug.employee_id
        ORDER BY
            u.employee_name,
            ug.group_name
    """).fetchall()

    # -----------------------------------------------------
    # ALL USERS
    # -----------------------------------------------------

    users = connection.execute("""
        SELECT
            employee_id,
            employee_name,
            status
        FROM users
        ORDER BY employee_name
    """).fetchall()

    connection.close()

    return render_template(
        "access_review.html",
        access_review_data=access_review_data,
        users=users,
        active_user_count=active_user_count,
        group_count=group_count,
        assignment_count=assignment_count
    )


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    init_db()

    print("")
    print("==========================================")
    print(" IAM Access Request Tracker")
    print("==========================================")
    print("")
    print("Dashboard:        http://127.0.0.1:5000/")
    print("Create Ticket:    http://127.0.0.1:5000/create-ticket")
    print("Provision User:   http://127.0.0.1:5000/provision-user")
    print("Access Review:    http://127.0.0.1:5000/access-review")
    print("Directory Users:  http://127.0.0.1:5000/directory-users")
    print("Directory Groups: http://127.0.0.1:5000/directory-groups")
    print("")
    print("==========================================")
    print("")

    app.run(
        debug=True
    )
