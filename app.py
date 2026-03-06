from flask import Flask, render_template, request, redirect, session, flash
import sqlite3, os
from datetime import datetime, date
import pandas as pd

app = Flask(__name__)
app.secret_key = "attendance_secret_key"

# ---------------- PATH ----------------
BASE_DIR = os.path.dirname(__file__)
DB_FOLDER = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_FOLDER, "attendance.db")
os.makedirs(DB_FOLDER, exist_ok=True)


# ---------------- DATABASE INIT ----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create tables only if they don't exist

    c.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        student_id TEXT UNIQUE,
        email TEXT,
        role TEXT,
        department TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        date TEXT,
        day TEXT,
        status TEXT,
        in_time TEXT,
        exit_time TEXT,
        UNIQUE(student_id,date)
    )
    """)

    conn.commit()
    conn.close()

init_db()


# ---------------- DB CONNECTION ----------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- HOME ----------------
@app.route("/")
def home():
    return redirect("/login")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():

    conn = get_db()

    # check if students exist in database
    student_count = conn.execute(
        "SELECT COUNT(*) FROM students"
    ).fetchone()[0]

    conn.close()

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # check admin credentials first
        if username == "admin" and password == "admin123":

            # only block login if database empty
            if student_count == 0:
                flash("Please upload student data first!", "error")
                return redirect("/login")

            session["admin"] = True
            return redirect("/dashboard")

        flash("Invalid Credentials!", "error")

    return render_template(
        "login.html",
        date=date,
        current_year=date.today().year
    )


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():

    # remove only admin session
    session.pop("admin", None)

    flash("Logged out successfully!", "success")

    return redirect("/login")

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():

    if not session.get("admin"):
        return redirect("/login")

    conn = get_db()
    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()

    return render_template("dashboard.html", students=students)


# ---------------- UPLOAD STUDENTS ----------------
@app.route("/upload-students", methods=["POST"])
def upload_students():

    file = request.files.get("file")

    if not file or file.filename == "":
        flash("No file selected!", "error")
        return redirect("/login")

    try:

        filename = file.filename.lower()

        if filename.endswith(".csv"):
            df = pd.read_csv(file)

        elif filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(file)

        else:
            flash("Only CSV or Excel allowed!", "error")
            return redirect("/login")

        df.columns = df.columns.str.strip().str.lower()

        if "name" not in df.columns or "studentid" not in df.columns:
            flash("File must contain name & studentid columns!", "error")
            return redirect("/login")

        df = df.fillna("").astype(str)

        conn = get_db()

        for _, row in df.iterrows():

            conn.execute("""
            INSERT OR IGNORE INTO students
            (name,student_id,email,role,department)
            VALUES(?,?,?,?,?)
            """, (
                row.get("name"),
                row.get("studentid"),
                row.get("email"),
                row.get("role"),
                row.get("department")
            ))

        conn.commit()
        conn.close()

        session["upload_done"] = True
        flash("Students uploaded successfully!", "success")

    except Exception as e:
        flash(str(e), "error")

    return redirect("/login")


# ---------------- ADMIN ATTENDANCE PAGE ----------------
@app.route("/attendance", methods=["GET", "POST"])
def student_attendance():

    conn = get_db()
    students = conn.execute("SELECT * FROM students").fetchall()

    message = None
    error = None





    if request.method == "POST":

        try:

            now = datetime.now()

            conn.execute("""
            INSERT INTO attendance
            (student_id,date,day,status,in_time)
            VALUES(?,?,?,?,?)
            """, (
                request.form["student_id"],
                now.strftime("%Y-%m-%d"),
                now.strftime("%A"),
                request.form["status"],
                now.strftime("%H:%M:%S")
            ))

            conn.commit()

            message = "Attendance marked!"

        except sqlite3.IntegrityError:

            error = "Attendance already exists today"

    conn.close()

    return render_template(
        "student_attendance.html",
        students=students,
        message=message,
        error=error
    )

@app.route("/admin-mark-exit/<int:student_id>", methods=["POST"])
def admin_mark_exit(student_id):
    # Check if admin is logged in
    if not session.get("admin"):
        return redirect("/login")

    conn = get_db()
    
    now = datetime.now()
    time = now.strftime("%H:%M:%S")
    date_today = now.strftime("%Y-%m-%d")
    
    # Update exit_time only if student was present
    conn.execute("""
        UPDATE attendance
        SET exit_time=?
        WHERE student_id=? AND date=? AND exit_time IS NULL
    """, (time, student_id, date_today))
    
    conn.commit()
    conn.close()

    flash("Exit time marked!", "success")
    return redirect("/dashboard")  # Back to dashboard after marking exit time


# ---------------- ADMIN VIEW ATTENDANCE ----------------
@app.route("/admin-attendance")
def admin_attendance():

    if not session.get("admin"):
        return redirect("/login")

    conn = get_db()

    records = conn.execute("""
    SELECT students.name,students.student_id,
           attendance.date,attendance.day,
           attendance.status,attendance.in_time,attendance.exit_time
    FROM attendance
    JOIN students ON students.student_id = attendance.student_id
    ORDER BY attendance.date DESC
    """).fetchall()

    conn.close()

    return render_template("admin_attendance.html", records=records)


# ---------------- STUDENT LOGIN ----------------
@app.route("/student-login", methods=["POST"])
def student_login():

    student_id = request.form["student_id"]
    password = request.form["password"]

    conn = get_db()

    student = conn.execute("""
    SELECT * FROM students
    WHERE student_id=? AND email=?
    """, (student_id, password)).fetchone()

    conn.close()

    if student:
        session["student_id"] = student_id
        return redirect("/student-dashboard")

    flash("Invalid Student Login", "error")
    return redirect("/login")


# ---------------- STUDENT DASHBOARD ----------------


@app.route("/student-dashboard")
def student_dashboard():
    if "student_id" not in session:
        return redirect("/login")

    student_id = session["student_id"]

    conn = get_db()

    student = conn.execute("""
        SELECT * FROM students WHERE student_id=?
    """, (student_id,)).fetchone()

    attendance_records = conn.execute("""
        SELECT * FROM attendance
        WHERE student_id=?
        ORDER BY date DESC
    """, (student_id,)).fetchall()

    # calculate total time
    attendance = []
    for row in attendance_records:
        in_time = row["in_time"]
        exit_time = row["exit_time"]

        total_time = None
        if in_time and exit_time:
            fmt = "%H:%M:%S"
            tdelta = datetime.strptime(exit_time, fmt) - datetime.strptime(in_time, fmt)
            total_time = str(tdelta)  # format as HH:MM:SS
        attendance.append({
            **row,
            "total_time": total_time
        })

    conn.close()

    return render_template(
        "student_dashboard.html",
        student=student,
        attendance=attendance
    )

# ---------------- MARK IN ----------------
@app.route("/mark-in", methods=["POST"])
def mark_in():

    if "student_id" not in session:
        return redirect("/login")

    student_id = session["student_id"]

    conn = get_db()

    now = datetime.now()

    date_today = now.strftime("%Y-%m-%d")

    check = conn.execute("""
    SELECT * FROM attendance
    WHERE student_id=? AND date=?
    """, (student_id, date_today)).fetchone()

    if not check:

        conn.execute("""
        INSERT INTO attendance
        (student_id,date,day,status,in_time)
        VALUES(?,?,?,?,?)
        """, (
            student_id,
            date_today,
            now.strftime("%A"),
            "Present",
            now.strftime("%H:%M:%S")
        ))

        conn.commit()

    conn.close()

    return redirect("/student-dashboard")


# ---------------- MARK OUT ----------------
@app.route("/mark-out", methods=["POST"])
def mark_out():

    if "student_id" not in session:
        return redirect("/login")

    student_id = session["student_id"]

    conn = get_db()

    now = datetime.now()

    conn.execute("""
    UPDATE attendance
    SET exit_time=?
    WHERE student_id=? AND date=?
    """, (
        now.strftime("%H:%M:%S"),
        student_id,
        now.strftime("%Y-%m-%d")
    ))

    conn.commit()
    conn.close()

    return redirect("/student-dashboard")


# ---------------- MARK LEAVE ----------------
@app.route("/mark-leave", methods=["POST"])
def mark_leave():

    if "student_id" not in session:
        return redirect("/login")

    student_id = session["student_id"]

    conn = get_db()

    now = datetime.now()

    conn.execute("""
    INSERT OR IGNORE INTO attendance
    (student_id,date,day,status)
    VALUES(?,?,?,?)
    """, (
        student_id,
        now.strftime("%Y-%m-%d"),
        now.strftime("%A"),
        "Leave"
    ))

    conn.commit()
    conn.close()

    return redirect("/student-dashboard")

@app.route("/student/<int:id>")
def student_profile(id):
    if not session.get("admin"):
        return redirect("/login")

    conn = get_db()

    # get student
    student = conn.execute(
        "SELECT * FROM students WHERE id=?",
        (id,)
    ).fetchone()

    # get attendance records
    attendance_records = conn.execute("""
        SELECT date, day, status, in_time, exit_time
        FROM attendance
        WHERE student_id=?
        ORDER BY date DESC
    """, (student["student_id"],)).fetchall()

    # calculate total time for each record
    attendance = []
    from datetime import datetime

    for row in attendance_records:
        in_time = row["in_time"]
        exit_time = row["exit_time"]
        total_time = None

        if in_time and exit_time:
            fmt = "%H:%M:%S"
            tdelta = datetime.strptime(exit_time, fmt) - datetime.strptime(in_time, fmt)
            total_time = str(tdelta)  # HH:MM:SS

        # Explicitly convert row to dict
        attendance.append({
            "date": row["date"],
            "day": row["day"],
            "status": row["status"],
            "in_time": row["in_time"],
            "exit_time": row["exit_time"],
            "total_time": total_time
        })

    # stats
    present = conn.execute("""
        SELECT COUNT(*) FROM attendance
        WHERE student_id=? AND status='Present'
    """,(student["student_id"],)).fetchone()[0]

    absent = conn.execute("""
        SELECT COUNT(*) FROM attendance
        WHERE student_id=? AND status='Absent'
    """,(student["student_id"],)).fetchone()[0]

    leave = conn.execute("""
        SELECT COUNT(*) FROM attendance
        WHERE student_id=? AND status='Leave'
    """,(student["student_id"],)).fetchone()[0]

    total = present + absent + leave
    percentage = round((present/total)*100,2) if total > 0 else 0

    conn.close()

    return render_template(
        "student_profile.html",
        student=student,
        attendance=attendance,
        present=present,
        absent=absent,
        leave=leave,
        percentage=percentage
    )
# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)