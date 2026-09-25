from flask import Flask, render_template, request, redirect
import psycopg
from psycopg.rows import dict_row
from datetime import datetime
import os

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db():
    conn = psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )
    return conn


def reset_sequence(conn):
    conn.execute("""
        SELECT setval(
            pg_get_serial_sequence('students', 'id'),
            COALESCE((SELECT MAX(id) FROM students), 1),
            (SELECT COUNT(*) > 0 FROM students)
        )
    """)


def normalize_ids(conn):
    rows = conn.execute("""
        SELECT id
        FROM students
        ORDER BY id
    """).fetchall()

    if not rows:
        reset_sequence(conn)
        return

    for row in rows:
        old_id = row["id"]
        temp_id = -1000000 - old_id

        conn.execute("""
            UPDATE students
            SET id = %s
            WHERE id = %s
        """, (temp_id, old_id))

    for new_id, row in enumerate(rows, start=1):
        old_id = row["id"]
        temp_id = -1000000 - old_id

        conn.execute("""
            UPDATE students
            SET id = %s
            WHERE id = %s
        """, (new_id, temp_id))

    reset_sequence(conn)


def calculate_fee(course_fee, last_fee_date, fee_paid_date, fee_paid):
    fine_per_day = 50
    late_days = 0
    total_fine = 0

    if last_fee_date and fee_paid_date:
        last_date = datetime.strptime(last_fee_date, "%Y-%m-%d")
        paid_date = datetime.strptime(fee_paid_date, "%Y-%m-%d")

        late_days = max((paid_date - last_date).days, 0)
        total_fine = late_days * fine_per_day

    total_payable = course_fee + total_fine
    remaining_fee = max(total_payable - fee_paid, 0)

    return (
        late_days,
        fine_per_day,
        total_fine,
        total_payable,
        remaining_fee
    )


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY,
            name TEXT,
            father_name TEXT,
            roll_no TEXT,
            course TEXT,
            email TEXT,
            phone TEXT,
            city TEXT,
            year TEXT,
            semester TEXT,
            course_fee REAL DEFAULT 0,
            last_fee_date TEXT,
            fee_paid_date TEXT,
            late_days INTEGER DEFAULT 0,
            fine_per_day REAL DEFAULT 50,
            total_fine REAL DEFAULT 0,
            total_payable REAL DEFAULT 0,
            fee_paid REAL DEFAULT 0,
            remaining_fee REAL DEFAULT 0
        )
    """)

    conn.execute("""
        ALTER TABLE students
        ADD COLUMN IF NOT EXISTS year TEXT
    """)

    conn.execute("""
        ALTER TABLE students
        ADD COLUMN IF NOT EXISTS semester TEXT
    """)

    conn.execute("""
        ALTER TABLE students
        ADD COLUMN IF NOT EXISTS course_fee REAL DEFAULT 0
    """)

    conn.execute("""
        ALTER TABLE students
        ADD COLUMN IF NOT EXISTS last_fee_date TEXT
    """)

    conn.execute("""
        ALTER TABLE students
        ADD COLUMN IF NOT EXISTS fee_paid_date TEXT
    """)

    conn.execute("""
        ALTER TABLE students
        ADD COLUMN IF NOT EXISTS late_days INTEGER DEFAULT 0
    """)

    conn.execute("""
        ALTER TABLE students
        ADD COLUMN IF NOT EXISTS fine_per_day REAL DEFAULT 50
    """)

    conn.execute("""
        ALTER TABLE students
        ADD COLUMN IF NOT EXISTS total_fine REAL DEFAULT 0
    """)

    conn.execute("""
        ALTER TABLE students
        ADD COLUMN IF NOT EXISTS total_payable REAL DEFAULT 0
    """)

    conn.execute("""
        ALTER TABLE students
        ADD COLUMN IF NOT EXISTS fee_paid REAL DEFAULT 0
    """)

    conn.execute("""
        ALTER TABLE students
        ADD COLUMN IF NOT EXISTS remaining_fee REAL DEFAULT 0
    """)

    normalize_ids(conn)

    conn.commit()
    conn.close()


init_db()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/add", methods=["GET", "POST"])
def add_student():

    if request.method == "POST":

        conn = get_db()

        normalize_ids(conn)

        result = conn.execute("""
            SELECT COALESCE(MAX(id), 0) + 1 AS next_id
            FROM students
        """).fetchone()

        next_id = result["next_id"]

        name = request.form["name"]
        father_name = request.form["father_name"]
        roll_no = request.form["roll_no"]
        course = request.form["course"]
        year = request.form["year"]
        semester = request.form["semester"]
        email = request.form["email"]
        phone = request.form["phone"]
        city = request.form["city"]

        course_fee = float(
            request.form.get("course_fee") or 0
        )

        last_fee_date = request.form.get(
            "last_fee_date"
        ) or ""

        fee_paid_date = request.form.get(
            "fee_paid_date"
        ) or ""

        fee_paid = float(
            request.form.get("fee_paid") or 0
        )

        (
            late_days,
            fine_per_day,
            total_fine,
            total_payable,
            remaining_fee
        ) = calculate_fee(
            course_fee,
            last_fee_date,
            fee_paid_date,
            fee_paid
        )

        conn.execute("""
            INSERT INTO students (
                id,
                name,
                father_name,
                roll_no,
                course,
                email,
                phone,
                city,
                year,
                semester,
                course_fee,
                last_fee_date,
                fee_paid_date,
                late_days,
                fine_per_day,
                total_fine,
                total_payable,
                fee_paid,
                remaining_fee
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            next_id,
            name,
            father_name,
            roll_no,
            course,
            email,
            phone,
            city,
            year,
            semester,
            course_fee,
            last_fee_date,
            fee_paid_date,
            late_days,
            fine_per_day,
            total_fine,
            total_payable,
            fee_paid,
            remaining_fee
        ))

        reset_sequence(conn)

        conn.commit()
        conn.close()

        return redirect("/students")

    return render_template("add_student.html")


@app.route("/students")
def students():

    search = request.args.get("search", "").strip()

    conn = get_db()

    if search:

        search_pattern = f"%{search}%"

        students = conn.execute("""
            SELECT *
            FROM students
            WHERE
                CAST(id AS TEXT) ILIKE %s
                OR name ILIKE %s
                OR father_name ILIKE %s
                OR roll_no ILIKE %s
                OR course ILIKE %s
                OR email ILIKE %s
                OR phone ILIKE %s
                OR city ILIKE %s
                OR year ILIKE %s
                OR semester ILIKE %s
            ORDER BY id
        """, (
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern
        )).fetchall()

    else:

        students = conn.execute("""
            SELECT *
            FROM students
            ORDER BY id
        """).fetchall()

    conn.close()

    return render_template(
        "students.html",
        students=students,
        search=search
    )


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_student(id):

    conn = get_db()

    if request.method == "POST":

        new_id = int(request.form["id"])

        count_result = conn.execute("""
            SELECT COUNT(*) AS total
            FROM students
        """).fetchone()

        total_students = count_result["total"]

        if new_id < 1 or new_id > total_students:

            conn.close()

            return """
            <h2>Invalid ID</h2>
            <p>ID must be between 1 and the total number of students.</p>
            <a href="/students">Back to Students</a>
            """

        rows = conn.execute("""
            SELECT id
            FROM students
            ORDER BY id
        """).fetchall()

        ordered_ids = [row["id"] for row in rows]

        ordered_ids.remove(id)

        ordered_ids.insert(new_id - 1, id)

        for old_id in ordered_ids:

            temp_id = -2000000 - old_id

            conn.execute("""
                UPDATE students
                SET id = %s
                WHERE id = %s
            """, (
                temp_id,
                old_id
            ))

        for position, old_id in enumerate(
            ordered_ids,
            start=1
        ):

            temp_id = -2000000 - old_id

            conn.execute("""
                UPDATE students
                SET id = %s
                WHERE id = %s
            """, (
                position,
                temp_id
            ))

        name = request.form["name"]
        father_name = request.form["father_name"]
        roll_no = request.form["roll_no"]
        course = request.form["course"]
        year = request.form["year"]
        semester = request.form["semester"]
        email = request.form["email"]
        phone = request.form["phone"]
        city = request.form["city"]

        course_fee = float(
            request.form.get("course_fee") or 0
        )

        last_fee_date = request.form.get(
            "last_fee_date"
        ) or ""

        fee_paid_date = request.form.get(
            "fee_paid_date"
        ) or ""

        fee_paid = float(
            request.form.get("fee_paid") or 0
        )

        (
            late_days,
            fine_per_day,
            total_fine,
            total_payable,
            remaining_fee
        ) = calculate_fee(
            course_fee,
            last_fee_date,
            fee_paid_date,
            fee_paid
        )

        conn.execute("""
            UPDATE students
            SET
                name = %s,
                father_name = %s,
                roll_no = %s,
                course = %s,
                year = %s,
                semester = %s,
                email = %s,
                phone = %s,
                city = %s,
                course_fee = %s,
                last_fee_date = %s,
                fee_paid_date = %s,
                late_days = %s,
                fine_per_day = %s,
                total_fine = %s,
                total_payable = %s,
                fee_paid = %s,
                remaining_fee = %s
            WHERE id = %s
        """, (
            name,
            father_name,
            roll_no,
            course,
            year,
            semester,
            email,
            phone,
            city,
            course_fee,
            last_fee_date,
            fee_paid_date,
            late_days,
            fine_per_day,
            total_fine,
            total_payable,
            fee_paid,
            remaining_fee,
            new_id
        ))

        reset_sequence(conn)

        conn.commit()
        conn.close()

        return redirect("/students")

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE id = %s
    """, (id,)).fetchone()

    conn.close()

    return render_template(
        "edit_student.html",
        student=student
    )


@app.route("/delete/<int:id>")
def delete_student(id):

    conn = get_db()

    conn.execute("""
        DELETE FROM students
        WHERE id = %s
    """, (id,))

    normalize_ids(conn)

    conn.commit()
    conn.close()

    return redirect("/students")


if __name__ == "__main__":
    app.run(debug=True)