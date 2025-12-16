import csv
from typing import List, Dict, Optional
import re

def _parse_score(s: Optional[str]) -> Optional[float]:
    if not s:
        return None
    s = s.strip()
    if s == '':
        return None
    # extract first numeric substring (handles values like "[9]", "88%", " 7.5 ", etc.)
    m = re.search(r'[-+]?\d*\.?\d+', s)
    if not m:
        return None
    try:
        return float(m.group())
    except Exception:
        return None

def _split_multi(value: Optional[str]) -> List[str]:
    if not value:
        return []
    parts = re.split(r'\s*[;,|/]\s*', value)
    return [p.strip() for p in parts if p.strip()]

def scrape_students_from_csv(file_path: str) -> Dict[str, List[Dict]]:
    """
    Read a CSV file (e.g. dummy_students.csv) and return {'students', 'grades'}.
    Supports flexible headers: 'name', 'student', 'full name'; 'grade', 'score', 'grades'; 'email'; 'age'.
    Multiple grades per cell may be separated by , ; | or /.
    """
    with open(file_path, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    students_map = {}  # key -> {'name', 'email', 'age'}
    grades_temp = []  # entries with student_key and score

    for row in rows:
        norm = {k.strip().lower(): (v.strip() if v is not None else '') for k, v in row.items()}

        name = norm.get('name') or norm.get('student') or norm.get('full name') or ''
        email = norm.get('email') or ''
        age_raw = norm.get('age') or ''
        grades_cell = norm.get('grades') or norm.get('grade') or norm.get('score') or ''

        grade_vals = _split_multi(grades_cell)

        try:
            age = int(age_raw) if age_raw else None
        except Exception:
            age = None

        key = (name or f'unknown_{len(students_map)+1}', email or '')

        if key not in students_map:
            students_map[key] = {
                'name': name,
                'email': email,
                'age': age
            }
        else:
            if students_map[key]['age'] is None and age is not None:
                students_map[key]['age'] = age

        # collect grades (each grade value becomes a separate grade record)
        for gv in grade_vals:
            score = _parse_score(gv)
            grades_temp.append({'student_key': key, 'score': score, 'feedback': None})

    # build students list with new ids
    students_list = []
    key_to_new_id = {}
    for i, (key, data) in enumerate(students_map.items(), start=1):
        key_to_new_id[key] = i
        students_list.append({
            'id': i,
            'name': data['name'],
            'email': data['email'],
            'age': data['age']
        })

    # remap grades to use new student ids (no class_id, no feedback)
    grades_list = []
    for g in grades_temp:
        new_sid = key_to_new_id.get(g['student_key'])
        if new_sid:
            grades_list.append({
                'student_id': new_sid,
                'score': g['score']
            })

    return {'students': students_list, 'grades': grades_list}

if __name__ == '__main__':
    # simple demo: expects dummy_students.csv in current directory
    import json
    parsed = scrape_students_from_csv('dummy_students.csv')
    print(json.dumps(parsed, indent=2, ensure_ascii=False))