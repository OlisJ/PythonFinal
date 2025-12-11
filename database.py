import sqlite3
from typing import List

from models import (
    StudentCreate,
    ClassCreate,
    GradeCreate
)



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

    # Classes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            teacher_name TEXT,
            schedule TEXT
        )
    ''')

    # Student-to-Class many-to-many table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS class_students (
            class_id INTEGER,
            student_id INTEGER,
            PRIMARY KEY (class_id, student_id),
            FOREIGN KEY (class_id) REFERENCES classes(id),
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')

    # Grades table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            class_id INTEGER,
            score REAL,
            feedback TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (class_id) REFERENCES classes(id)
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


def insert_class(class_obj: ClassCreate, cursor) -> int:
    cursor.execute('''
        INSERT INTO classes (title, teacher_name, schedule)
        VALUES (?, ?, ?)
    ''', (class_obj.title, class_obj.teacher_name, class_obj.schedule))

    class_id = cursor.lastrowid

    # Insert students enrolled in this class (if any)
    for student_id in class_obj.students:
        cursor.execute('''
            INSERT OR IGNORE INTO class_students (class_id, student_id)
            VALUES (?, ?)
        ''', (class_id, student_id))

    return class_id


def insert_grade(grade_obj: GradeCreate, cursor) -> int:
    cursor.execute('''
        INSERT INTO grades (student_id, class_id, score, feedback)
        VALUES (?, ?, ?, ?)
    ''', (grade_obj.student_id, grade_obj.class_id, grade_obj.score, grade_obj.feedback))

    return cursor.lastrowid



def insert_data(students: List[StudentCreate], classes: List[ClassCreate], grades: List[GradeCreate]):
    conn, cursor = create_database()

    # Insert students
    student_ids = []
    for student in students:
        sid = insert_student(student, cursor)
        student_ids.append(sid)

    # Insert classes
    class_ids = []
    for class_obj in classes:
        cid = insert_class(class_obj, cursor)
        class_ids.append(cid)

    # Insert grades
    for grade in grades:
        insert_grade(grade, cursor)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    students_data = [
        StudentCreate(name="Alice Johnson", email="alice@example.com", age=15, enrolled_classes=[]),
        StudentCreate(name="Bob Smith", email="bob@example.com", age=16, enrolled_classes=[]),
    ]

    classes_data = [
        ClassCreate(title="Math", teacher_name="Mr. Brown", schedule="Mon-Wed-Fri", students=[1, 2]),
        ClassCreate(title="Science", teacher_name="Dr. Miller", schedule="Tue-Thu", students=[1]),
    ]

    grades_data = [
        GradeCreate(student_id=1, class_id=1, score=95.0, feedback="Excellent work"),
        GradeCreate(student_id=2, class_id=1, score=88.0, feedback="Strong performance"),
    ]

    insert_data(students_data, classes_data, grades_data)