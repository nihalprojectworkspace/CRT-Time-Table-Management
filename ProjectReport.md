# Classroom Timetable Management System — Project Report

## Overview

This project is a complete web application for collecting departmental timetable data, validating it, generating a conflict-free schedule, storing it permanently, and viewing it by class, teacher, or classroom. It follows the workflow in `TimetableGenerator.md` and is intentionally usable as a compact academic-project codebase.

## Technology choices

| Layer | Choice | Why |
|---|---|---|
| Backend | Python + Flask | Small, readable, server-rendered application with straightforward routing and form handling. |
| Database | SQLite (`database/timetable.db`) | Zero server configuration, relational constraints, and portable project data. |
| Data access | Python `sqlite3` | Avoids an unnecessary ORM dependency while keeping SQL explicit for learning and maintenance. |
| UI | HTML/Jinja templates, CSS, JavaScript | Fast, responsive interface without a frontend build chain. |

The workspace now includes a `.venv` with Flask installed. Start with `.venv/bin/python app.py` and visit `http://127.0.0.1:5000`. For a fresh checkout, run `python3 -m venv .venv`, then `.venv/bin/python -m pip install -r requirements.txt`. Database directories and tables are initialized automatically for both the script entry point and Flask's CLI/imported application.

## Structure

```
app.py                 Flask routes, schema, validation and persistence
services/scheduler.py  Slot validation, bounded backtracking and final validation
tests/test_app.py      Isolated database and scheduling regression tests
templates/             Jinja page templates and shared shell
static/style.css       dark flat design system and responsive behavior
static/app.js          mobile navigation and destructive-action confirmations
database/timetable.db  created automatically at first start
requirements.txt       Flask dependency
```

## Data model

The relational model now contains `courses`, `teachers`, `classrooms`, `classes`, `subjects`, `subject_assignments`, `timetable`, and `settings`. Courses have a stable course ID, unique course name and department. Classes and subjects reference a course ID with foreign keys. Teachers select their department from the distinct departments entered in Courses. Multiple courses in one department can share its teachers. This represents the requested separate course database as a related table within the same SQLite file, so relationships can be validated together.

Primary keys are supplied identifiers; assignments and timetable records use integer keys. Child foreign keys are nullable and use `ON DELETE SET NULL`: deleting a parent preserves its child records for repair. Class course names are retained as a compatibility field for older databases and synchronized from the selected course; deleting that course clears both its ID and cached name. Unique constraints prevent duplicate teacher/class/room occupancy for a timetable day and starting time.

The versioned migration creates a SQLite backup at `database/timetable.pre-courses.bak`, then adds course references without deleting existing records. It derives courses from existing class course names and matches department names case-insensitively where possible. A subject's course is inferred only when all its existing assignments point to one course. Ambiguous or unassigned legacy subjects remain unlinked until edited. Generation flags old assignments whose subject course or teacher department is incompatible; it does not silently reassign teachers.

## App workflow and features

1. Add courses and their departments, then classrooms, teachers, classes and subjects. Every management form sits above its record table. Pages include add, edit, search, filtering and deletion with a dependency-impact report. IDs are immutable during edits. Subject room-type dropdowns contain only types present in Classrooms, with the same rule enforced by the backend.
2. Define workload on Assignments. Select a course first: the class and subject dropdowns show only that course's records, and the teacher dropdown shows only its department's teachers. JavaScript rebuilds dependent option lists and clears incompatible choices. Server validation enforces the same constraints even if JavaScript is bypassed. Assignments can be edited, deleted, filtered and summarized by class workload.
3. Configure days, number of periods, start time, period duration and the consecutive-subject limit in Settings. Add or remove named break rows with their own start and end times, including zero breaks if desired.
4. Open Timetable. Its **Generate new timetable?** panel includes setup issues, status, settings access and the generation button. The separate Generate navigation item has been removed; older `/generate` GET links redirect to Timetable.
5. View the schedule by class, teacher or room. Days are rows and time slots are columns, with separate labeled break columns. Print / Save PDF uses the browser's print dialog and a landscape table layout.

The dashboard is a resource directory with counts and actual classroom, teacher, subject, class and course lists, each showing up to eight records and a View all control. Generation controls belong exclusively to Timetable.

## Generator design

The generator uses constraint search with backtracking. At each step it selects an assignment with the fewest currently available room/slot combinations. It tries compatible placements, undoing previous decisions when a branch cannot satisfy all remaining periods. Occupancy maps check class, teacher, and room conflicts. Room lists enforce capacity and exact room type. Candidate ordering prefers spreading subjects across days and using smaller suitable rooms; these are preferences rather than guarantees of a globally optimal schedule.

Repeated sessions of one assignment use increasing slot indices to avoid exploring different permutations of the same result. An explicit search stack avoids recursion-depth failures. A 10-second/100,000-placement budget bounds search; reaching that limit reports uncertainty rather than incorrectly claiming no feasible solution exists. Exhausting all candidates is reported separately.

The consecutive limit measures adjacent periods of the same subject within a class and day, including sessions assigned to different teachers. A free period, different subject, or lunch break separates runs. It is not a daily subject-period quota. Thus three nonconsecutive periods in one day can be allowed with a consecutive limit of one.

Before storage, an independent validator checks exact assignment counts, allowed time slots, all resource conflicts, suitable rooms, and consecutive limits.

Generation begins an immediate SQLite transaction and rechecks source inputs while holding the write reservation, so another write cannot invalidate the inputs before saving. It builds and validates the new schedule in memory before deleting anything. On success, replacement, status, generation timestamp, and a snapshot of the entire slot grid commit together. Any solver or database failure rolls back the transaction, preserving the old schedule. An existing timetable requires an explicit confirmation checkbox which is also enforced on the server.

The snapshot keeps free periods, working days and break labels visible after settings changes. Older databases without a snapshot fall back to stored schedule times and infer generic breaks from gaps. Source changes mark saved timetables **Outdated**. The Timetable page also distinguishes **Not Generated**, **Generated**, and **Generation Failed** (when there is no previous schedule). Failure of a later attempt does not invalidate a still-current saved timetable; the error is shown separately.

Multiple daily breaks are stored as normalized JSON in the settings table. The slot builder sorts them and skips every intersecting break when seeking the next full teaching period. Breaks do not count toward the teaching-period total. If a break intersects a potential period, the whole period starts after the break instead of being shortened. Names, valid times, end-after-start ordering, non-overlap and a maximum of 12 breaks are validated. The earlier lunch-only settings remain supported for migration and older callers. Current forms submit the full break list, and generated timetables save a separate break snapshot.

## UI design decisions

The interface uses a flat dark palette, consistent spacing, thin borders and a restrained indigo accent. The sidebar groups Workspace, Academic Data and Scheduling, uses inline SVG icons, marks the active page, and becomes a dismissible drawer on mobile. Shared Jinja macros provide icons, form controls, CSRF tokens and the course-dependent assignment form. Primary, secondary, ghost and danger buttons share height, padding and alignment rules; compact Edit/Delete buttons are grouped at the right of each table row. Forms use multiple columns internally on desktop, but their panels always sit above the full-width table.

The print stylesheet removes navigation, filters and action panels, applies A4 landscape with 12 mm margins, and renders a fully bordered day/time matrix. It uses a white background, legible dark type, lightly shaded break cells, repeated table headers and row-break avoidance. Printed title, schedule type, generation date and status identify the selected schedule. PDF output is generated using the browser's Save as PDF option, so the application requires no PDF-generation dependency at runtime.

## Validation and security

Numeric inputs are validated on the server before SQLite receives them; SQLite's flexible typing alone would otherwise allow some invalid text values in integer columns. Classroom room types must be supported; subject room types must additionally exist in the classroom inventory. Course IDs must exist and teacher departments must be defined by a course. Working days must be unique canonical weekday names. Settings enforce positive bounded period counts, duration and consecutive limits, non-overlapping ordered breaks, and a schedule that ends before midnight. Malformed settings are rejected without replacing valid stored settings.

All modifying requests require a session CSRF token. Jinja escapes displayed content, SQL values use placeholders, and dynamic SQL identifiers come only from application-owned metadata. Deletes use POST, clear child references, and report the affected tables. Expected validation failures show useful messages without exposing SQL internals. Debug mode is off by default. `TIMETABLE_SECRET` can provide a stable secret for deployment; without it a random process secret means sessions expire on restart. This remains a local administrative application without user authentication; access control is a separate deployment feature.

## Verification

Run `.venv/bin/python -m unittest discover -s tests -v`. Tests use disposable databases inside the project directory and never mutate the application's persistent database. Coverage includes fresh initialization, page rendering, form tokens, numeric and room-type validation, invalid settings preservation, CRUD dependency handling, editing, schedule generation and filtered views, persistence across clients, explicit replacement confirmation, solver failures, database insertion rollback, stale schedule display, lunch handling, consecutive-period semantics, room selection, bounded failure, and independent output validation. The database-failure test uses a rejecting SQLite trigger after an initial valid timetable is saved, proving that failed replacement restores the original rows.

The regression suite additionally tests the migration backup and preservation of legacy records, course/department mismatch rejection, subject room-type availability, multiple breaks, break-overlap rejection, grid orientation and dashboard/navigation changes. Optional `tests/browser_smoke.py` uses Playwright and a temporary local server/database to verify stacked panels, real course-dependent dropdown behavior, adding/removing breaks, generation, mobile navigation, viewport overflow, PDF table borders and JavaScript errors. It writes desktop/mobile screenshots and a sample PDF into `artifacts/`. Playwright is a development-only dependency; the running app still requires only Flask.

## Timetable lifecycle and GitHub preparation

The Timetable page provides a confirmed Delete timetable action for the entire saved schedule, across all classes, teachers and rooms. The POST endpoint requires the application's CSRF token. Deletion runs in a transaction, removes saved periods and generation metadata (timestamp, slots and breaks), and resets the status to Not Generated. Academic records, assignments and schedule configuration are retained. A database failure rolls back the deletion.

Generation is disabled in the interface and rejected by server validation whenever source records, assignments or saved timetable periods have missing references. The server repeats validation inside the generation transaction. Damaged generated periods cannot be edited directly: repair source records and assignments, delete the damaged saved timetable, then generate again. Validation covers incomplete source records even if they are not used by an assignment.

Navigation places Overview first without a group caption, Timetable within Academic Data, and Schedule Configuration as a separate sidebar entry. The existing /settings URL remains compatible.

The .gitignore excludes Python environments and caches, browser downloads, generated screenshots/PDFs, database files and migration backups, local secrets and editor settings, build/test output, and README.md as requested. Local data and the existing README are preserved on disk. The application creates the database directory on startup, so an empty database file is unnecessary in a checkout. ProjectReport.md, the specification, application source, templates, static assets, dependency list and tests remain suitable for version control. No GitHub remote or publication is configured.

Regression coverage includes deletion metadata cleanup, preservation of academic records, CSRF enforcement, rejection of GET deletion, generation after deletion, and rejection of incomplete unused source records. The browser smoke test exercises deletion of a damaged timetable followed by successful regeneration.

## Limitations and extension points

Dense problems may reach the search budget even when feasible. A dedicated constraint solver would improve scalability. There is no claim of globally optimal teacher gaps, room utilization, or subject distribution. Teacher availability, mandatory double-period practical sessions, pagination, authentication, schedule history, and CSV import/export remain possible extensions. SQLite and synchronous bounded generation suit a small departmental application; background jobs and a larger database would be appropriate for heavy concurrent use. Timetable master-data names are resolved from current records rather than archived, with source edits explicitly marking the timetable outdated.

## Deletion and repair workflow

Schema version 2 rebuilds the affected SQLite tables because SQLite cannot directly remove a NOT NULL constraint or change a foreign-key delete action. The migration first backs up an existing database to `database/timetable.pre-null-deletes.bak`. It copies rows without changing IDs, restores custom indexes and triggers, preserves autoincrement high-water marks, checks foreign-key integrity, and commits the schema change atomically. Foreign-key enforcement is temporarily disabled only on the migration connection and restored afterward.

Deletion and its dependency changes execute in one immediate transaction. Before deleting, the service counts direct references by table and field. The database then clears foreign keys automatically. Application-managed relationships need two additional rules: deleting the last course for a department clears that department on teachers; deleting the last classroom of a room type clears the corresponding subject room requirements. Shared departments and room types remain intact while another parent provides them. Grandchild rows are retained without unnecessarily clearing references to parents that still exist.

The UI displays a green deletion-success message and, when references changed, a separate red table showing every affected table, changed field, row count and repair link. Unreferenced deletions show only success. A failed database operation rolls back the parent deletion and every NULL update, and does not show a success notice. Deleting an already-missing record returns 404.

Master-data pages and Assignments persistently identify incomplete records and offer a needs-repair filter. Assignment queries use LEFT JOIN so missing teachers, classes and subjects do not make the remaining rows disappear. Edit forms continue to open for these rows; repairing them requires valid replacement selections. The timetable retains its saved periods, displays missing values explicitly, and lists all incomplete periods separately, even when their class was deleted. Timetable rows are generated data: repair the source records and assignments, delete the damaged timetable, then generate again. Creating a new parent with the same identifier does not automatically reattach old NULL references.

Generation refuses incomplete assignments or source records rather than silently omitting them. New and edited records still require valid selections; nullable columns are an intentional temporary repair state after deletion, not permission to create incomplete new records.

Regression tests cover parent deletion for teachers, classes, subjects, courses and classrooms; multi-table notices; shared department/room-type behavior; edit-and-regenerate recovery; failed-deletion rollback; foreign-key behavior outside the HTTP route; and migration preservation of rows, IDs, indexes, triggers and sequence values. Browser verification additionally deletes a teacher, checks both colored notices, repairs the retained assignment with a replacement teacher, deletes the damaged timetable and generates again.
