from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, send_from_directory, jsonify
)
from functools import wraps
import mysql.connector
from datetime import date
import os

# PDF generation
from pdf_generator import generate_assignment_pdf

app = Flask(__name__)
app.secret_key = "your_secret_key"  # 🔒 Change in production

# ─── MySQL Connection ─────────────────────────────────────────────────────────
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Sheel@3319",
    database="business_management"
)
cursor = db.cursor(dictionary=True)

# ─── Ensure static/pdfs folder ────────────────────────────────────────────────
PDF_DIR = os.path.join(app.root_path, "static", "pdfs")
os.makedirs(PDF_DIR, exist_ok=True)

# ─── Login Required Decorator ─────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ─── Home ─────────────────────────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    return render_template("index.html")

# ─── Orders ───────────────────────────────────────────────────────────────────
@app.route("/orders")
@login_required
def view_orders():
    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    return render_template("orders.html", orders=cursor.fetchall())

@app.route("/orders/add", methods=["GET", "POST"])
@login_required
def add_order():
    if request.method == "POST":
        data = (
            request.form["customer_name"], request.form["address"],
            request.form["contact_number"], request.form["order_date"],
            request.form["sofa_type"], request.form["quantity"],
            request.form["expected_delivery"], request.form["notes"]
        )
        cursor.execute("""
            INSERT INTO orders
              (customer_name, address, contact_number, order_date,
               sofa_type, quantity, expected_delivery, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, data)
        db.commit()
        flash("New order added!", "success")
        return redirect(url_for("view_orders"))
    return render_template("add_order.html")

@app.route("/orders/complete/<int:order_id>")
@login_required
def mark_order_completed(order_id):
    cursor.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
    order = cursor.fetchone()
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("view_orders"))

    cursor.execute("""
        INSERT INTO completed_orders (
            original_order_id, customer_name, address, contact_number,
            order_date, sofa_type, quantity, expected_delivery, notes,
            completion_date
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        order["id"], order["customer_name"], order["address"],
        order["contact_number"], order["order_date"], order["sofa_type"],
        order["quantity"], order["expected_delivery"], order["notes"],
        date.today()
    ))
    cursor.execute("UPDATE orders SET status='completed' WHERE id=%s", (order_id,))
    db.commit()
    flash("Order marked as completed ✔️", "success")
    return redirect(url_for("view_orders"))

@app.route("/completed-orders")
@login_required
def view_completed_orders():
    cursor.execute("SELECT * FROM completed_orders ORDER BY completion_date DESC")
    return render_template("completed_orders.html", orders=cursor.fetchall())

# ─── Workers ──────────────────────────────────────────────────────────────────
@app.route("/workers")
@login_required
def view_workers():
    cursor.execute("SELECT * FROM workers ORDER BY id")
    return render_template("workers.html", workers=cursor.fetchall())

# ─── Assign Work ──────────────────────────────────────────────────────────────
@app.route("/assign", methods=["GET", "POST"])
@login_required
def assign_worker():
    if request.method == "POST":
        worker_id        = request.form["worker_id"]
        order_id         = request.form["order_id"]
        fabric_id        = request.form["fabric_id"]
        sofa_model_id    = request.form["sofa_model_id"]
        sofa_design_id   = request.form.get("sofa_design_id") or None
        expected_comp    = request.form["completion_date"]
        instructions     = request.form.get("instructions") or None
        assign_date      = date.today()

        cursor.execute("""
            INSERT INTO work_assignments (
                worker_id, order_id, assign_date,
                fabric_id, sofa_design_id, sofa_model_id,
                expected_completion, instructions
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            worker_id, order_id, assign_date,
            fabric_id, sofa_design_id, sofa_model_id,
            expected_comp, instructions
        ))
        db.commit()
        assignment_id = cursor.lastrowid

        cursor.execute("SELECT * FROM workers WHERE id=%s", (worker_id,))
        worker = cursor.fetchone()
        cursor.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
        order  = cursor.fetchone()

        pdf_file = generate_assignment_pdf(
            assignment_id, worker, order, assign_date, PDF_DIR
        )

        flash(
            "Work assigned! "
            f"<a href='{url_for('download_pdf', filename=pdf_file)}' target='_blank'>"
            "Download PDF</a>",
            "success"
        )
        return redirect(url_for("assign_worker"))

    # Dropdowns data
    cursor.execute("SELECT id, name FROM workers WHERE is_active=1")
    workers = cursor.fetchall()

    cursor.execute("SELECT id, customer_name FROM orders WHERE status='in_progress'")
    orders = cursor.fetchall()

    cursor.execute("SELECT id, fabric_type FROM fabrics")
    fabrics = cursor.fetchall()

    cursor.execute("SELECT id, model_name FROM sofa_models")
    sofa_models = cursor.fetchall()

    return render_template("assign_form.html",
        workers=workers, orders=orders,
        fabrics=fabrics, sofa_models=sofa_models
    )

# ─── Return Designs JSON for Selected Model ───────────────────────────────────
@app.route("/get_designs/<int:model_id>")
@login_required
def get_designs_for_model(model_id):
    cursor.execute("""
        SELECT sd.id, sm.model_name, sd.photo_path
        FROM sofa_designs sd
        JOIN sofa_models sm ON sm.id = sd.sofa_model_id
        WHERE sd.sofa_model_id = %s
    """, (model_id,))
    rows = cursor.fetchall()

    designs = [
        {
            "id": r["id"],
            "model_name": r["model_name"],
            "photo_url": url_for("static", filename=r["photo_path"]),
        }
        for r in rows
    ]
    return jsonify(designs)

# ─── Assignments ──────────────────────────────────────────────────────────────
@app.route("/assignments")
@login_required
def view_assignments():
    cursor.execute("""
        SELECT wa.id, w.name AS worker_name, o.customer_name,
               wa.assign_date, wa.work_date, wa.work_progress,
               wa.sofas_completed, wa.total_earning
        FROM work_assignments wa
        JOIN workers w ON wa.worker_id = w.id
        JOIN orders  o ON wa.order_id  = o.id
        ORDER BY wa.assign_date DESC
    """)
    return render_template("assignments.html", assignments=cursor.fetchall())

# ─── Serve PDFs ───────────────────────────────────────────────────────────────
@app.route("/pdf/<filename>")
@login_required
def download_pdf(filename):
    return send_from_directory(PDF_DIR, filename, as_attachment=True)

# ─── Admin Login & Logout ─────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        uname = request.form["username"]
        pwd   = request.form["password"]
        cursor.execute(
            "SELECT * FROM admin_login WHERE username=%s AND password=%s",
            (uname, pwd)
        )
        if cursor.fetchone():
            session["admin_logged_in"] = True
            return redirect(url_for("index"))
        flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("login"))

# ─── Run Server ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
