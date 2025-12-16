
import sqlite3
from typing import List, Tuple
import streamlit as st
import pandas as pd


DB_PATH = 'classroom.db'


def get_db_connection():
	conn = sqlite3.connect(DB_PATH)
	conn.row_factory = sqlite3.Row
	return conn


def fetch_students() -> List[sqlite3.Row]:
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute('SELECT id, name, email, age FROM students ORDER BY id')
	rows = cur.fetchall()
	conn.close()
	return rows


def fetch_grades() -> List[sqlite3.Row]:
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute('SELECT id, student_id, score FROM grades ORDER BY id')
	rows = cur.fetchall()
	conn.close()
	return rows


def add_student(name: str, email: str, age: int | None):
	conn = get_db_connection()
	cur = conn.cursor()
	try:
		cur.execute('INSERT INTO students (name, email, age) VALUES (?, ?, ?)', (name, email, age))
		conn.commit()
		return cur.lastrowid
	except sqlite3.IntegrityError as e:
		raise
	finally:
		conn.close()


def update_student(student_id: int, name: str, email: str, age: int | None):
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute('UPDATE students SET name = ?, email = ?, age = ? WHERE id = ?', (name, email, age, student_id))
	conn.commit()
	conn.close()


def delete_student(student_id: int):
	conn = get_db_connection()
	cur = conn.cursor()
	# delete associated grades first (optional)
	cur.execute('DELETE FROM grades WHERE student_id = ?', (student_id,))
	cur.execute('DELETE FROM students WHERE id = ?', (student_id,))
	conn.commit()
	conn.close()


def add_grade(student_id: int, score: float):
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute('INSERT INTO grades (student_id, score) VALUES (?, ?)', (student_id, score))
	conn.commit()
	last = cur.lastrowid
	conn.close()
	return last


def update_grade(grade_id: int, student_id: int, score: float):
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute('UPDATE grades SET student_id = ?, score = ? WHERE id = ?', (student_id, score, grade_id))
	conn.commit()
	conn.close()


def delete_grade(grade_id: int):
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute('DELETE FROM grades WHERE id = ?', (grade_id,))
	conn.commit()
	conn.close()


def students_select_options() -> List[Tuple[int, str]]:
	rows = fetch_students()
	return [(r['id'], f"{r['id']}: {r['name']} ({r['email']})") for r in rows]


def main():
	st.set_page_config(page_title='Classroom Manager', layout='wide')

	st.title('Classroom Manager — Students & Grades')

	menu = st.sidebar.selectbox('Choose view', ['Students', 'Grades'])

	if menu == 'Students':
		st.header('Students')

		# show students
		students = fetch_students()
		if students:
			df_students = pd.DataFrame([[s['id'], s['name'], s['email'], s['age']] for s in students],
									   columns=['id', 'name', 'email', 'age'])
			st.dataframe(df_students, use_container_width=True)
		else:
			st.info('No students found')

		st.subheader('Add student')
		with st.form('add_student'):
			name = st.text_input('Name')
			email = st.text_input('Email')
			age = st.number_input('Age', min_value=0, max_value=200, step=1, value=0)
			submitted = st.form_submit_button('Add')
			if submitted:
				try:
					age_val = None if age == 0 else int(age)
					add_student(name.strip(), email.strip(), age_val)
					st.success('Student added')
					st.experimental_rerun()
				except sqlite3.IntegrityError:
					st.error('A student with that email already exists')
				except Exception as e:
					st.error(f'Error adding student: {e}')

		st.subheader('Update / Delete student')
		opts = students_select_options()
		if opts:
			sel = st.selectbox('Select student', options=opts, format_func=lambda x: x[1])
			sid = sel[0]
			# fetch current
			conn = get_db_connection()
			cur = conn.cursor()
			cur.execute('SELECT id, name, email, age FROM students WHERE id = ?', (sid,))
			row = cur.fetchone()
			conn.close()

			if row:
				with st.form('update_student'):
					name_u = st.text_input('Name', value=row['name'])
					email_u = st.text_input('Email', value=row['email'])
					age_u = st.number_input('Age', min_value=0, max_value=200, step=1, value=(row['age'] or 0))
					upd = st.form_submit_button('Update')
					if upd:
						try:
							age_val = None if age_u == 0 else int(age_u)
							update_student(sid, name_u.strip(), email_u.strip(), age_val)
							st.success('Student updated')
							st.experimental_rerun()
						except sqlite3.IntegrityError:
							st.error('Email already used by another student')
						except Exception as e:
							st.error(f'Error updating student: {e}')

				# Delete flow: require an explicit confirm click (uses session_state)
				if st.button('Delete student', key=f'delete_prompt_{sid}'):
					st.session_state[f'confirm_delete_student_{sid}'] = True

				if st.session_state.get(f'confirm_delete_student_{sid}'):
					st.warning('This will delete the student and all their grades.')
					if st.button('Confirm delete', key=f'confirm_delete_{sid}'):
						try:
							delete_student(sid)
							st.success('Student deleted (and their grades)')
							# clear state and refresh
							st.session_state.pop(f'confirm_delete_student_{sid}', None)
							st.experimental_rerun()
						except Exception as e:
							st.error(f'Error deleting student: {e}')
					if st.button('Cancel', key=f'cancel_delete_{sid}'):
						st.session_state.pop(f'confirm_delete_student_{sid}', None)
						st.info('Delete canceled')
		else:
			st.info('No students to select')

	else:  # Grades
		st.header('Grades')
		grades = fetch_grades()
		students = fetch_students()
		student_map = {s['id']: s['name'] for s in students}

		if grades:
			df_grades = pd.DataFrame([[g['id'], g['student_id'], student_map.get(g['student_id'], 'Unknown'), g['score']] for g in grades],
									 columns=['id', 'student_id', 'student_name', 'score'])
			st.dataframe(df_grades, use_container_width=True)
		else:
			st.info('No grades found')

		st.subheader('Add grade')
		with st.form('add_grade'):
			student_opts = [(s['id'], f"{s['id']}: {s['name']}") for s in students]
			if student_opts:
				sel = st.selectbox('Student', options=student_opts, format_func=lambda x: x[1])
				student_id = sel[0]
				score = st.number_input('Score', min_value=0.0, max_value=100.0, value=0.0, step=0.1)
				added = st.form_submit_button('Add Grade')
				if added:
					try:
						add_grade(student_id, float(score))
						st.success('Grade added')
						st.experimental_rerun()
					except Exception as e:
						st.error(f'Error adding grade: {e}')
			else:
				st.info('No students available — add students first')

		st.subheader('Update / Delete grade')
		if grades:
			grade_opts = [(g['id'], f"{g['id']}: student {g['student_id']} — {g['score']}") for g in grades]
			selg = st.selectbox('Select grade', options=grade_opts, format_func=lambda x: x[1])
			gid = selg[0]
			conn = get_db_connection()
			cur = conn.cursor()
			cur.execute('SELECT id, student_id, score FROM grades WHERE id = ?', (gid,))
			grow = cur.fetchone()
			conn.close()

			if grow:
				with st.form('update_grade'):
					stu_opts = [(s['id'], f"{s['id']}: {s['name']}") for s in students]
					# default the selectbox to the grade's current student
					default_index = 0
					for i, opt in enumerate(stu_opts):
						if opt[0] == grow['student_id']:
							default_index = i
					selstu = st.selectbox('Student', options=stu_opts, index=default_index, format_func=lambda x: x[1])
					score_u = st.number_input('Score', min_value=0.0, max_value=100.0, value=float(grow['score']), step=0.1)
					upg = st.form_submit_button('Update Grade')
					if upg:
						try:
							update_grade(gid, selstu[0], float(score_u))
							st.success('Grade updated')
							st.experimental_rerun()
						except Exception as e:
							st.error(f'Error updating grade: {e}')

				if st.button('Delete grade', key=f'delete_grade_prompt_{gid}'):
					st.session_state[f'confirm_delete_grade_{gid}'] = True

				if st.session_state.get(f'confirm_delete_grade_{gid}'):
					st.warning('This will permanently delete the selected grade.')
					if st.button('Confirm delete grade', key=f'confirm_delete_grade_{gid}'):
						try:
							delete_grade(gid)
							st.success('Grade deleted')
							st.session_state.pop(f'confirm_delete_grade_{gid}', None)
							st.experimental_rerun()
						except Exception as e:
							st.error(f'Error deleting grade: {e}')
					if st.button('Cancel', key=f'cancel_delete_grade_{gid}'):
						st.session_state.pop(f'confirm_delete_grade_{gid}', None)
						st.info('Delete canceled')
		else:
			st.info('No grades to select')


if __name__ == '__main__':
	main()
