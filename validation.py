from .models import Student, Room

def validate_allocation(students, rooms, assignments, min_group_distance=1):
    issues=[]
    selected={s.student_id:s for s in students}
    room_map={r.room_id:r for r in rooms}
    seats={seat.seat_id:seat for r in rooms for seat in r.seats}
    if set(assignments) != set(selected):
        issues.append("Every selected student must be allocated exactly once.")
    if len(set(assignments.values())) != len(assignments):
        issues.append("A seat is assigned to more than one student.")
    for sid, seat_id in assignments.items():
        if seat_id not in seats:
            issues.append(f"{sid}: assigned seat does not exist."); continue
        seat=seats[seat_id]; student=selected.get(sid)
        if seat.blocked: issues.append(f"{sid}: assigned to blocked seat.")
        if seat.room_id not in room_map or not room_map[seat.room_id].available:
            issues.append(f"{sid}: assigned to unavailable room.")
        if student and student.accessibility and not seat.accessible:
            issues.append(f"{sid}: accessibility requirement not met.")
        if student and student.required_facilities and not student.required_facilities.issubset(room_map[seat.room_id].facilities):
            issues.append(f"{sid}: required room facilities missing.")
    # Check same-group adjacency independently of the solver.
    for sid, seat_id in assignments.items():
        if seat_id not in seats or sid not in selected: continue
        a=seats[seat_id]
        for oid, other_seat_id in assignments.items():
            if oid <= sid or other_seat_id not in seats or oid not in selected: continue
            b=seats[other_seat_id]
            if selected[sid].group == selected[oid].group and a.room_id==b.room_id and not(a.aisle or b.aisle):
                if abs(a.row-b.row)+abs(a.column-b.column) < max(1,min_group_distance)+1:
                    issues.append(f"Same-group adjacency: {sid} and {oid}.")
    return {"valid":not issues,"checked":8,"violations":len(issues),"issues":issues}
