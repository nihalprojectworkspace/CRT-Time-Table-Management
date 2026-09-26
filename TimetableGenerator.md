# Classroom Timetable Management System

## Project Overview

The **Classroom Timetable Management System** is a web-based application for creating, generating, storing, and viewing academic timetables for a college or department.

The application is built using **Python, Flask, SQLite, HTML5, CSS3, and JavaScript**. Its main purpose is to reduce the manual work involved in timetable preparation by collecting structured information about classrooms, teachers, classes, subjects, and teaching assignments, and then using that information to automatically generate a valid timetable.

The system should prevent common timetable conflicts such as:

- The same teacher being assigned to two classes at the same time.
- The same classroom being assigned to two classes at the same time.
- A class receiving two subjects during the same time slot.
- A classroom being assigned when its capacity is lower than the class strength.
- A subject being scheduled in an unsuitable room type.
- A subject receiving fewer or more periods than its required weekly hours.
- A teacher being assigned to a subject or class that has not been assigned to them.

The application should use a **professional flat dark-theme interface** with a clean dashboard, simple navigation, responsive tables, modern forms, clear status indicators, and minimal visual clutter.

---

# 1. Main Objectives

The system should provide a complete workflow for timetable preparation.

The administrator first enters all available classrooms, then teachers, classes, subjects, and subject assignments. Once the required information is available, the system generates the timetable automatically and stores the generated schedule in the database.

The intended workflow is:

```text
Classrooms
    ↓
Teachers
    ↓
Classes
    ↓
Subjects
    ↓
Subject Assignments
    ↓
Timetable Generation
    ↓
Validation
    ↓
Timetable Storage
    ↓
View / Filter / Print Timetable
```

The system should be designed so that every stage depends on information created in the previous stages. This prevents incomplete or invalid timetable generation.

---

# 2. Technology Stack

## Backend

### Python

Python is the primary programming language used for the backend application.

Python is responsible for:

- Application logic.
- Timetable-generation logic.
- Database communication.
- Data validation.
- Conflict detection.
- Processing form submissions.
- Handling Flask routes.
- Preparing data for HTML templates.
- Saving generated timetable entries.

### Flask

Flask is used as the web application framework.

Flask should handle:

- Page routing.
- Form submissions.
- CRUD operations.
- Database queries.
- Timetable generation requests.
- Validation messages.
- Rendering Jinja2 templates.
- JSON endpoints where JavaScript needs asynchronous data.

Recommended Flask structure:

```text
app.py
routes/
services/
models/
templates/
static/
database/
```

For a smaller academic project, the application may initially use a single `app.py`, but separating timetable-generation logic and database operations into their own modules is recommended.

---

## Frontend

### HTML5

HTML provides the structure of all application pages, including:

- Dashboard.
- Forms.
- Tables.
- Navigation.
- Timetable grid.
- Confirmation dialogs.
- Empty-state messages.
- Summary cards.

### CSS3

CSS is responsible for the visual design.

The application should follow a **flat professional dark-theme design** rather than a highly decorative interface.

The UI should focus on:

- Strong hierarchy.
- Consistent spacing.
- Flat cards.
- Thin borders.
- Clean typography.
- Subtle hover states.
- Clear form controls.
- Responsive layouts.
- Professional timetable presentation.

### JavaScript

JavaScript should be used for client-side interactions such as:

- Form validation.
- Delete confirmations.
- Dynamic dropdown updates.
- Filtering tables.
- Search functionality.
- Loading indicators.
- Timetable generation progress.
- Confirmation dialogs.
- Toast notifications.
- Optional AJAX requests.
- Dynamic subject-assignment forms.

JavaScript should enhance the interface but should not contain critical business logic that must be protected from invalid data. Important validation must also occur on the Flask backend.

---

## Database

### SQLite

SQLite is suitable for this project because it:

- Requires no separate database server.
- Is easy to configure.
- Works directly with Python.
- Is appropriate for a student project or departmental application.
- Supports relational tables, foreign keys, indexes, and constraints.
- Can later be replaced with PostgreSQL or MySQL with limited architectural changes if an ORM is used.

Recommended database file:

```text
database/timetable.db
```

SQLite foreign-key enforcement should be enabled.

---

## Optional Libraries

The application can use the following libraries:

```text
Flask
Flask-SQLAlchemy
Flask-WTF
WTForms
```

`Flask-SQLAlchemy` is recommended because it makes relational database operations easier and produces cleaner application code.

If the project is intentionally kept simple, Python's built-in `sqlite3` module can also be used.

---

# 3. Database Design

The system should contain six primary tables:

```text
Teachers
Classrooms
Classes
Subjects
Subject_Assignments
Timetable
```

An optional seventh table, `Teacher_Availability`, can be added later.

The database should be relational. IDs should be used to connect tables instead of repeatedly storing names.

---

# 4. Teachers Table

The `Teachers` table stores information about faculty members.

## Fields

| Field | Type | Description |
|---|---|---|
| teacher_id | INTEGER / TEXT | Unique identifier for the teacher |
| name | TEXT | Full name of the teacher |
| department | TEXT | Department to which the teacher belongs |

Example:

| teacher_id | name | department |
|---|---|---|
| T001 | Ravi Kumar | Computer Science |
| T002 | Ananya Rao | Computer Science |
| T003 | Meera S | Mathematics |

## Important Rules

- Every teacher must have a unique ID.
- Teacher name is stored only in this table.
- Other tables should refer to a teacher using `teacher_id`.
- A teacher should not be deleted if active subject assignments depend on that teacher unless the dependent records are first reassigned or removed.

---

# 5. Classrooms Table

The `Classrooms` table stores all rooms that can be used when generating the timetable.

## Fields

| Field | Type | Description |
|---|---|---|
| classroom_no | TEXT | Unique classroom or room number |
| capacity | INTEGER | Maximum number of students that can use the room |
| room_type | TEXT | Type of classroom |

Recommended room types:

```text
Lecture Room
Computer Lab
Science Lab
Seminar Hall
Auditorium
```

Example:

| classroom_no | capacity | room_type |
|---|---:|---|
| 301 | 60 | Lecture Room |
| Lab-1 | 40 | Computer Lab |
| Seminar-2 | 80 | Seminar Hall |

## Important Rules

- Classroom number must be unique.
- Capacity must be greater than zero.
- The timetable generator must never assign a room whose capacity is below the class strength.
- Room type must be compatible with the subject requirement.
- One classroom cannot host multiple classes during the same period.

---

# 6. Classes Table

The `Classes` table represents student groups for which timetables are generated.

## Fields

| Field | Type | Description |
|---|---|---|
| class_id | TEXT | Unique identifier for the class |
| course_name | TEXT | Course name |
| semester | INTEGER / TEXT | Semester |
| section | TEXT | Section |
| strength | INTEGER | Number of students |

Example:

| class_id | course_name | semester | section | strength |
|---|---|---:|---|---:|
| BCA5A | BCA | 5 | A | 55 |
| BCA5B | BCA | 5 | B | 48 |
| BCA3A | BCA | 3 | A | 58 |

## Important Rules

- Every class must have a unique `class_id`.
- Strength must be greater than zero.
- Strength is used when selecting a valid classroom.
- Semester and section should be stored separately so that classes can be filtered easily.

---

# 7. Subjects Table

The `Subjects` table stores master information about academic subjects.

## Fields

| Field | Type | Description |
|---|---|---|
| subject_id | TEXT | Unique subject identifier |
| subject_name | TEXT | Name of the subject |
| required_room_type | TEXT | Type of room required by the subject |

Example:

| subject_id | subject_name | required_room_type |
|---|---|---|
| CS501 | Python Programming | Computer Lab |
| CS502 | Web Technology | Lecture Room |
| CS503 | Data Analytics | Lecture Room |

## Why Class ID Is Not Stored Here

A subject may be taught to more than one class.

For example:

```text
Python Programming
    ├── BCA5A
    └── BCA5B
```

Storing multiple class IDs inside the `Subjects` table would violate good relational database design and would make queries difficult.

The relationship between classes, subjects, and teachers is therefore stored in the `Subject_Assignments` table.

---

# 8. Subject Assignments Table

The `Subject_Assignments` table is one of the most important tables in the system.

It defines:

> Which teacher teaches which subject to which class, and how many hours per week the subject must be scheduled.

## Fields

| Field | Type | Description |
|---|---|---|
| assignment_id | INTEGER | Unique assignment identifier |
| class_id | FOREIGN KEY | Class receiving the subject |
| subject_id | FOREIGN KEY | Subject being taught |
| teacher_id | FOREIGN KEY | Teacher responsible for the subject |
| weekly_hours | INTEGER | Required number of timetable periods per week |

Example:

| assignment_id | class_id | subject_id | teacher_id | weekly_hours |
|---:|---|---|---|---:|
| 1 | BCA5A | CS501 | T001 | 4 |
| 2 | BCA5A | CS502 | T002 | 3 |
| 3 | BCA5A | CS503 | T003 | 4 |
| 4 | BCA5B | CS501 | T004 | 4 |

## Important Rules

- The selected class must already exist.
- The selected subject must already exist.
- The selected teacher must already exist.
- `weekly_hours` must be greater than zero.
- Duplicate assignments should be prevented.
- A class-subject-teacher combination should normally appear only once.
- The timetable generator should use this table as its primary workload input.

---

# 9. Timetable Table

The `Timetable` table contains the final schedule produced by the system.

Unlike the previous tables, this table is primarily created by the timetable-generation algorithm.

## Fields

| Field | Type | Description |
|---|---|---|
| timetable_id | INTEGER | Unique timetable entry |
| class_id | FOREIGN KEY | Class for which the period is scheduled |
| day | TEXT | Day of the week |
| start_time | TIME / TEXT | Period start time |
| end_time | TIME / TEXT | Period end time |
| subject_id | FOREIGN KEY | Scheduled subject |
| teacher_id | FOREIGN KEY | Assigned teacher |
| classroom_no | FOREIGN KEY | Assigned classroom |

Example:

| timetable_id | class_id | day | start_time | end_time | subject_id | teacher_id | classroom_no |
|---:|---|---|---|---|---|---|---|
| 1 | BCA5A | Monday | 09:00 | 10:00 | CS501 | T001 | Lab-1 |
| 2 | BCA5A | Monday | 10:00 | 11:00 | CS502 | T002 | 301 |
| 3 | BCA5B | Monday | 09:00 | 10:00 | CS503 | T003 | 302 |

---

# 10. Database Relationships

The database relationships can be visualized as follows:

```text
Teachers
   │
   │ teacher_id
   │
   ▼
Subject_Assignments
   ▲        ▲
   │        │
class_id    │ subject_id
   │        │
Classes   Subjects

         │
         │ timetable generation
         ▼

      Timetable
       ▲   ▲
       │   │
       │   └──────── Classrooms
       │
       └──────── Teachers / Subjects / Classes
```

The core idea is that `Subject_Assignments` describes what must be taught, while `Timetable` describes when and where it will be taught.

---

# 11. Recommended Database Constraints

The database should enforce as many correctness rules as possible.

Recommended constraints include:

```text
Teachers.teacher_id UNIQUE
Classrooms.classroom_no UNIQUE
Classes.class_id UNIQUE
Subjects.subject_id UNIQUE
Subject_Assignments.assignment_id PRIMARY KEY
Timetable.timetable_id PRIMARY KEY
```

Foreign keys should connect:

```text
Subject_Assignments.class_id      → Classes.class_id
Subject_Assignments.subject_id    → Subjects.subject_id
Subject_Assignments.teacher_id    → Teachers.teacher_id

Timetable.class_id                → Classes.class_id
Timetable.subject_id              → Subjects.subject_id
Timetable.teacher_id              → Teachers.teacher_id
Timetable.classroom_no            → Classrooms.classroom_no
```

The application should additionally check for timetable conflicts before inserting timetable rows.

---

# 12. Application Working Flow

The system should guide the user through a fixed data-entry sequence.

## Step 1 — Enter Classrooms

The administrator first creates all available classrooms.

The form should contain:

```text
Classroom Number
Capacity
Room Type
```

The classroom management page should allow:

- Add classroom.
- View classrooms.
- Edit classroom.
- Delete classroom.
- Search classroom.
- Filter by room type.

The dashboard should show the number of available classrooms.

Example:

```text
Total Classrooms: 12
Lecture Rooms: 8
Computer Labs: 3
Seminar Halls: 1
```

This data must be entered first because the timetable generator needs to know what physical rooms are available.

---

# 13. Step 2 — Enter Teachers

The administrator enters all teachers.

Form fields:

```text
Teacher ID
Teacher Name
Department
```

The teacher page should support:

- Add teacher.
- Edit teacher.
- Delete teacher.
- Search teacher.
- Filter by department.
- View assigned subjects.

A teacher detail page can optionally display all subject assignments for that teacher.

---

# 14. Step 3 — Enter Classes

The administrator creates the student classes.

Form fields:

```text
Class ID
Course Name
Semester
Section
Strength
```

Example:

```text
Class ID: BCA5A
Course: BCA
Semester: 5
Section: A
Strength: 55
```

Before timetable generation, every active class must have at least one subject assignment.

---

# 15. Step 4 — Enter Subjects

The administrator enters subjects into the subject master table.

Form fields:

```text
Subject ID
Subject Name
Required Room Type
```

Example:

```text
Subject ID: CS501
Subject Name: Python Programming
Required Room Type: Computer Lab
```

The subject page should allow:

- Add subject.
- Edit subject.
- Delete subject.
- Search subject.
- Filter by room requirement.

---

# 16. Step 5 — Create Subject Assignments

After classrooms, teachers, classes, and subjects have been entered, the administrator defines the teaching assignments.

The form should contain dropdowns:

```text
Class
Subject
Teacher
Weekly Hours
```

For example:

```text
Class: BCA5A
Subject: Python Programming
Teacher: Ravi Kumar
Weekly Hours: 4
```

When the form is saved, the application stores the corresponding IDs rather than duplicate names.

For example:

```text
class_id   = BCA5A
subject_id = CS501
teacher_id = T001
weekly_hours = 4
```

The assignment page should display a readable version:

```text
BCA5A | Python Programming | Ravi Kumar | 4 Hours/Week
```

The page should support:

- Add assignment.
- Edit assignment.
- Delete assignment.
- Filter by class.
- Filter by teacher.
- Filter by subject.
- Show total weekly hours for each class.

---

# 17. Step 6 — Timetable Generation

Once all required information is available, the administrator opens the **Generate Timetable** page.

The page should show a pre-generation summary.

Example:

```text
Classrooms: 12
Teachers: 18
Classes: 6
Subjects: 24
Subject Assignments: 32
```

The system should perform validation before generation.

Examples of validation errors:

```text
BCA5A has no subject assignments.

CS501 requires a Computer Lab but no Computer Lab exists.

BCA5A has 42 required weekly periods but only 35 timetable slots are available.

Teacher T004 does not exist.

No classroom has sufficient capacity for BCA5B.
```

The **Generate Timetable** button should remain disabled or display a clear error until blocking problems are resolved.

---

# 18. Timetable Configuration

The application should have timetable-generation settings.

Recommended settings:

```text
Working Days
Periods Per Day
Day Start Time
Period Duration
Lunch Break Start
Lunch Break End
Maximum Consecutive Periods for Same Subject
```

Example:

```text
Working Days:
Monday
Tuesday
Wednesday
Thursday
Friday
Saturday

Day Start: 09:00

Period Duration: 60 minutes

Lunch Break:
13:00 - 14:00
```

The system converts these settings into available scheduling slots.

Example:

```text
Monday
09:00 - 10:00
10:00 - 11:00
11:00 - 12:00
12:00 - 13:00
14:00 - 15:00
15:00 - 16:00
```

---

# 19. Timetable Generation Logic

The timetable generator should generate schedules using the `Subject_Assignments` table.

For each class:

1. Read all subject assignments.
2. Determine how many weekly periods each subject requires.
3. Create a pool of required sessions.
4. Find available day/time slots.
5. Check teacher availability.
6. Check classroom availability.
7. Check classroom capacity.
8. Check required room type.
9. Place the subject into a valid slot.
10. Continue until all required weekly periods are scheduled.
11. Validate the completed timetable.
12. Store the timetable.

---

# 20. Core Conflict Rules

Before placing any timetable entry, the algorithm must verify all required constraints.

## Teacher Conflict

A teacher cannot teach two classes at the same time.

Invalid example:

```text
Monday 09:00 - 10:00

BCA5A → CS501 → T001
BCA3A → CS302 → T001
```

The second assignment must be rejected.

---

## Class Conflict

A class cannot have two subjects at the same time.

Invalid:

```text
BCA5A
Monday 10:00 - 11:00

Python Programming
Web Technology
```

Only one can occupy the slot.

---

## Classroom Conflict

A classroom cannot be used by two classes at the same time.

Invalid:

```text
Room 301
Monday 11:00 - 12:00

BCA5A
BCA3A
```

---

## Classroom Capacity

The selected classroom must satisfy:

```text
class_strength <= classroom_capacity
```

If:

```text
BCA5A Strength = 55
Room 203 Capacity = 40
```

Room 203 cannot be assigned.

---

## Room Type

The room must satisfy the subject's required room type.

Example:

```text
Python Programming
Required Room Type: Computer Lab
```

It should not be assigned to an ordinary lecture room.

---

## Weekly Hours

If:

```text
Python Programming
Weekly Hours = 4
```

the final timetable must contain exactly four periods for that assignment.

---

# 21. Recommended Scheduling Strategy

For an academic project, a **constraint-based greedy scheduling algorithm with backtracking** is appropriate.

A practical implementation can work as follows:

```text
Load all subject assignments.

Sort assignments by difficulty.

Schedule the most restricted assignments first.

For every required weekly period:
    Find candidate time slots.
    Find compatible classrooms.
    Check teacher conflict.
    Check class conflict.
    Check room conflict.
    Check capacity.
    Check room type.
    Place the session.

If no valid slot exists:
    Backtrack and try an alternative placement.
```

Assignments that are difficult to schedule should be processed first.

Examples:

- Lab subjects.
- Teachers with many assigned classes.
- Classes with high weekly-hour requirements.
- Subjects requiring rare classroom types.

This reduces the probability of reaching an impossible timetable late in the generation process.

---

# 22. Avoiding Poor Timetables

A technically conflict-free timetable can still be inconvenient.

The generator should therefore attempt to improve timetable quality.

Recommended soft rules:

- Avoid placing the same subject in too many consecutive periods.
- Spread high-hour subjects across multiple days.
- Avoid unnecessary teacher gaps.
- Avoid excessive empty periods for a class.
- Prefer using appropriately sized rooms.
- Avoid repeatedly scheduling the same subject as the first or last class every day.
- Avoid scheduling practical subjects into isolated single periods if a double period is required.

These should be treated as preferences rather than strict rules unless the project specifically requires them.

---

# 23. Timetable Storage

After generation succeeds, the final timetable should be written to the `Timetable` table.

Example generated data:

```text
TT001 | BCA5A | Monday | 09:00 | 10:00 | CS501 | T001 | Lab-1
TT002 | BCA5A | Monday | 10:00 | 11:00 | CS502 | T002 | 301
TT003 | BCA5B | Monday | 09:00 | 10:00 | CS503 | T003 | 302
```

Timetable data should not exist only in Python memory.

It must be stored so that the application can:

- Display it later.
- Filter it.
- Print it.
- Reload it after restart.
- Generate teacher schedules.
- Generate classroom schedules.

---

# 24. Regenerating a Timetable

The system should not silently overwrite an existing timetable.

If timetable records already exist, clicking **Generate Timetable** should display a confirmation dialog such as:

```text
A generated timetable already exists.

Generating a new timetable will replace the current schedule.

[Cancel] [Regenerate]
```

A safe implementation should:

1. Generate the new schedule in memory.
2. Validate the complete result.
3. Begin a database transaction.
4. Delete the previous generated timetable.
5. Insert the new timetable.
6. Commit only if every insert succeeds.
7. Roll back if any error occurs.

This prevents the database from being left with an incomplete timetable.

---

# 25. Viewing the Timetable

The timetable page should provide multiple views.

## Class View

The user selects:

```text
BCA → Semester 5 → Section A
```

The timetable displays as a weekly grid.

Example:

| Time | Monday | Tuesday | Wednesday | Thursday | Friday |
|---|---|---|---|---|---|
| 09:00 | Python | Web Tech | Data Analytics | Python | Web Tech |
| 10:00 | Data Analytics | Python | Web Tech | Data Analytics | Python |
| 11:00 | Web Tech | Data Analytics | Python | Web Tech | Data Analytics |

Each cell can display:

```text
Subject
Teacher
Room
```

Example:

```text
Python Programming
Ravi Kumar
Lab-1
```

---

## Teacher View

The user selects a teacher.

The application displays only that teacher's periods.

This helps faculty members quickly view their personal schedule.

---

## Classroom View

The user selects a classroom.

The application displays when that classroom is occupied and by which class.

This is useful for finding free rooms.

---

# 26. Dashboard

The dashboard should provide an immediate overview of the system.

Recommended summary cards:

```text
Total Teachers
Total Classrooms
Total Classes
Total Subjects
Total Assignments
Scheduled Periods
```

Additional dashboard sections can include:

```text
Recently Added Teachers
Recently Added Subjects
Classes Without Assignments
Timetable Generation Status
```

Example generation status:

```text
Timetable Status

Generated
Last Generated: 24 September 2026, 6:45 PM
Total Scheduled Periods: 184
Conflicts: 0
```

---

# 27. Professional Flat Dark UI Design

The application should look like a modern administrative dashboard rather than a basic student HTML project.

The visual design should follow a **flat dark-theme system**.

## Design Principles

Use:

- Large clean surfaces.
- Minimal shadows.
- Thin borders.
- Consistent spacing.
- Rounded corners used moderately.
- Strong text contrast.
- Muted secondary text.
- One primary accent color.
- Consistent button styling.
- Clear table headers.
- Simple icons.
- Responsive layouts.

Avoid:

- Gradients everywhere.
- Glossy buttons.
- Excessive shadows.
- Neon colors.
- Overly rounded components.
- Unnecessary animations.
- Decorative backgrounds that reduce readability.

---

# 28. Recommended Dark Theme

Example design tokens:

```css
:root {
    --bg-primary: #0f1115;
    --bg-secondary: #151820;
    --surface: #1b1f28;
    --surface-hover: #222733;

    --border: #2a303b;

    --text-primary: #f4f6f8;
    --text-secondary: #aeb6c2;
    --text-muted: #737d8c;

    --accent: #6c7cff;
    --accent-hover: #7e8cff;

    --success: #43b581;
    --warning: #e3a83b;
    --danger: #e05a63;
}
```

The exact colors can be adjusted, but the entire application should use a consistent design system rather than page-specific colors.

---

# 29. Typography

Use a professional sans-serif typeface such as:

```text
Inter
Roboto
Manrope
System UI
```

Recommended hierarchy:

```text
Page Title        28–32px
Section Heading   20–24px
Card Title        16–18px
Body              14–16px
Table Text        14px
Helper Text       12–13px
```

Use font weight and spacing to create hierarchy rather than excessive colors.

---

# 30. Application Layout

Recommended desktop layout:

```text
┌──────────────────────────────────────────────────────────────┐
│ Sidebar                     Main Content                     │
│                                                              │
│ Dashboard                   Page Header                      │
│ Classrooms                  ───────────────────────────────  │
│ Teachers                    Content                          │
│ Classes                                                      │
│ Subjects                                                     │
│ Assignments                                                  │
│ Generate Timetable                                           │
│ Timetable                                                    │
│ Settings                                                     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

The sidebar should stay fixed on larger displays.

On smaller screens, it should collapse into a menu button.

---

# 31. Sidebar Navigation

Recommended items:

```text
Dashboard
Classrooms
Teachers
Classes
Subjects
Subject Assignments
Generate Timetable
Timetable
Settings
```

The current page should be visibly highlighted.

Icons can be provided using:

- Font Awesome.
- Bootstrap Icons.
- Lucide Icons.

---

# 32. Forms

Forms should use a clean card layout.

Example:

```text
Add Classroom

Classroom Number
[________________]

Capacity
[________________]

Room Type
[ Lecture Room ▼ ]

                         [Cancel] [Save Classroom]
```

Required features:

- Visible field labels.
- Helpful placeholders.
- Required-field indicators.
- Inline validation.
- Disabled submit state while processing.
- Server-side error messages.
- Clear success message after saving.

Do not rely only on placeholders as labels.

---

# 33. Tables

Database management pages should use consistent data tables.

Example:

```text
Teachers

[Search teachers...]          [Department ▼]   [+ Add Teacher]

┌───────┬──────────────────┬────────────────────┬────────────┐
│ ID    │ Name             │ Department         │ Actions    │
├───────┼──────────────────┼────────────────────┼────────────┤
│ T001  │ Ravi Kumar       │ Computer Science   │ Edit Delete│
│ T002  │ Ananya Rao       │ Computer Science   │ Edit Delete│
└───────┴──────────────────┴────────────────────┴────────────┘
```

Tables should support:

- Search.
- Filtering.
- Empty states.
- Responsive overflow.
- Edit actions.
- Delete actions.
- Optional pagination when records grow.

---

# 34. Buttons

Use a small number of standardized button styles.

```text
Primary
Secondary
Danger
Icon Button
```

Examples:

```text
Save Classroom
Generate Timetable
Edit
Delete
Cancel
```

Destructive actions should never look identical to ordinary actions.

---

# 35. Notifications

Use toast notifications or compact alerts.

Examples:

```text
✓ Teacher added successfully.

✓ Timetable generated successfully.

⚠ BCA5A has no subject assignments.

✕ Unable to generate timetable because no compatible classroom is available.
```

Notifications should provide useful information instead of generic messages such as "Error occurred."

---

# 36. Confirmation Dialogs

Important actions should require confirmation.

Examples:

```text
Delete Teacher?

This teacher currently has 3 subject assignments.
Remove or reassign them before deleting the teacher.
```

and:

```text
Regenerate Timetable?

The existing generated timetable will be replaced.

[Cancel] [Regenerate]
```

---

# 37. Suggested Flask Routes

A functional application can expose routes such as:

```text
GET  /
GET  /dashboard

GET  /classrooms
GET  /classrooms/add
POST /classrooms/add
GET  /classrooms/<id>/edit
POST /classrooms/<id>/edit
POST /classrooms/<id>/delete

GET  /teachers
GET  /teachers/add
POST /teachers/add
GET  /teachers/<id>/edit
POST /teachers/<id>/edit
POST /teachers/<id>/delete

GET  /classes
GET  /classes/add
POST /classes/add

GET  /subjects
GET  /subjects/add
POST /subjects/add

GET  /assignments
GET  /assignments/add
POST /assignments/add

GET  /timetable/generate
POST /timetable/generate

GET  /timetable
GET  /timetable/class/<class_id>
GET  /timetable/teacher/<teacher_id>
GET  /timetable/classroom/<classroom_no>
```

Routes can later be organized using Flask Blueprints.

---

# 38. Suggested Application Structure

```text
Classroom-Timetable-Management-System/
│
├── app.py
├── config.py
├── requirements.txt
├── README.md
│
├── database/
│   └── timetable.db
│
├── models/
│   ├── teacher.py
│   ├── classroom.py
│   ├── class_model.py
│   ├── subject.py
│   ├── assignment.py
│   └── timetable.py
│
├── services/
│   ├── timetable_generator.py
│   └── timetable_validator.py
│
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   │
│   ├── classrooms/
│   │   ├── list.html
│   │   └── form.html
│   │
│   ├── teachers/
│   │   ├── list.html
│   │   └── form.html
│   │
│   ├── classes/
│   │   ├── list.html
│   │   └── form.html
│   │
│   ├── subjects/
│   │   ├── list.html
│   │   └── form.html
│   │
│   ├── assignments/
│   │   ├── list.html
│   │   └── form.html
│   │
│   └── timetable/
│       ├── generate.html
│       ├── class_view.html
│       ├── teacher_view.html
│       └── classroom_view.html
│
└── static/
    ├── css/
    │   └── style.css
    │
    ├── js/
    │   ├── app.js
    │   └── timetable.js
    │
    └── icons/
```

For a smaller implementation, multiple model files may initially be combined, but keeping timetable generation in a separate service is strongly recommended.

---

# 39. Backend Validation

Every submitted form must be validated on the backend.

Examples:

## Classroom

```text
Classroom number cannot be empty.
Capacity must be a positive integer.
Room type must be selected.
```

## Teacher

```text
Teacher ID cannot be duplicated.
Name cannot be empty.
Department cannot be empty.
```

## Class

```text
Class ID must be unique.
Strength must be greater than zero.
```

## Subject Assignment

```text
Class must exist.
Subject must exist.
Teacher must exist.
Weekly hours must be positive.
Duplicate assignment must not exist.
```

Never trust browser-side validation alone.

---

# 40. Error Handling

The application should handle predictable failures gracefully.

Examples:

```text
Database unavailable
Invalid foreign key
Duplicate ID
Incomplete form
No possible timetable solution
Invalid room capacity
Missing subject assignment
```

A failed timetable-generation attempt must not destroy the currently stored valid timetable.

---

# 41. Timetable Generation Result

After generation, show a summary page.

Example:

```text
Timetable Generated Successfully

Classes Scheduled: 6
Teachers Scheduled: 18
Periods Created: 184
Classrooms Used: 10
Conflicts Detected: 0
```

Buttons:

```text
View Timetable
View by Class
View by Teacher
Regenerate
```

If generation fails, show the actual reasons.

Example:

```text
Timetable Could Not Be Generated

The following requirements could not be satisfied:

• BCA5A requires a Computer Lab for 6 periods.
• Only one Computer Lab is available.
• T003 is required for 11 overlapping assignment slots.

Modify the input data and try again.
```

---

# 42. Timetable Status

The application should clearly distinguish between:

```text
Not Generated
Generated
Outdated
Generation Failed
```

A timetable becomes **Outdated** when important source data changes after generation.

Examples:

- Teacher assignment changed.
- Classroom deleted.
- Class strength changed.
- Weekly hours changed.
- Subject room requirement changed.

The dashboard can then display:

```text
Timetable Outdated

Source data has changed since the last generation.
Regenerate the timetable to apply the latest information.
```

This is a useful professional feature because stored timetable data should not appear valid after its source configuration changes.

---

# 43. Optional Teacher Availability

A future enhancement can add:

```text
Teacher_Availability
```

Fields:

| Field | Description |
|---|---|
| availability_id | Unique record |
| teacher_id | Teacher |
| day | Weekday |
| start_time | Start |
| end_time | End |
| is_available | Availability status |

This allows the administrator to define restrictions such as:

```text
T001 unavailable Monday 09:00–11:00
T005 unavailable Friday afternoon
```

The timetable generator would then avoid those periods.

---

# 44. Security and Data Integrity

Although this is an academic project, the application should follow sensible security practices.

Recommended measures:

- Validate all server-side inputs.
- Use parameterized database operations or an ORM.
- Do not build SQL statements directly from user input.
- Enable foreign-key constraints.
- Use CSRF protection if Flask-WTF is used.
- Escape template output.
- Use POST requests for delete operations.
- Do not expose raw database errors to users.
- Keep debug mode disabled in production deployments.

---

# 45. Responsive Design

The interface should work on:

```text
Desktop
Laptop
Tablet
Mobile
```

The timetable itself may require horizontal scrolling on smaller displays because a complete weekly grid is naturally wide.

On mobile:

- Sidebar becomes a drawer.
- Forms become single-column.
- Dashboard cards stack vertically.
- Tables use horizontal scrolling.
- Timetable remains readable rather than shrinking text excessively.

---

# 46. Recommended User Experience

The application should guide the administrator through setup.

For example, the dashboard can display:

```text
System Setup

✓ Classrooms added
✓ Teachers added
✓ Classes added
✓ Subjects added
✓ Subject assignments created
○ Timetable not generated
```

If a step is incomplete, the next action should be clear.

Example:

```text
3 classes have no subject assignments.

[Review Assignments]
```

This makes the system easier to use and reduces generation errors.

---

# 47. Complete Operational Flow

The complete application flow is:

```text
START
  │
  ▼
Open Dashboard
  │
  ▼
Add Classrooms
  │
  ▼
Add Teachers
  │
  ▼
Add Classes
  │
  ▼
Add Subjects
  │
  ▼
Create Subject Assignments
  │
  ▼
Validate Input Data
  │
  ├── Invalid ──► Display Problems ──► Correct Data
  │
  ▼
Configure Working Days and Periods
  │
  ▼
Generate Timetable
  │
  ▼
Check Class Conflicts
  │
  ▼
Check Teacher Conflicts
  │
  ▼
Check Classroom Conflicts
  │
  ▼
Check Capacity and Room Type
  │
  ▼
Check Weekly Hours
  │
  ├── Generation Failed ──► Explain Unresolved Constraints
  │
  ▼
Validate Complete Timetable
  │
  ▼
Store Timetable in SQLite
  │
  ▼
Display Timetable
  │
  ├── Class View
  ├── Teacher View
  └── Classroom View
  │
  ▼
END
```

---

# 48. Minimum Functional Version

The first complete version of the project should include:

```text
Dashboard

Classroom CRUD
Teacher CRUD
Class CRUD
Subject CRUD
Subject Assignment CRUD

Timetable Settings

Automatic Timetable Generation

Conflict Checking

Timetable Database Storage

Class Timetable View
Teacher Timetable View
Classroom Timetable View

Search and Filters

Dark Responsive UI
```

A project with these features will already function as a complete timetable management application.

---

# 49. Possible Future Enhancements

After the core project is working, additional features can be added:

```text
Administrator Login
Multiple Departments
Multiple Academic Years
Teacher Availability
Manual Timetable Editing
Locked Timetable Slots
Drag-and-Drop Timetable Editing
PDF Timetable Export
Excel Export
Print View
Email Timetables
Teacher Workload Reports
Classroom Utilization Reports
Timetable Version History
Automatic Backup
PostgreSQL Deployment
REST API
```

---

# 50. Final System Concept

The application should treat the database tables as configuration data for a timetable-generation engine.

The administrator defines:

```text
WHAT rooms exist
WHO teaches
WHAT classes exist
WHAT subjects exist
WHO teaches WHAT to WHICH class
HOW MANY times each subject must occur
```

The computer then determines:

```text
WHEN each class happens
WHERE it happens
WHICH teacher is occupied
WHICH room is occupied
```

The final relationship can be summarized as:

```text
Classrooms
Teachers
Classes
Subjects
     │
     ▼
Subject Assignments
     │
     ▼
Generation Rules + Time Slots
     │
     ▼
Conflict-Aware Timetable Generator
     │
     ▼
Generated Timetable
     │
     ▼
SQLite Storage
     │
     ▼
Class / Teacher / Classroom Views
```

The finished application should feel like a compact professional academic scheduling system rather than a collection of disconnected CRUD pages. Data entry, validation, generation, storage, and timetable viewing should form one consistent workflow.
