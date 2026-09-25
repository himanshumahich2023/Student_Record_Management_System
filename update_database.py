import sqlite3

conn = sqlite3.connect("students.db")
cursor = conn.cursor()

columns = [
    ("father_name", "TEXT"),
    ("city", "TEXT"),
    ("course_fee", "REAL DEFAULT 0"),
    ("last_fee_date", "TEXT"),
    ("fee_paid_date", "TEXT"),
    ("late_days", "INTEGER DEFAULT 0"),
    ("fine_per_day", "REAL DEFAULT 0"),
    ("total_fine", "REAL DEFAULT 0"),
    ("total_payable", "REAL DEFAULT 0"),
    ("fee_paid", "REAL DEFAULT 0"),
    ("remaining_fee", "REAL DEFAULT 0")
]

for column, datatype in columns:
    try:
        cursor.execute(
            f"ALTER TABLE students ADD COLUMN {column} {datatype}"
        )
        print(f"{column} added")
    except sqlite3.OperationalError:
        print(f"{column} already exists")

conn.commit()
conn.close()

print("Database update complete.")