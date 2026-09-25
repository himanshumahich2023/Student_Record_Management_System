import sqlite3
import psycopg
import os


# =========================
# DATABASE CONNECTION
# =========================

DATABASE_URL = os.environ.get("DATABASE_URL")

sqlite_conn = sqlite3.connect("students.db")
sqlite_conn.row_factory = sqlite3.Row

postgres_conn = psycopg.connect(DATABASE_URL)


# =========================
# READ DATA FROM SQLITE
# =========================

sqlite_students = sqlite_conn.execute(
    "SELECT * FROM students ORDER BY id"
).fetchall()

print("Students found in SQLite:", len(sqlite_students))


# =========================
# INSERT DATA INTO POSTGRESQL
# =========================

for student in sqlite_students:

    postgres_conn.execute("""
        INSERT INTO students (
            id,
            name,
            father_name,
            roll_no,
            course,
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
            remaining_fee
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (id) DO NOTHING
    """, (
        student["id"],
        student["name"],
        student["father_name"],
        student["roll_no"],
        student["course"],
        student["email"],
        student["phone"],
        student["city"],
        student["course_fee"],
        student["last_fee_date"],
        student["fee_paid_date"],
        student["late_days"],
        student["fine_per_day"],
        student["total_fine"],
        student["total_payable"],
        student["fee_paid"],
        student["remaining_fee"]
    ))


# =========================
# FIX NEXT ID
# =========================

postgres_conn.execute("""
    SELECT setval(
        pg_get_serial_sequence('students', 'id'),
        COALESCE((SELECT MAX(id) FROM students), 1),
        true
    )
""")


postgres_conn.commit()

sqlite_conn.close()
postgres_conn.close()

print("Migration completed successfully!")