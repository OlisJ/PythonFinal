from books_scrapper import scrape_students_from_csv
from models.student import StudentCreate
from models.grade import GradeCreate
from database import insert_data
from typing import List
import sqlite3

# read CSV and prepare models, then insert into DB
parsed = scrape_students_from_csv('dummy_students.csv')

students_payload: List[StudentCreate] = []
for s in parsed.get('students', []):
    students_payload.append(StudentCreate(name=s['name'], email=s['email'], age=s.get('age')))

grades_payload: List[GradeCreate] = []
# grades in parsed are student_id (local id) and score; we need to map to eventual DB student ids.
# The database.insert_data will insert students first (in same order), so parsed student ids map to insert order.
for g in parsed.get('grades', []):
    score = g.get('score')
    if score is None:
        continue  # skip invalid/missing scores
    try:
        score_val = float(score)
    except Exception:
        continue
    grades_payload.append(GradeCreate(student_id=g['student_id'], score=score_val))

try:
    insert_data(students_payload, grades_payload)
    print("Inserted students and grades into classroom.db")
except sqlite3.IntegrityError as e:
    # likely rerun where unique emails already exist
    print("Insert skipped due to integrity error (possible duplicates):", e)
except Exception as e:
    print("Insert failed:", e)

# print a small sample from the DB so the script verifies the insert
conn = sqlite3.connect('classroom.db')
cur = conn.cursor()
cur.execute('SELECT id,name,email,age FROM students LIMIT 5')
print('students sample:', cur.fetchall())
cur.execute('SELECT id,student_id,score FROM grades LIMIT 5')
print('grades sample:', cur.fetchall())
conn.close()
