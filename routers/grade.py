import sqlite3
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends

from models.grade import Grade, GradeCreate
from database import get_db_connection
from auth.security import get_api_key

router = APIRouter()


# ---------------------------------------------------------
# GET ALL GRADES
# ---------------------------------------------------------
@router.get("/", response_model=List[Grade])
def get_grades():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, student_id, class_id, score, feedback FROM grades"
    )
    grades = cursor.fetchall()
    conn.close()

    return [
        {
            "id": grade[0],
            "student_id": grade[1],
            "class_id": grade[2],
            "score": grade[3],
            "feedback": grade[4]
        }
        for grade in grades
    ]


# ---------------------------------------------------------
# CREATE GRADE
# ---------------------------------------------------------
@router.post("/", response_model=Grade)
def create_grade(grade: GradeCreate, _: str = Depends(get_api_key)):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO grades (student_id, class_id, score, feedback) "
            "VALUES (?, ?, ?, ?)",
            (grade.student_id, grade.class_id, grade.score, grade.feedback),
        )

        conn.commit()
        grade_id = cursor.lastrowid
        return Grade(id=grade_id, **grade.dict())

    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid student_id or class_id"
        )

    finally:
        conn.close()


# ---------------------------------------------------------
# UPDATE GRADE
# ---------------------------------------------------------
@router.put("/{grade_id}", response_model=Grade)
def update_grade(grade_id: int, grade: GradeCreate, _: str = Depends(get_api_key)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE grades SET student_id = ?, class_id = ?, score = ?, feedback = ? "
        "WHERE id = ?",
        (grade.student_id, grade.class_id, grade.score, grade.feedback, grade_id),
    )

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Grade not found")

    conn.commit()
    conn.close()

    return Grade(id=grade_id, **grade.dict())


# ---------------------------------------------------------
# DELETE GRADE
# ---------------------------------------------------------
@router.delete("/{grade_id}", response_model=dict)
def delete_grade(grade_id: int, _: str = Depends(get_api_key)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM grades WHERE id = ?", (grade_id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Grade not found")

    conn.commit()
    conn.close()

    return {"detail": "Grade deleted"}