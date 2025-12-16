import sqlite3
from typing import List

from models.student import StudentCreate
from models.grade import GradeCreate



# Database Connection

def get_db_connection():
    conn = sqlite3.connect('classroom.db')
    conn.row_factory = sqlite3.Row
    return conn


def create_database():
    conn = sqlite3.connect('classroom.db')
    cursor = conn.cursor()

    # Students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            age INTEGER
        )
    ''')

    # Grades table (only student reference, no feedback)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            score REAL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')

    conn.commit()
    return conn, cursor



# Insert Functions

def insert_student(student: StudentCreate, cursor) -> int:
    cursor.execute('''
        INSERT INTO students (name, email, age)
        VALUES (?, ?, ?)
    ''', (student.name, student.email, student.age))

    return cursor.lastrowid


def insert_grade(grade_obj: GradeCreate, cursor) -> int:
    cursor.execute('''
        INSERT INTO grades (student_id, score)
        VALUES (?, ?)
    ''', (grade_obj.student_id, grade_obj.score))

    return cursor.lastrowid



def insert_data(students: List[StudentCreate], grades: List[GradeCreate]):
    conn, cursor = create_database()

    # Insert students
    student_db_ids = []
    for student in students:
        sid = insert_student(student, cursor)
        student_db_ids.append(sid)

    # Insert grades
    # grades provided may reference parsed student IDs (1-based index into the `students` list).
    # Map parsed id -> actual DB id using student_db_ids.
    for grade in grades:
        mapped_student_id = grade.student_id
        try:
            if isinstance(grade.student_id, int) and 1 <= grade.student_id <= len(student_db_ids):
                mapped_student_id = student_db_ids[grade.student_id - 1]
        except Exception:
            mapped_student_id = grade.student_id

        cursor.execute('''
            INSERT INTO grades (student_id, score)
            VALUES (?, ?)
        ''', (mapped_student_id, grade.score))

    conn.commit()
    conn.close()

    return student_db_ids


if __name__ == "__main__":
    create_database()