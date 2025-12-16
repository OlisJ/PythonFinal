import sqlite3
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends

from models.student import Student, StudentCreate
from database import get_db_connection
from auth.security import get_api_key

router = APIRouter()


@router.get("/", response_model=List[Student])
def get_students():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, email, age FROM students")
    students = cursor.fetchall()
    conn.close()

    return [
        {
            "id": student[0],
            "name": student[1],
            "email": student[2],
            "age": student[3],
        }
        for student in students
    ]


@router.post("/", response_model=Student)
def create_student(student: StudentCreate, _: str = Depends(get_api_key)):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO students (name, email, age) "
            "VALUES (?, ?, ?)",
            (student.name, student.email, student.age),
        )

        conn.commit()
        student_id = cursor.lastrowid
        return Student(id=student_id, **student.dict())

    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"The student '{student.name}' already exists."
        )

    finally:
        conn.close()


@router.put("/{student_id}", response_model=Student)
def update_student(student_id: int, student: StudentCreate, _: str = Depends(get_api_key)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE students SET name = ?, email = ?, age = ? "
        "WHERE id = ?",
        (student.name, student.email, student.age, student_id),
    )

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Student not found")

    conn.commit()
    conn.close()

    return Student(id=student_id, **student.dict())


@router.delete("/{student_id}", response_model=dict)
def delete_student(student_id: int, _: str = Depends(get_api_key)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Student not found")

    conn.commit()
    conn.close()

    return {"detail": "Student deleted"}