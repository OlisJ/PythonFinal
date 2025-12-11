import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin
import concurrent.futures


def _text_or_none(tag):
    return tag.get_text(strip=True) if tag else None


def parse_students_from_html(html: str, selectors: Optional[Dict[str, str]] = None) -> Dict[str, List[Dict]]:
    """
    Parse HTML and return structured data for students, classes and grades.

    Returns a dict with keys: 'students', 'classes', 'grades'.

    - students: list of dicts matching StudentBase (name, email, age, enrolled_classes -> filled with CLASS TITLES initially)
    - classes: list of dicts {id, title}
    - grades: list of dicts matching GradeBase (student_id, class_id, score, feedback) where class is temporarily stored as 'class_title'
    """
    soup = BeautifulSoup(html, 'html.parser')

    # allow custom selectors
    selectors = selectors or {}
    row_sel = selectors.get('row')

    students_raw = []

    # First: try to find a table with header
    table = soup.find('table')
    if table:
        # determine header mapping
        headers = []
        thead = table.find('thead')
        if thead:
            headers = [th.get_text(strip=True).lower() for th in thead.find_all('th')]
        else:
            first_row = table.find('tr')
            if first_row:
                headers = [th.get_text(strip=True).lower() for th in first_row.find_all(['th', 'td'])]

        # fallback: rows are tr under tbody or table
        rows = table.find_all('tr')
        for r in rows[1:]:  # skip header row
            cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
            if not cols:
                continue
            entry = {}
            for i, val in enumerate(cols):
                if i < len(headers):
                    h = headers[i]
                    entry[h] = val
                else:
                    entry[f'col_{i}'] = val
            students_raw.append(entry)
    else:
        # Table not found, look for repeated student blocks
        # Use selector if provided, otherwise try common patterns
        if not row_sel:
            candidates = soup.select('.student') or soup.select('.student-row') or soup.select('div.student')
            if candidates:
                rows = candidates
            else:
                # fallback to list items
                rows = soup.select('ul li') or soup.select('ol li')
        else:
            rows = soup.select(row_sel)

        for r in rows:
            name = None
            class_name = None
            grade = None
            email = None
            age = None

            # try common sub-selectors
            name_tag = r.select_one(selectors.get('name', '.name')) or r.select_one('h2') or r.select_one('a')
            class_tag = r.select_one(selectors.get('class', '.class')) or r.select_one('.course')
            grade_tag = r.select_one(selectors.get('grade', '.grade')) or r.select_one('.score')
            email_tag = r.select_one(selectors.get('email', '.email'))
            age_tag = r.select_one(selectors.get('age', '.age'))

            name = _text_or_none(name_tag)
            class_name = _text_or_none(class_tag)
            grade = _text_or_none(grade_tag)
            email = _text_or_none(email_tag)
            age = _text_or_none(age_tag)

            # If row is a plain li with text like "Name - Class - 95", try splitting
            if not (name or class_name or grade) and r.get_text(strip=True):
                parts = [p.strip() for p in r.get_text(separator='|').split('|') if p.strip()]
                # attempt heuristic
                if len(parts) >= 2:
                    name = name or parts[0]
                    class_name = class_name or parts[1]
                if len(parts) >= 3:
                    grade = grade or parts[2]

            # build raw entry
            entry = {}
            if name:
                entry['name'] = name
            if class_name:
                entry.setdefault('classes', []).append(class_name)
            if grade:
                entry.setdefault('grades', []).append(grade)
            if email:
                entry['email'] = email
            if age:
                entry['age'] = age
            if entry:
                students_raw.append(entry)

    # Normalize raw entries into structured lists and maps
    classes_set = []
    students = []
    grades = []

    # helper to convert grade text to float if possible
    def parse_score(s: Optional[str]) -> Optional[float]:
        if s is None:
            return None
        try:
            # remove percent sign and other noise
            s_clean = s.replace('%', '').strip()
            return float(s_clean)
        except Exception:
            return None

    # iterate and assign temporary ids; store class TITLES on student entries and in grade entries keep 'class_title' temporarily
    for idx, raw in enumerate(students_raw, start=1):
        name = raw.get('name') or raw.get('student') or raw.get('full name')
        email = raw.get('email') or ''
        age_raw = raw.get('age')
        try:
            age = int(age_raw) if age_raw else None
        except Exception:
            age = None

        # classes might be in 'classes' (list) or in key 'class' or header 'class'
        class_names = []
        if 'classes' in raw:
            class_names = raw.get('classes', [])
        elif 'class' in raw:
            class_names = [raw.get('class')]
        else:
            # also check common header keys
            for k in list(raw.keys()):
                if 'class' in k:
                    val = raw.get(k)
                    if val:
                        class_names.append(val)

        # grades: could be in 'grades' or header 'grade' or 'score'
        grade_vals = []
        if 'grades' in raw:
            grade_vals = raw.get('grades', [])
        else:
            for k in list(raw.keys()):
                if 'grade' in k or 'score' in k:
                    val = raw.get(k)
                    if val:
                        grade_vals.append(val)

        # ensure at least one class placeholder
        if not class_names:
            class_names = []

        # store student with enrolled_classes as class TITLES (will be remapped later)
        students.append({
            'id': idx,
            'name': name or f'unknown_{idx}',
            'email': email,
            'age': age,
            'enrolled_classes': []  # will hold class titles for now
        })

        # register classes (titles) and grades (use 'class_title' field for now)
        for i, cname in enumerate(class_names):
            if cname not in classes_set:
                classes_set.append(cname)
            # attach title to student
            students[-1]['enrolled_classes'].append(cname)

            # match grade if available
            score = None
            if i < len(grade_vals):
                score = parse_score(grade_vals[i])
            elif grade_vals:
                # if only one grade provided, assign it to the first class
                score = parse_score(grade_vals[0])

            if score is not None:
                grades.append({
                    'student_id': idx,
                    'class_title': cname,  # temporary, will map to id later
                    'score': score,
                    'feedback': None
                })

    # Build canonical classes list (titles -> ids) and remap enrolled_classes and grades to use class ids
    classes = [{'id': i + 1, 'title': title} for i, title in enumerate(classes_set)]
    class_title_to_id = {c['title']: c['id'] for c in classes}

    # remap students' enrolled_classes from titles -> ids
    for s in students:
        s['enrolled_classes'] = [class_title_to_id.get(title) for title in s['enrolled_classes'] if title in class_title_to_id]

    # remap grades 'class_title' -> 'class_id'
    for g in grades:
        title = g.pop('class_title', None)
        g['class_id'] = class_title_to_id.get(title)
        # keep student_id, score, feedback as-is

    return {'students': students, 'classes': classes, 'grades': grades}


def _find_detail_links(soup: BeautifulSoup, base_url: str, selectors: Optional[Dict[str, str]] = None) -> List[str]:
    """
    Heuristic to find detail/profile links on a page. Optional selectors can provide a CSS selector
    under key 'link' to target anchors explicitly.
    """
    selectors = selectors or {}
    link_sel = selectors.get('link')
    links = set()
    if link_sel:
        for a in soup.select(link_sel):
            href = a.get('href')
            if href:
                links.add(urljoin(base_url, href))
        return list(links)

    # common heuristics
    # look for anchors with words that hint at profile/details or anchors inside student blocks or table rows
    for a in soup.select('a'):
        href = a.get('href')
        if not href:
            continue
        text = (a.get_text(strip=True) or '').lower()
        parent_classes = ' '.join(a.parent.get('class') or [])
        if any(k in text for k in ('profile', 'details', 'student')) or 'student' in parent_classes:
            links.add(urljoin(base_url, href))

    # also look for first anchor in table rows
    for tr in soup.select('table tr'):
        a = tr.select_one('a')
        if a and a.get('href'):
            links.add(urljoin(base_url, a.get('href')))

    return list(links)


def _merge_parsed_results(main_parsed: Dict[str, List[Dict]], detail_parsed_list: List[Dict[str, List[Dict]]]) -> Dict[str, List[Dict]]:
    """
    Merge main page parsed data with one or more detail pages' parsed data.
    Deduplicate students by (name,email). Build a single classes list with unique titles and remap IDs.
    """
    # collect all students (students keep enrolled_classes as ids referencing their source; but because parse_students_from_html normalized to ids per-page
    # we will instead merge by using name/email equality and aggregate the union of class titles by extracting class titles from classes lists)
    # To simplify: reconstruct from all sources using class titles available in each source's classes list.

    # Collect all class titles from every parsed source
    title_set = []
    sources = [main_parsed] + list(detail_parsed_list)
    for src in sources:
        for c in src.get('classes', []):
            if c['title'] not in title_set:
                title_set.append(c['title'])
    class_map = {title: i + 1 for i, title in enumerate(title_set)}
    merged_students = {}
    merged_grades = []

    # Helper to map per-source class_id back to title (if possible)
    def class_id_to_title(src, cid):
        for c in src.get('classes', []):
            if c['id'] == cid:
                return c['title']
        return None

    # merge students and collect enrolled class titles
    for src in sources:
        for s in src.get('students', []):
            key = (s.get('name'), s.get('email') or '')
            if key not in merged_students:
                merged_students[key] = {
                    'name': s.get('name'),
                    'email': s.get('email'),
                    'age': s.get('age'),
                    'enrolled_titles': set(),
                }
            # map enrolled_classes ids in this src to titles
            for cid in s.get('enrolled_classes', []):
                title = class_id_to_title(src, cid)
                if title:
                    merged_students[key]['enrolled_titles'].add(title)

    # merge grades: translate each grade's class id to title then to global id
    for src in sources:
        for g in src.get('grades', []):
            sid = g.get('student_id')
            # find student in this src by id to get name/email mapping
            src_student = next((x for x in src.get('students', []) if x['id'] == sid), None)
            if not src_student:
                continue
            key = (src_student.get('name'), src_student.get('email') or '')
            # find class title
            ctitle = class_id_to_title(src, g.get('class_id'))
            if not ctitle:
                continue
            merged_grades.append({
                'student_key': key,
                'class_title': ctitle,
                'score': g.get('score'),
                'feedback': g.get('feedback')
            })

    # build final students list with new ids and mapped class ids
    students_list = []
    key_to_new_id = {}
    for i, (key, data) in enumerate(merged_students.items(), start=1):
        key_to_new_id[key] = i
        students_list.append({
            'id': i,
            'name': data['name'],
            'email': data['email'],
            'age': data['age'],
            'enrolled_classes': [class_map[t] for t in sorted(data['enrolled_titles'])]
        })

    # remap grades to use new student ids and class ids
    grades_list = []
    for mg in merged_grades:
        new_sid = key_to_new_id.get(mg['student_key'])
        new_cid = class_map.get(mg['class_title'])
        if new_sid and new_cid:
            grades_list.append({
                'student_id': new_sid,
                'class_id': new_cid,
                'score': mg['score'],
                'feedback': mg['feedback']
            })

    classes_list = [{'id': i + 1, 'title': title} for i, title in enumerate(title_set)]

    return {'students': students_list, 'classes': classes_list, 'grades': grades_list}


def scrape_students_from_url(url: str, selectors: Optional[Dict[str, str]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, List[Dict]]:
    """
    Fetch the given URL and parse student/class/grade data using `parse_students_from_html`.
    This enhanced version will look for detail/profile links on the page (heuristic or via selectors['link'])
    and fetch those pages in parallel to enrich/merge the dataset.
    """
    headers = headers or {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/58.0.3029.110 Safari/537.3"
    }
    session = requests.Session()
    resp = session.get(url, headers=headers)
    resp.raise_for_status()
    main_html = resp.text
    main_parsed = parse_students_from_html(main_html, selectors=selectors)

    # find candidate detail links
    soup = BeautifulSoup(main_html, 'html.parser')
    detail_links = _find_detail_links(soup, url, selectors=selectors)

    # fetch detail pages in parallel (limit threads to avoid DOS)
    detail_parsed = []
    if detail_links:
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            future_to_link = {ex.submit(session.get, link, headers=headers): link for link in detail_links}
            for fut in concurrent.futures.as_completed(future_to_link):
                link = future_to_link[fut]
                try:
                    r = fut.result()
                    r.raise_for_status()
                    parsed = parse_students_from_html(r.text, selectors=selectors)
                    detail_parsed.append(parsed)
                except Exception:
                    # ignore single page failures, continue with others
                    continue

    # merge main + detail parsed results
    merged = _merge_parsed_results(main_parsed, detail_parsed)
    return merged


if __name__ == '__main__':
    # Simple example showing how the parser works with sample HTML
    sample_html = '''
    <html>
      <body>
        <table>
          <tr><th>Name</th><th>Class</th><th>Grade</th><th>Email</th></tr>
          <tr><td>Alice Smith</td><td>Math 101</td><td>95</td><td>alice@example.com</td></tr>
          <tr><td>Bob Jones</td><td>History</td><td>88%</td><td>bob@example.com</td></tr>
        </table>
      </body>
    </html>
    '''

    parsed = parse_students_from_html(sample_html)
    print('Students:')
    for s in parsed['students']:
        print(s)
    print('\nClasses:')
    for c in parsed['classes']:
        print(c)
    print('\nGrades:')
    for g in parsed['grades']:
        print(g)
    # Example of scraping from a URL (uncomment to use)