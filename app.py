from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, send_from_directory
)
from pdf_generator import generate_assignment_pdf

from functools import wraps
import mysql.connector
from datetime import date
import os

# ─── PDF helper (ReportLab) ────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = 'your_secret_key'   # change in production!

# ─── Database connection ───────────────────────────────────────────────────────
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Sheel@3319",
    database="business_management"
)
cursor = db.cursor(dictionary=True)

# ─── Ensure /static/pdfs/ exists no matter where we run from ───────────────────
PDF_DIR = os.path.join(app.root_path, 'static', 'pdfs')
os.makedirs(PDF_DIR, exist_ok=True)

# ─── Login-required decorator ──────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function



# ─── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
@login_required
def index():
    return render_template("index.html")


@app.route('/orders')
@login_required
def view_orders():
    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = cursor.fetchall()
    return render_template("orders.html", orders=orders)


@app.route('/orders/add', methods=['GET', 'POST'])
@login_required
def add_order():
    if request.method == 'POST':
        data = (
            request.form['customer_name'], request.form['address'],
            request.form['contact_number'], request.form['order_date'],
            request.form['sofa_type'], request.form['quantity'],
            request.form['expected_delivery'], request.form['notes']
        )
        cursor.execute("""
            INSERT INTO orders
              (customer_name, address, contact_number, order_date,
               sofa_type, quantity, expected_delivery, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, data)
        db.commit()
        flash("New order added!", "success")
        return redirect(url_for('view_orders'))
    return render_template("add_order.html")


@app.route('/workers')
@login_required
def view_workers():
    cursor.execute("SELECT * FROM workers ORDER BY id")
    workers = cursor.fetchall()
    return render_template("workers.html", workers=workers)


@app.route('/assign', methods=['GET', 'POST'])
@login_required
def assign_worker():
    if request.method == 'POST':
        worker_id   = request.form['worker_id']
        order_id    = request.form['order_id']
        assign_date = date.today()

        # Insert the assignment
        cursor.execute("""
            INSERT INTO work_assignments (worker_id, order_id, assign_date)
            VALUES (%s, %s, %s)
        """, (worker_id, order_id, assign_date))
        db.commit()
        assignment_id = cursor.lastrowid

        # Fetch details for PDF
        cursor.execute("SELECT * FROM workers WHERE id=%s", (worker_id,))
        worker = cursor.fetchone()
        cursor.execute("SELECT * FROM orders WHERE id=%s",  (order_id,))
        order  = cursor.fetchone()

        pdf_file = generate_assignment_pdf(assignment_id, worker, order, assign_date, PDF_DIR)

        flash(
            "Work assigned! "
            f"<a href='{url_for('download_pdf', filename=pdf_file)}' target='_blank'>"
            "Download PDF</a>",
            "success"
        )
        return redirect(url_for('assign_worker'))

    cursor.execute("SELECT id, name, contact_number FROM workers WHERE is_active=1")
    workers = cursor.fetchall()
    cursor.execute("SELECT id, customer_name FROM orders WHERE status='in_progress'")
    orders  = cursor.fetchall()
    return render_template("assign_form.html", workers=workers, orders=orders)


@app.route('/assignments')
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
    assignments = cursor.fetchall()
    return render_template("assignments.html", assignments=assignments)


@app.route('/pdf/<filename>')
@login_required
def download_pdf(filename):
    return send_from_directory(PDF_DIR, filename, as_attachment=True)


# ─── Admin login & logout ──────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd   = request.form['password']
        cursor.execute(
            "SELECT * FROM admin_login WHERE username=%s AND password=%s",
            (uname, pwd)
        )
        if cursor.fetchone():
            session['admin_logged_in'] = True
            return redirect(url_for('index'))
        flash("Invalid credentials", "danger")
    return render_template("login.html")


@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))


# ─── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)
