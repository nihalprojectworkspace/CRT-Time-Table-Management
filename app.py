from __future__ import annotations

import os
import json
import secrets
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, url_for, session
from services.scheduler import build_slots, get_breaks, solve, validate_schedule
from services.dependencies import migrate_nullable_references, delete_with_impact

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "database" / "timetable.db"
ROOM_TYPES = ["Lecture Room", "Computer Lab", "Science Lab", "Seminar Hall", "Auditorium"]
DEFAULT_SETTINGS = {"days": "Monday,Tuesday,Wednesday,Thursday,Friday", "periods_per_day": "6", "start_time": "09:00", "duration": "60", "lunch_start": "13:00", "lunch_end": "14:00", "max_consecutive": "2"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("TIMETABLE_SECRET") or secrets.token_hex(32)

SCHEMA = """
CREATE TABLE IF NOT EXISTS courses (course_id TEXT PRIMARY KEY, course_name TEXT NOT NULL UNIQUE, department TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS teachers (teacher_id TEXT PRIMARY KEY, name TEXT NOT NULL, department TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS classrooms (classroom_no TEXT PRIMARY KEY, capacity INTEGER NOT NULL CHECK(capacity > 0), room_type TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS classes (class_id TEXT PRIMARY KEY, course_name TEXT NOT NULL, semester TEXT NOT NULL, section TEXT NOT NULL, strength INTEGER NOT NULL CHECK(strength > 0));
CREATE TABLE IF NOT EXISTS subjects (subject_id TEXT PRIMARY KEY, subject_name TEXT NOT NULL, required_room_type TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS subject_assignments (assignment_id INTEGER PRIMARY KEY AUTOINCREMENT, class_id TEXT NOT NULL REFERENCES classes(class_id) ON DELETE RESTRICT, subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON DELETE RESTRICT, teacher_id TEXT NOT NULL REFERENCES teachers(teacher_id) ON DELETE RESTRICT, weekly_hours INTEGER NOT NULL CHECK(weekly_hours > 0), UNIQUE(class_id, subject_id, teacher_id));
CREATE TABLE IF NOT EXISTS timetable (timetable_id INTEGER PRIMARY KEY AUTOINCREMENT, class_id TEXT NOT NULL REFERENCES classes(class_id), day TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL, subject_id TEXT NOT NULL REFERENCES subjects(subject_id), teacher_id TEXT NOT NULL REFERENCES teachers(teacher_id), classroom_no TEXT NOT NULL REFERENCES classrooms(classroom_no), UNIQUE(class_id, day, start_time), UNIQUE(teacher_id, day, start_time), UNIQUE(classroom_no, day, start_time));
CREATE TABLE IF NOT EXISTS settings (setting_key TEXT PRIMARY KEY, setting_value TEXT NOT NULL);
"""

def db():
    if "db" not in g:
        init_db()
        DATABASE.parent.mkdir(exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_=None):
    connection = g.pop("db", None)
    if connection: connection.close()

def init_db():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DATABASE)
    con.execute("PRAGMA foreign_keys = ON")
    needs_migration = con.execute('PRAGMA user_version').fetchone()[0] < 1
    existing = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='classes'").fetchone()
    backup = DATABASE.with_suffix('.pre-courses.bak')
    if needs_migration and existing and not backup.exists():
        destination = sqlite3.connect(backup)
        try: con.backup(destination)
        finally: destination.close()
    con.executescript(SCHEMA)
    if needs_migration:
        migrate_courses(con)
    for key, value in DEFAULT_SETTINGS.items():
        con.execute("INSERT OR IGNORE INTO settings VALUES (?, ?)", (key, value))
    con.commit()
    try:
        migrate_nullable_references(con, DATABASE, backup_existing=bool(existing))
    finally:
        con.close()

def migrate_courses(con):
    for table in ('classes', 'subjects'):
        if 'course_id' not in {r[1] for r in con.execute(f'PRAGMA table_info({table})')}:
            con.execute(f'ALTER TABLE {table} ADD COLUMN course_id TEXT REFERENCES courses(course_id) ON DELETE RESTRICT')
    departments = [r[0] for r in con.execute('SELECT DISTINCT department FROM teachers')]
    for index, (name,) in enumerate(con.execute('SELECT DISTINCT course_name FROM classes').fetchall(), 1):
        department = next((d for d in departments if d.casefold() == name.casefold()), name)
        course_id = f'COURSE{index:03}'
        con.execute('INSERT INTO courses VALUES (?,?,?)', (course_id, name, department))
        con.execute('UPDATE classes SET course_id=? WHERE course_name=?', (course_id, name))
    # Infer a subject only when all its existing assignments agree on a course.
    for subject_id, in con.execute('SELECT subject_id FROM subjects').fetchall():
        courses = con.execute('SELECT DISTINCT c.course_id FROM subject_assignments a JOIN classes c USING(class_id) WHERE a.subject_id=?', (subject_id,)).fetchall()
        if len(courses) == 1:
            con.execute('UPDATE subjects SET course_id=? WHERE subject_id=?', (courses[0][0], subject_id))
    if con.execute('SELECT COUNT(*) FROM timetable').fetchone()[0]:
        con.execute("INSERT OR REPLACE INTO settings VALUES ('status', 'Outdated')")
    con.execute('PRAGMA user_version=1')

def rows(sql, params=()): return db().execute(sql, params).fetchall()
def one(sql, params=()): return db().execute(sql, params).fetchone()

def settings():
    values = DEFAULT_SETTINGS.copy()
    values.update({r["setting_key"]: r["setting_value"] for r in rows("SELECT * FROM settings")})
    return values

def slots():
    return build_slots(settings())

def mark_outdated():
    if one('SELECT COUNT(*) AS n FROM timetable')['n']:
        db().execute("INSERT OR REPLACE INTO settings VALUES ('status', 'Outdated')")

@app.before_request
def protect_forms():
    session.setdefault('csrf_token', secrets.token_hex(32))
    if request.method == 'POST' and not secrets.compare_digest(session['csrf_token'].encode(), request.form.get('csrf_token', '').encode()):
        abort(400, description='The form expired. Reload the page and try again.')

@app.context_processor
def common_context():
    values = settings()
    return {'schedule_status': values.get('status', 'Outdated' if one('SELECT COUNT(*) AS n FROM timetable')['n'] else 'Not Generated'), 'last_generated': values.get('last_generated', '')}

def validate_record(meta, form):
    data = {key: form.get(key, '').strip() for key, _, _ in meta['fields']}
    for key, label, kind in meta['fields']:
        if not data[key] or len(data[key]) > 200:
            raise ValueError(f'{label} is required and must be at most 200 characters.')
        if kind == 'number':
            try: value = int(data[key])
            except ValueError: raise ValueError(f'{label} must be a positive whole number.')
            if not 1 <= value <= 100000: raise ValueError(f'{label} must be between 1 and 100000.')
            data[key] = value
        if kind == 'select' and data[key] not in {value for value, _ in field_choices(key)}:
            raise ValueError(f'Choose a valid {label.lower()}.')
    if '/' in data[meta['pk']]: raise ValueError('IDs cannot contain a slash.')
    return data

def field_choices(key):
    if key == 'room_type': return [(value, value) for value in ROOM_TYPES]
    if key == 'required_room_type': return [(r[0], r[0]) for r in rows('SELECT DISTINCT room_type FROM classrooms ORDER BY room_type')]
    if key == 'department': return [(r[0], r[0]) for r in rows('SELECT DISTINCT department FROM courses ORDER BY department')]
    if key == 'course_id': return [(r['course_id'], r['course_name']) for r in rows('SELECT * FROM courses ORDER BY course_name')]
    return []

ENTITIES = {
 "courses": {"title":"Courses", "pk":"course_id", "fields":[("course_id","Course ID","text"),("course_name","Course name","text"),("department","Department","text")]},
 "teachers": {"title":"Teachers", "pk":"teacher_id", "fields":[("teacher_id","Teacher ID","text"),("name","Teacher name","text"),("department","Department","select")]},
 "classrooms": {"title":"Classrooms", "pk":"classroom_no", "fields":[("classroom_no","Room number","text"),("capacity","Capacity","number"),("room_type","Room type","select")]},
 "classes": {"title":"Classes", "pk":"class_id", "fields":[("class_id","Class ID","text"),("course_id","Course","select"),("semester","Semester","text"),("section","Section","text"),("strength","Strength","number")]},
 "subjects": {"title":"Subjects", "pk":"subject_id", "fields":[("subject_id","Subject ID","text"),("subject_name","Subject name","text"),("course_id","Course","select"),("required_room_type","Required room type","select")]},
}

REPAIR_FIELDS = {'courses': (), 'classrooms': (), 'teachers': ('department',), 'classes': ('course_id',), 'subjects': ('course_id', 'required_room_type')}
ASSIGNMENT_QUERY = '''SELECT a.*, c.course_name, COALESCE(c.course_id,s.course_id) AS course_id,
    c.course_id AS class_course, s.course_id AS subject_course,
    s.subject_name, s.required_room_type, t.name, t.department
    FROM subject_assignments a LEFT JOIN classes c USING(class_id)
    LEFT JOIN subjects s USING(subject_id) LEFT JOIN teachers t USING(teacher_id)'''

def needs_assignment_repair(record):
    return any(record[field] is None for field in ('class_id', 'subject_id', 'teacher_id', 'class_course', 'subject_course', 'department', 'required_room_type'))

@app.route("/")
def dashboard():
    counts = {k: one(f"SELECT COUNT(*) AS count FROM {k}")["count"] for k in [*ENTITIES, "subject_assignments","timetable"]}
    missing = rows("SELECT c.* FROM classes c LEFT JOIN subject_assignments a ON a.class_id=c.class_id WHERE a.assignment_id IS NULL")
    collections = {entity: rows(f'SELECT * FROM {entity} ORDER BY {meta["pk"]} LIMIT 8') for entity, meta in ENTITIES.items()}
    return render_template("dashboard.html", counts=counts, missing=missing, collections=collections, entities=ENTITIES, course_names=dict(field_choices('course_id')))

@app.route("/<entity>", methods=["GET", "POST"])
def manage(entity):
    if entity not in ENTITIES: abort(404)
    meta = ENTITIES[entity]
    if request.method == "POST":
        try:
            data = validate_record(meta, request.form)
            if entity == 'classes': data['course_name'] = one('SELECT course_name FROM courses WHERE course_id=?', (data['course_id'],))[0]
            columns = ", ".join(data); marks = ", ".join("?" * len(data))
            db().execute(f"INSERT INTO {entity} ({columns}) VALUES ({marks})", tuple(data.values())); mark_outdated(); db().commit()
            flash('Record saved.', 'success'); return redirect(url_for("manage", entity=entity))
        except ValueError as e: flash(str(e), 'error')
        except sqlite3.IntegrityError:
            db().rollback(); flash('That ID already exists or the record is invalid.', 'error')
    query = request.args.get("q", "").strip()
    filter_field = {'courses': 'department', 'teachers': 'department', 'classrooms': 'room_type', 'subjects': 'course_id', 'classes': 'course_id'}[entity]
    selected_filter = request.args.get('filter', '')
    filter_options = [r[filter_field] for r in rows(f'SELECT DISTINCT {filter_field} FROM {entity} ORDER BY {filter_field}')]
    conditions, params = [], []
    if query:
        conditions.append('(' + ' OR '.join(f'{f[0]} LIKE ?' for f in meta['fields']) + ')')
        params.extend([f'%{query}%'] * len(meta['fields']))
    if selected_filter:
        conditions.append(f'{filter_field}=?'); params.append(selected_filter)
    repair_condition = ' OR '.join(f'{field} IS NULL' for field in REPAIR_FIELDS[entity]) or '0'
    incomplete_count = one(f'SELECT COUNT(*) AS n FROM {entity} WHERE {repair_condition}')['n']
    if request.args.get('repair') == '1': conditions.append(f'({repair_condition})')
    data = rows(f"SELECT * FROM {entity}" + (' WHERE ' + ' AND '.join(conditions) if conditions else '') + f" ORDER BY {meta['pk']}", params)
    return render_template("manage.html", entity=entity, meta=meta, data=data, choices={key:field_choices(key) for key,_,_ in meta['fields']}, course_names=dict(field_choices('course_id')), query=query, filter_options=[x for x in filter_options if x is not None], selected_filter=selected_filter, filter_label=filter_field.replace('_id','').replace('_',' ').capitalize(), incomplete_count=incomplete_count)

@app.route('/<entity>/<key>/edit', methods=['GET', 'POST'])
def edit(entity, key):
    if entity not in ENTITIES: abort(404)
    meta = ENTITIES[entity]
    record = one(f"SELECT * FROM {entity} WHERE {meta['pk']}=?", (key,))
    if record is None: abort(404)
    if request.method == 'POST':
        try:
            data = validate_record(meta, request.form)
            if data[meta['pk']] != key: raise ValueError('The record ID cannot be changed.')
            if entity == 'classes': data['course_name'] = one('SELECT course_name FROM courses WHERE course_id=?', (data['course_id'],))[0]
            if entity == 'courses' and data['department'] != record['department'] and one('SELECT 1 FROM teachers WHERE department=?', (record['department'],)):
                raise ValueError('Reassign teachers from the current department before changing this course department.')
            fields = [field for field in data if field != meta['pk']]
            db().execute(f"UPDATE {entity} SET {', '.join(f'{field}=?' for field in fields)} WHERE {meta['pk']}=?", tuple(data[field] for field in fields) + (key,))
            if entity == 'courses': db().execute('UPDATE classes SET course_name=? WHERE course_id=?', (data['course_name'], key))
            mark_outdated(); db().commit()
            flash('Record updated.', 'success')
            return redirect(url_for('manage', entity=entity))
        except ValueError as e: flash(str(e), 'error')
        except sqlite3.IntegrityError:
            db().rollback(); flash('A record with those details already exists.', 'error')
    return render_template('edit.html', entity=entity, meta=meta, record=request.form if request.method == 'POST' else dict(record), choices={key:field_choices(key) for key,_,_ in meta['fields']})

@app.post("/<entity>/<key>/delete")
def delete(entity, key):
    if entity not in ENTITIES: abort(404)
    try:
        affected = delete_with_impact(db(), entity, ENTITIES[entity]['pk'], key)
        if affected is None: abort(404)
        flash(f'Delete successful: {key} was removed.', 'success')
        if affected:
            for change in affected:
                target = change['entity']
                change['url'] = url_for('assignments', repair='1') if target == 'subject_assignments' else url_for('timetable', _anchor='incomplete-periods') if target == 'timetable' else url_for('manage', entity=target, repair='1')
            flash(affected, 'dependencies')
    except sqlite3.Error:
        db().rollback(); flash('Deletion could not be saved. The record and its child records have been left unchanged.', 'error')
    return redirect(url_for("manage", entity=entity))

@app.route("/assignments", methods=["GET", "POST"])
def assignments():
    if request.method == "POST":
        data = tuple(request.form.get(k, "").strip() for k in ("class_id","subject_id","teacher_id","weekly_hours"))
        try:
            if not all(data) or not 1 <= int(data[3]) <= 168: raise ValueError
            data = data[:3] + (int(data[3]),)
            group = one('SELECT * FROM classes WHERE class_id=?', (data[0],))
            subject = one('SELECT * FROM subjects WHERE subject_id=?', (data[1],))
            teacher = one('SELECT * FROM teachers WHERE teacher_id=?', (data[2],))
            course = one('SELECT * FROM courses WHERE course_id=?', (group['course_id'],)) if group else None
            if not course or not subject or not teacher or subject['course_id'] != course['course_id'] or teacher['department'] != course['department']:
                raise ValueError('Choose a class and subject from the same course, and a teacher from its department.')
            if request.form.get('course_id') and request.form['course_id'] != course['course_id']:
                raise ValueError('The selected class does not belong to the selected course.')
            edit_id = request.form.get('assignment_id')
            if edit_id:
                if not one('SELECT * FROM subject_assignments WHERE assignment_id=?', (edit_id,)): abort(404)
                db().execute('UPDATE subject_assignments SET class_id=?,subject_id=?,teacher_id=?,weekly_hours=? WHERE assignment_id=?', data + (edit_id,))
            else:
                db().execute("INSERT INTO subject_assignments(class_id,subject_id,teacher_id,weekly_hours) VALUES(?,?,?,?)", data)
            mark_outdated(); db().commit(); flash("Teaching assignment saved.", "success"); return redirect(url_for("assignments"))
        except (ValueError, sqlite3.IntegrityError) as error:
            db().rollback(); flash(str(error) if isinstance(error,ValueError) and str(error) and 'invalid literal' not in str(error) else 'Choose valid records and 1–168 whole weekly periods. Duplicate assignments are not allowed.', 'error')
    data = rows(ASSIGNMENT_QUERY + ' ORDER BY a.class_id, s.subject_name, a.assignment_id')
    incomplete_count = sum(needs_assignment_repair(record) for record in data)
    if request.args.get('repair') == '1': data = [record for record in data if needs_assignment_repair(record)]
    for field in ('class_id', 'subject_id', 'teacher_id'):
        if request.args.get(field): data = [record for record in data if record[field] == request.args[field]]
    totals = defaultdict(int)
    for item in data: totals[item['class_id'] or 'NULL class'] += item['weekly_hours']
    return render_template("assignments.html", data=data, classes=rows("SELECT * FROM classes"), subjects=rows("SELECT * FROM subjects"), teachers=rows("SELECT * FROM teachers"), courses=rows('SELECT * FROM courses ORDER BY course_name'), record=request.form, incomplete_count=incomplete_count, totals=totals)

@app.post("/assignments/<int:assignment_id>/delete")
def delete_assignment(assignment_id):
    db().execute("DELETE FROM subject_assignments WHERE assignment_id=?", (assignment_id,)); mark_outdated(); db().commit(); flash("Assignment deleted.", "success"); return redirect(url_for("assignments"))

@app.get('/assignments/<int:assignment_id>/edit')
def edit_assignment(assignment_id):
    record = one(ASSIGNMENT_QUERY + ' WHERE a.assignment_id=?', (assignment_id,))
    if record is None: abort(404)
    return render_template('edit_assignment.html', record=dict(record), classes=rows('SELECT * FROM classes'), subjects=rows('SELECT * FROM subjects'), teachers=rows('SELECT * FROM teachers'), courses=rows('SELECT * FROM courses ORDER BY course_name'))

def validate_inputs():
    problems=[]; all_classes=rows("SELECT * FROM classes"); assignments=rows("SELECT a.*, c.strength, s.required_room_type FROM subject_assignments a LEFT JOIN classes c USING(class_id) LEFT JOIN subjects s USING(subject_id)")
    incomplete = one('SELECT COUNT(*) AS n FROM timetable WHERE class_id IS NULL OR subject_id IS NULL OR teacher_id IS NULL OR classroom_no IS NULL')['n']
    if incomplete:
        problems.append(f'{incomplete} saved timetable period(s) have missing references. Delete the damaged timetable and repair all source records before generating again.')
    for entity, fields in REPAIR_FIELDS.items():
        for field in fields:
            count = one(f'SELECT COUNT(*) AS n FROM {entity} WHERE {field} IS NULL')['n']
            if count: problems.append(f"{ENTITIES[entity]['title']}: {count} record(s) have NULL {field.replace('_',' ')}. Edit them to restore the missing values.")
    for assignment in rows(ASSIGNMENT_QUERY):
        if needs_assignment_repair(assignment): problems.append(f"Assignment {assignment['assignment_id']} has NULL references or incomplete source records. Repair its class, subject and teacher before generation.")
    available=defaultdict(list)
    for r in rows("SELECT * FROM classrooms") : available[r['room_type']].append(r)
    assigned={a['class_id'] for a in assignments}
    try: cap=len(slots())
    except ValueError as e: return [f'Correct scheduling settings: {e}'], assignments
    for c in all_classes:
        if c['class_id'] not in assigned: problems.append(f"{c['class_id']} has no subject assignments.")
        if sum(a['weekly_hours'] for a in assignments if a['class_id']==c['class_id']) > cap: problems.append(f"{c['class_id']} needs more periods than the {cap} available slots.")
    for a in assignments:
        if a['strength'] is None or a['required_room_type'] is None: continue
        compatible=[r for r in available[a['required_room_type']] if r['capacity'] >= a['strength']]
        if not compatible: problems.append(f"{a['class_id']} / {a['subject_id']} has no suitable {a['required_room_type']} with enough capacity.")
    for record in rows('SELECT a.assignment_id, c.course_id AS class_course, s.course_id AS subject_course, t.department AS teacher_department, co.department AS course_department FROM subject_assignments a LEFT JOIN classes c USING(class_id) LEFT JOIN subjects s USING(subject_id) LEFT JOIN teachers t USING(teacher_id) LEFT JOIN courses co ON co.course_id=c.course_id'):
        if not record['class_course'] or record['class_course'] != record['subject_course'] or record['teacher_department'] != record['course_department']:
            problems.append(f"Assignment {record['assignment_id']} needs review: class, subject and teacher must match the course and department.")
    if not assignments: problems.append("Create at least one teaching assignment before generating.")
    for teacher in rows('SELECT teacher_id, SUM(weekly_hours) AS hours FROM subject_assignments WHERE teacher_id IS NOT NULL GROUP BY teacher_id'):
        if teacher['hours'] > cap: problems.append(f"Teacher {teacher['teacher_id']} needs {teacher['hours']} periods but only {cap} slots are available.")
    return problems, assignments

def generate(assignments):
    rooms = rows('SELECT * FROM classrooms')
    available = slots()
    maximum = int(settings()['max_consecutive'])
    schedule = solve(assignments, rooms, available, maximum)
    validate_schedule(schedule, assignments, rooms, available, maximum)
    return schedule

@app.route('/generate', methods=['GET','POST'])
def generate_page():
    if request.method == 'GET': return redirect(url_for('timetable', _anchor='generate'))
    problems, assignments = validate_inputs(); existing=one("SELECT COUNT(*) count FROM timetable")['count']
    if request.method=='POST' and not problems:
        if existing and request.form.get('replace') != 'yes':
            flash('Confirm replacement of the existing timetable before generating.', 'error')
            return redirect(url_for('timetable', _anchor='generate'))
        try:
            con = db()
            con.execute('BEGIN IMMEDIATE')
            if one('SELECT COUNT(*) AS n FROM timetable')['n'] and request.form.get('replace') != 'yes':
                raise ValueError('A timetable was saved by another request. Reload and confirm replacement.')
            problems, assignments = validate_inputs()
            if problems: raise ValueError('; '.join(problems))
            schedule=generate(assignments)
            con.execute("DELETE FROM timetable")
            con.executemany("INSERT INTO timetable(class_id,day,start_time,end_time,subject_id,teacher_id,classroom_no) VALUES(:class_id,:day,:start_time,:end_time,:subject_id,:teacher_id,:classroom_no)", schedule)
            con.execute("INSERT OR REPLACE INTO settings VALUES ('status', 'Generated')")
            con.execute("INSERT OR REPLACE INTO settings VALUES ('last_generated', ?)", (datetime.now().astimezone().isoformat(timespec='seconds'),))
            con.execute("INSERT OR REPLACE INTO settings VALUES ('saved_slots', ?)", (json.dumps(slots()),))
            con.execute("INSERT OR REPLACE INTO settings VALUES ('saved_breaks', ?)", (json.dumps(get_breaks(settings())),))
            con.commit()
            flash(f"Generated and stored {len(schedule)} conflict-free periods.", "success"); return redirect(url_for('timetable'))
        except (ValueError, sqlite3.Error) as e:
            db().rollback()
            if not existing:
                db().execute("INSERT OR REPLACE INTO settings VALUES ('status', 'Generation Failed')"); db().commit()
            flash(str(e) if isinstance(e, ValueError) else 'The timetable could not be saved. The previous schedule has been preserved.', 'error')
    if problems:
        for problem in problems: flash(problem, 'error')
    return redirect(url_for('timetable', _anchor='generate'))

@app.post('/timetable/delete')
def delete_timetable():
    con = db()
    try:
        con.execute('BEGIN IMMEDIATE')
        con.execute('DELETE FROM timetable')
        con.execute("DELETE FROM settings WHERE setting_key IN ('last_generated', 'saved_slots', 'saved_breaks')")
        con.execute("INSERT OR REPLACE INTO settings VALUES ('status', 'Not Generated')")
        con.commit()
        flash('Saved timetable deleted. Academic records and schedule configuration have been preserved.', 'success')
    except sqlite3.Error:
        con.rollback()
        flash('The timetable could not be deleted. Please try again.', 'error')
    return redirect(url_for('timetable'))

@app.route('/timetable')
def timetable():
    view=request.args.get('view','class'); selected=request.args.get('id','')
    if view not in ('class', 'teacher', 'room'): abort(400, description='Unknown timetable view.')
    options=rows(f"SELECT {'class_id' if view=='class' else 'teacher_id' if view=='teacher' else 'classroom_no'} AS id, {'class_id' if view=='class' else 'name' if view=='teacher' else 'classroom_no'} AS label FROM {'classes' if view=='class' else 'teachers' if view=='teacher' else 'classrooms'} ORDER BY label")
    if selected not in {option['id'] for option in options}: selected=options[0]['id'] if options else ''
    column={'class':'class_id','teacher':'teacher_id','room':'classroom_no'}[view]
    data=rows(f"SELECT tt.*, s.subject_name, t.name, c.course_name FROM timetable tt LEFT JOIN subjects s USING(subject_id) LEFT JOIN teachers t USING(teacher_id) LEFT JOIN classes c USING(class_id) WHERE tt.{column}=?",(selected,)) if selected else []
    incomplete_periods = rows('SELECT tt.*, s.subject_name, t.name FROM timetable tt LEFT JOIN subjects s USING(subject_id) LEFT JOIN teachers t USING(teacher_id) WHERE tt.class_id IS NULL OR tt.subject_id IS NULL OR tt.teacher_id IS NULL OR tt.classroom_no IS NULL ORDER BY tt.timetable_id')
    grid={(r['day'],r['start_time']):r for r in data}
    # Render persisted times even when the current generation settings have changed.
    saved = rows('SELECT DISTINCT day,start_time,end_time FROM timetable')
    snapshot = settings().get('saved_slots')
    if saved and snapshot:
        slot_list = json.loads(snapshot)
        days = list(dict.fromkeys(slot[0] for slot in slot_list))
    elif saved:
        from services.scheduler import WEEKDAYS
        days = sorted({r['day'] for r in saved}, key=WEEKDAYS.index)
        times = sorted({(r['start_time'], r['end_time']) for r in saved})
        slot_list = [(day, start, end) for start, end in times for day in days]
    else:
        try:
            slot_list = slots(); days = [x.strip() for x in settings()['days'].split(',')]
        except ValueError as e:
            flash(f'Correct scheduling settings: {e}', 'error')
            slot_list = []; days = []
    break_list = json.loads(settings().get('saved_breaks', '[]')) if saved else get_breaks(settings())
    time_columns = [dict(start=start, end=end, name='', kind='period') for start,end in sorted({(s[1], s[2]) for s in slot_list})]
    if saved and 'saved_breaks' not in settings():
        # Older timetables only stored periods; preserve their gaps as generic breaks.
        break_list = [dict(name='Break', start=left['end'], end=right['start']) for left,right in zip(time_columns,time_columns[1:]) if left['end'] < right['start']]
    if time_columns:
        first, last = time_columns[0]['start'], time_columns[-1]['end']
        time_columns += [dict(**b, kind='break') for b in break_list if b['start'] >= first and b['end'] <= last]
    time_columns.sort(key=lambda column:column['start'])
    problems, _ = validate_inputs()
    return render_template('timetable.html', view=view, selected=selected, options=options, grid=grid, time_columns=time_columns, days=days, problems=problems, existing=bool(saved), incomplete_periods=incomplete_periods)

@app.route('/settings', methods=['GET','POST'])
def settings_page():
    if request.method=='POST':
        try:
            values={k:request.form.get(k, settings().get(k, '')).strip() for k in DEFAULT_SETTINGS}
            if 'breaks_form' in request.form:
                names, starts, ends = (request.form.getlist(key) for key in ('break_name', 'break_start', 'break_end'))
                if not len(names) == len(starts) == len(ends): raise ValueError('Complete every break row.')
                values['breaks'] = json.dumps([dict(name=name,start=start,end=end) for name,start,end in zip(names,starts,ends)])
            elif 'breaks' in request.form: values['breaks'] = request.form['breaks']
            build_slots(values)
            if 'breaks' in values: values['breaks'] = json.dumps(get_breaks(values))
            values['days'] = ','.join(day.strip() for day in values['days'].split(','))
            db().executemany("INSERT INTO settings VALUES (?,?) ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value", values.items()); mark_outdated(); db().commit(); flash('Scheduling settings saved. Regenerate to apply them.', 'success'); return redirect(url_for('settings_page'))
        except ValueError as e: flash(str(e), 'error')
    return render_template('settings.html', values=settings(), breaks=get_breaks(settings()))

@app.errorhandler(sqlite3.Error)
def database_error(error):
    connection = g.get('db')
    if connection: connection.rollback()
    app.logger.error('Database operation failed', exc_info=error)
    return 'The database is temporarily unavailable. Please retry. No incomplete changes were saved.', 503

if __name__ == '__main__':
    init_db(); app.run()
