"""Nullable references and transactional parent deletion with an impact report."""
import sqlite3


REPLACEMENTS = {
    'teachers': 'teacher_id TEXT PRIMARY KEY, name TEXT NOT NULL, department TEXT',
    'classes': 'class_id TEXT PRIMARY KEY, course_name TEXT, semester TEXT NOT NULL, section TEXT NOT NULL, strength INTEGER NOT NULL CHECK(strength > 0), course_id TEXT REFERENCES courses(course_id) ON DELETE SET NULL',
    'subjects': 'subject_id TEXT PRIMARY KEY, subject_name TEXT NOT NULL, required_room_type TEXT, course_id TEXT REFERENCES courses(course_id) ON DELETE SET NULL',
    'subject_assignments': 'assignment_id INTEGER PRIMARY KEY AUTOINCREMENT, class_id TEXT REFERENCES classes(class_id) ON DELETE SET NULL, subject_id TEXT REFERENCES subjects(subject_id) ON DELETE SET NULL, teacher_id TEXT REFERENCES teachers(teacher_id) ON DELETE SET NULL, weekly_hours INTEGER NOT NULL CHECK(weekly_hours > 0), UNIQUE(class_id, subject_id, teacher_id)',
    'timetable': 'timetable_id INTEGER PRIMARY KEY AUTOINCREMENT, class_id TEXT REFERENCES classes(class_id) ON DELETE SET NULL, day TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL, subject_id TEXT REFERENCES subjects(subject_id) ON DELETE SET NULL, teacher_id TEXT REFERENCES teachers(teacher_id) ON DELETE SET NULL, classroom_no TEXT REFERENCES classrooms(classroom_no) ON DELETE SET NULL, UNIQUE(class_id, day, start_time), UNIQUE(teacher_id, day, start_time), UNIQUE(classroom_no, day, start_time)',
}


def migrate_nullable_references(connection, database_path, backup_existing):
    if connection.execute('PRAGMA user_version').fetchone()[0] >= 2:
        return
    backup_path = database_path.with_suffix('.pre-null-deletes.bak')
    if backup_existing and not backup_path.exists():
        backup = sqlite3.connect(backup_path)
        try:
            connection.backup(backup)
        finally:
            backup.close()
    # SQLite cannot remove NOT NULL or change a foreign-key action in place.
    # Rebuild in one transaction with enforcement restored after the integrity check.
    connection.execute('PRAGMA foreign_keys=OFF')
    try:
        connection.execute('BEGIN IMMEDIATE')
        # Another process may have completed the migration while we waited.
        if connection.execute('PRAGMA user_version').fetchone()[0] >= 2:
            connection.rollback()
            return
        definitions = connection.execute("SELECT sql FROM sqlite_master WHERE type IN ('index','trigger') AND sql IS NOT NULL AND tbl_name IN ('teachers','classes','subjects','subject_assignments','timetable')").fetchall()
        sequences = dict(connection.execute('SELECT name,seq FROM sqlite_sequence'))
        for table, definition in REPLACEMENTS.items():
            columns = ', '.join(f'"{row[1]}"' for row in connection.execute(f'PRAGMA table_info({table})'))
            connection.execute(f'CREATE TABLE _nullable_{table} ({definition})')
            connection.execute(f'INSERT INTO _nullable_{table} ({columns}) SELECT {columns} FROM {table}')
            connection.execute(f'DROP TABLE {table}')
            connection.execute(f'ALTER TABLE _nullable_{table} RENAME TO {table}')
        for (definition,) in definitions:
            connection.execute(definition)
        for table in ('subject_assignments', 'timetable'):
            if table in sequences:
                connection.execute('UPDATE sqlite_sequence SET seq=MAX(seq, ?) WHERE name=?', (sequences[table], table))
        if connection.execute('PRAGMA foreign_key_check').fetchall():
            raise sqlite3.IntegrityError('Foreign-key integrity check failed during migration')
        connection.execute('PRAGMA user_version=2')
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.execute('PRAGMA foreign_keys=ON')


# Only direct foreign keys are cleared; the child rows and their IDs survive.
CHILDREN = {
    'courses': [('classes', 'course_id'), ('subjects', 'course_id')],
    'teachers': [('subject_assignments', 'teacher_id'), ('timetable', 'teacher_id')],
    'classes': [('subject_assignments', 'class_id'), ('timetable', 'class_id')],
    'subjects': [('subject_assignments', 'subject_id'), ('timetable', 'subject_id')],
    'classrooms': [('timetable', 'classroom_no')],
}
TABLE_LABELS = {'classes': 'Classes', 'subjects': 'Subjects', 'teachers': 'Teachers', 'subject_assignments': 'Subject Assignments', 'timetable': 'Timetable'}


def delete_with_impact(connection, entity, primary_key, key):
    """Delete one parent atomically and return counts per changed table/field."""
    connection.execute('BEGIN IMMEDIATE')
    try:
        record = connection.execute(f'SELECT * FROM {entity} WHERE {primary_key}=?', (key,)).fetchone()
        if record is None:
            connection.rollback()
            return None
        affected = []

        def record_effect(table, field, value, clear=False):
            count = connection.execute(f'SELECT COUNT(*) FROM {table} WHERE {field}=?', (value,)).fetchone()[0]
            if count:
                affected.append(dict(table=TABLE_LABELS[table], entity=table, field=field, count=count))
                if clear:
                    connection.execute(f'UPDATE {table} SET {field}=NULL WHERE {field}=?', (value,))

        for table, field in CHILDREN[entity]:
            record_effect(table, field, key)
        if entity == 'courses':
            count = connection.execute('SELECT COUNT(*) FROM classes WHERE course_id=? AND course_name IS NOT NULL', (key,)).fetchone()[0]
            if count:
                affected.append(dict(table='Classes', entity='classes', field='course_name', count=count))
                connection.execute('UPDATE classes SET course_name=NULL WHERE course_id=?', (key,))
            # Department is shared by courses, so it survives until the last one is removed.
            if not connection.execute('SELECT 1 FROM courses WHERE department=? AND course_id<>?', (record['department'], key)).fetchone():
                record_effect('teachers', 'department', record['department'], clear=True)
        if entity == 'classrooms':
            # A room type remains valid while any other classroom provides it.
            if not connection.execute('SELECT 1 FROM classrooms WHERE room_type=? AND classroom_no<>?', (record['room_type'], key)).fetchone():
                record_effect('subjects', 'required_room_type', record['room_type'], clear=True)
        connection.execute(f'DELETE FROM {entity} WHERE {primary_key}=?', (key,))
        if connection.execute('SELECT 1 FROM timetable LIMIT 1').fetchone():
            connection.execute("INSERT OR REPLACE INTO settings VALUES ('status', 'Outdated')")
        connection.commit()
        return affected
    except Exception:
        connection.rollback()
        raise
