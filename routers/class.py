import sqlite3
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends

from models.class_model import Class, ClassCreate   # adjust filename as needed
from database import get_db_connection
from auth.security import get_api_key

router = APIRouter()


# ---------------------------------------------------------
# GET ALL CLASSES
# ---------------------------------------------------------
@router.get("/", response_model=List[Class])
def get_classes():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch classes
    cursor.execute("SELECT id, title, teacher_name, schedule FROM classes")
    rows = cursor.fetchall()

    classes_list = []

    for row in rows:
        class_id = row["id"]

        # Fetch enrolled student IDs
        cursor.execute(
            "SELECT student_id FROM class_students WHERE class_id = ?",
            (class_id,)
        )
        student_ids = [r["student_id"] for r in cursor.fetchall()]

        classes_list.append(
            Class(
                id=class_id,
                title=row["title"],
                teacher_name=row["teacher_name"],
                schedule=row["schedule"],
                students=student_ids,
            )
        )

    conn.close()
    return classes_list


# ---------------------------------------------------------
# CREATE CLASS
# ---------------------------------------------------------
@router.post("/", response_model=Class)
def create_class(
        class_data: ClassCreate,
        _: str = Depends(get_api_key)  # Enforce API key
):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Insert class
        cursor.execute(
            "INSERT INTO classes (title, teacher_name, schedule) VALUES (?, ?, ?)",
            (class_data.title, class_data.teacher_name, class_data.schedule),
        )
        conn.commit()
        class_id = cursor.lastrowid

        # Insert student enrollments into the join table
        for student_id in class_data.students:
            cursor.execute(
                "INSERT OR IGNORE INTO class_students (class_id, student_id) VALUES (?, ?)",
                (class_id, student_id),
            )

        conn.commit()

        return Class(
            id=class_id,
            title=class_data.title,
            teacher_name=class_data.teacher_name,
            schedule=class_data.schedule,
            students=class_data.students,
        )

    finally:
        conn.close()


# ---------------------------------------------------------
# UPDATE CLASS
# ---------------------------------------------------------
@router.put("/{class_id}", response_model=Class)
def update_class(
        class_id: int,
        class_data: ClassCreate,
        _: str = Depends(get_api_key)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Update class main fields
    cursor.execute(
        "UPDATE classes SET title = ?, teacher_name = ?, schedule = ? WHERE id = ?",
        (class_data.title, class_data.teacher_name, class_data.schedule, class_id),
    )

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Class not found")

    # Update student enrollments (simplest method = clear + reinsert)
    cursor.execute("DELETE FROM class_students WHERE class_id = ?", (class_id,))

    for student_id in class_data.students:
        cursor.execute(
            "INSERT OR IGNORE INTO class_students (class_id, student_id) VALUES (?, ?)",
            (class_id, student_id),
        )

    conn.commit()
    conn.close()

    return Class(
        id=class_id,
        title=class_data.title,
        teacher_name=class_data.teacher_name,
        schedule=class_data.schedule,
        students=class_data.students,
    )


# ---------------------------------------------------------
# DELETE CLASS
# ---------------------------------------------------------
@router.delete("/{class_id}", response_model=dict)
def delete_class(
        class_id: int,
        _: str = Depends(get_api_key)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Remove relationship entries first
    cursor.execute("DELETE FROM class_students WHERE class_id = ?", (class_id,))

    # Delete class
    cursor.execute("DELETE FROM classes WHERE id = ?", (class_id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Class not found")

    conn.commit()
    conn.close()

    return {"detail": "Class deleted"}