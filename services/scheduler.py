"""Validated slot configuration and bounded constraint search, independent of Flask."""
from collections import Counter, defaultdict
import json
from datetime import datetime, timedelta
from time import monotonic

WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

def get_breaks(values):
    """Normalize multiple daily breaks, including the previous lunch-only format."""
    try:
        breaks = json.loads(values['breaks']) if 'breaks' in values else [dict(name='Lunch', start=values['lunch_start'], end=values['lunch_end'])]
        if not isinstance(breaks, list) or len(breaks) > 12:
            raise ValueError('Use at most 12 breaks per day.')
        normalized = []
        for item in breaks:
            if not isinstance(item, dict) or not all(isinstance(item.get(key), str) for key in ('name', 'start', 'end')):
                raise ValueError('Enter text for every break name, start time and end time.')
            name = item['name'].strip()
            start = datetime.strptime(item['start'], '%H:%M')
            end = datetime.strptime(item['end'], '%H:%M')
            if not name or len(name) > 60 or end <= start:
                raise ValueError('Each break needs a name and an end time after its start.')
            normalized.append(dict(name=name, start=start.strftime('%H:%M'), end=end.strftime('%H:%M')))
        normalized.sort(key=lambda item: item['start'])
        if any(a['end'] > b['start'] for a, b in zip(normalized, normalized[1:])):
            raise ValueError('Break times must not overlap.')
        return normalized
    except (KeyError, TypeError, json.JSONDecodeError):
        raise ValueError('Enter a name, start time and end time for every break.')

def build_slots(values):
    days = [day.strip() for day in values.get('days', '').split(',')]
    if not days or len(set(days)) != len(days) or any(day not in WEEKDAYS for day in days):
        raise ValueError('Working days must be unique, full weekday names separated by commas.')
    try:
        periods, duration, maximum = (int(values[key]) for key in ('periods_per_day', 'duration', 'max_consecutive'))
        start = datetime.strptime(values['start_time'], '%H:%M')
    except (ValueError, KeyError):
        raise ValueError('Enter valid times and whole numbers for periods, duration and consecutive periods.')
    if not (1 <= periods <= 24 and 1 <= duration <= 240 and 1 <= maximum <= periods):
        raise ValueError('Use 1–24 periods, 1–240 minutes, and a consecutive limit between 1 and the daily period count.')
    breaks = [(datetime.strptime(b['start'], '%H:%M'), datetime.strptime(b['end'], '%H:%M')) for b in get_breaks(values)]
    result = []
    current = start
    for _ in range(periods):
        end = current + timedelta(minutes=duration)
        for break_start, break_end in breaks:
            if current < break_end and end > break_start:
                current = break_end
                end = current + timedelta(minutes=duration)
        if end.date() != start.date():
            raise ValueError('All teaching periods must end before midnight.')
        result.extend((day, current.strftime('%H:%M'), end.strftime('%H:%M')) for day in days)
        current = end
    return result

def consecutive_ok(occupied, slot, subject, maximum, available):
    day, start, end = available[slot]
    run = 1
    cursor = start
    for index in sorted(occupied, key=lambda i: available[i][1], reverse=True):
        d, s, e = available[index]
        if d == day and e == cursor and occupied[index] == subject:
            run += 1
            cursor = s
    cursor = end
    for index in sorted(occupied, key=lambda i: available[i][1]):
        d, s, e = available[index]
        if d == day and s == cursor and occupied[index] == subject:
            run += 1
            cursor = e
    return run <= maximum

def solve(assignments, rooms, available, maximum, time_limit=10, node_limit=100000):
    """Try constrained assignments first; undo placements on dead ends.

    Identical sessions use increasing slot indices to remove permutation symmetry.
    Explicit search frames avoid Python recursion limits for larger timetables.
    """
    assignments = [dict(a) for a in assignments]
    compatible = {a['assignment_id']: sorted((r for r in rooms if r['room_type'] == a['required_room_type'] and r['capacity'] >= a['strength']), key=lambda r: r['capacity']) for a in assignments}
    remaining = {a['assignment_id']: a['weekly_hours'] for a in assignments}
    last = defaultdict(lambda: -1)
    classes, teachers, used_rooms = defaultdict(dict), set(), set()
    placed, frames = [], []
    deadline = monotonic() + time_limit
    nodes = 0

    def candidates(a):
        options = []
        daily = Counter(available[i][0] for i, subject in classes[a['class_id']].items() if subject == a['subject_id'])
        for index, (day, start, end) in enumerate(available):
            if index <= last[a['assignment_id']] or index in classes[a['class_id']] or (a['teacher_id'], index) in teachers:
                continue
            if not consecutive_ok(classes[a['class_id']], index, a['subject_id'], maximum, available):
                continue
            for room in compatible[a['assignment_id']]:
                if (room['classroom_no'], index) not in used_rooms:
                    options.append((daily[day], index, room['capacity'], room['classroom_no']))
        return sorted(options)

    while True:
        if monotonic() > deadline or nodes >= node_limit:
            raise ValueError('The scheduling search limit was reached. A solution may exist; simplify workloads or add slots/rooms and retry.')
        if not any(remaining.values()):
            return [dict(class_id=a['class_id'], subject_id=a['subject_id'], teacher_id=a['teacher_id'], classroom_no=room, day=available[index][0], start_time=available[index][1], end_time=available[index][2]) for a, index, room, _ in placed]
        best = None
        for a in assignments:
            if not remaining[a['assignment_id']]: continue
            options = candidates(a)
            if len({o[1] for o in options}) < remaining[a['assignment_id']]:
                best = (a, [])
                break
            if best is None or len(options) < len(best[1]): best = (a, options)
        frames.append([best[0], best[1], 0])
        while frames:
            a, options, next_option = frames[-1]
            if next_option < len(options):
                _, index, _, room = options[next_option]
                frames[-1][2] += 1
                nodes += 1
                placed.append((a, index, room, last[a['assignment_id']]))
                last[a['assignment_id']] = index
                remaining[a['assignment_id']] -= 1
                classes[a['class_id']][index] = a['subject_id']
                teachers.add((a['teacher_id'], index))
                used_rooms.add((room, index))
                break
            frames.pop()
            if placed:
                a, index, room, previous = placed.pop()
                remaining[a['assignment_id']] += 1
                last[a['assignment_id']] = previous
                del classes[a['class_id']][index]
                teachers.remove((a['teacher_id'], index))
                used_rooms.remove((room, index))
        else:
            raise ValueError('No valid timetable satisfies these workloads, rooms and consecutive-period constraints.')

def validate_schedule(schedule, assignments, rooms, available, maximum):
    """Independently check the complete result before replacing persistent data."""
    expected = {(a['class_id'], a['subject_id'], a['teacher_id']): a['weekly_hours'] for a in assignments}
    actual = Counter((e['class_id'], e['subject_id'], e['teacher_id']) for e in schedule)
    if actual != expected: raise ValueError('Generated workload does not match teaching assignments.')
    lookup = {(a['class_id'], a['subject_id'], a['teacher_id']): a for a in assignments}
    room_lookup = {r['classroom_no']: r for r in rooms}
    occupied, seen = defaultdict(dict), set()
    slot_lookup = {slot: i for i, slot in enumerate(available)}
    for entry in schedule:
        slot = (entry['day'], entry['start_time'], entry['end_time'])
        if slot not in slot_lookup: raise ValueError('Invalid generated time slot.')
        index = slot_lookup[slot]
        a = lookup[(entry['class_id'], entry['subject_id'], entry['teacher_id'])]
        room = room_lookup.get(entry['classroom_no'])
        if room is None or room['capacity'] < a['strength'] or room['room_type'] != a['required_room_type']:
            raise ValueError('Invalid generated room allocation.')
        for resource in ('class_id', 'teacher_id', 'classroom_no'):
            key = (resource, entry[resource], index)
            if key in seen: raise ValueError('Generated schedule contains a resource conflict.')
            seen.add(key)
        if not consecutive_ok(occupied[entry['class_id']], index, entry['subject_id'], maximum, available):
            raise ValueError('Generated schedule exceeds the consecutive-period limit.')
        occupied[entry['class_id']][index] = entry['subject_id']
