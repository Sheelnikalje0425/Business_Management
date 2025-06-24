from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
import mysql.connector
from datetime import date

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # REQUIRED for session handling

# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Sheel@3319",  # your MySQL password
    database="business_management"
)
cursor = db.cursor(dictionary=True)

# 🔐 Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# 🏠 Home Dashboard
@app.route('/')
@login_required
def index():
    return render_template("index.html")


# 📦 View Orders
@app.route('/orders')
@login_required
def view_orders():
    cursor.execute("SELECT * FROM orders")
    orders = cursor.fetchall()
    return render_template("orders.html", orders=orders)


# 👷 View Workers
@app.route('/workers')
@login_required
def view_workers():
    cursor.execute("SELECT * FROM workers")
    workers = cursor.fetchall()
    return render_template("workers.html", workers=workers)


# 🛠️ Assign Work
@app.route('/assign', methods=['GET', 'POST'])
@login_required
def assign_worker():
    if request.method == 'POST':
        worker_id = request.form['worker_id']
        order_id = request.form['order_id']
        assign_date = date.today()

        cursor.execute("""
            INSERT INTO work_assignments (worker_id, order_id, assign_date)
            VALUES (%s, %s, %s)
        """, (worker_id, order_id, assign_date))
        db.commit()
        flash("Work assigned successfully!", "success")
        return redirect(url_for('assign_worker'))

    cursor.execute("SELECT id, name FROM workers WHERE is_active = 1")
    workers = cursor.fetchall()

    cursor.execute("SELECT id, customer_name FROM orders WHERE status = 'in_progress'")
    orders = cursor.fetchall()

    return render_template("assign_form.html", workers=workers, orders=orders)


# 📋 View Assignments
@app.route('/assignments')
@login_required
def view_assignments():
    query = """
        SELECT wa.id, w.name AS worker_name, o.customer_name, wa.assign_date, 
               wa.work_date, wa.work_progress, wa.sofas_completed, wa.total_earning
        FROM work_assignments wa
        JOIN workers w ON wa.worker_id = w.id
        JOIN orders o ON wa.order_id = o.id
        ORDER BY wa.assign_date DESC
    """
    cursor.execute(query)
    assignments = cursor.fetchall()
    return render_template("assignments.html", assignments=assignments)


# 🔑 Admin Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']

        cursor.execute("SELECT * FROM admin_login WHERE username=%s AND password=%s", (uname, pwd))
        admin = cursor.fetchone()

        if admin:
            session['admin_logged_in'] = True
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials", "danger")

    return render_template("login.html")


# 🚪 Logout
@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
