"""A from-scratch CSP solver: MRV + degree, LCV, recursive backtracking and forward checking."""
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple
from .models import Student, Seat, Room

@dataclass
class SolverResult:
    success: bool
    assignments: dict
    nodes: int
    backtracks: int
    pruned_values: int
    message: str
    conflicts: list

class CSPSolver:
    def __init__(self, students: list[Student], rooms: list[Room], min_group_distance: int = 1,
                 use_lcv: bool = True, balance_rooms: bool = True):
        self.students = students
        self.rooms = {r.room_id:r for r in rooms if r.available}
        self.seats = {s.seat_id:s for r in self.rooms.values() for s in r.seats if not s.blocked}
        self.distance = max(1, int(min_group_distance))
        self.use_lcv = use_lcv
        self.balance_rooms = balance_rooms
        self.nodes = self.backtracks = self.pruned = 0
        self.conflicts = []
        self.domains = {}
        for st in students:
            self.domains[st.student_id] = [
                seat_id for seat_id, seat in self.seats.items()
                if self._eligible(st, seat)
            ]

    def _eligible(self, student, seat):
        room = self.rooms[seat.room_id]
        if student.accessibility and not seat.accessible:
            return False
        if not student.required_facilities.issubset(room.facilities):
            return False
        return True

    def _adjacent(self, a: Seat, b: Seat):
        if a.room_id != b.room_id: return False
        # Aisles interrupt adjacency. Grid distance is Manhattan distance.
        if a.aisle or b.aisle: return False
        return abs(a.row-b.row) + abs(a.column-b.column) < self.distance + 1

    def _consistent(self, sid, seat_id, assignments):
        st = next(x for x in self.students if x.student_id == sid)
        seat = self.seats[seat_id]
        for other_id, other_seat_id in assignments.items():
            other = next(x for x in self.students if x.student_id == other_id)
            if other_seat_id == seat_id: return False
            if st.group == other.group and self._adjacent(seat, self.seats[other_seat_id]):
                return False
        return True

    def _select_variable(self, unassigned, domains, assignments):
        # MRV first; degree heuristic breaks ties by number of unassigned variables
        def degree(sid):
            st = next(x for x in self.students if x.student_id == sid)
            return sum(1 for oid in unassigned if oid != sid and
                       next(x for x in self.students if x.student_id == oid).group == st.group)
        return min(unassigned, key=lambda sid: (len(domains[sid]), -degree(sid),
                    -next(x.priority for x in self.students if x.student_id == sid)))

    def _lcv_order(self, sid, values, unassigned, domains, assignments):
        def impact(value):
            seat = self.seats[value]
            st = next(x for x in self.students if x.student_id == sid)
            removed = 0
            for oid in unassigned:
                if oid == sid: continue
                ost = next(x for x in self.students if x.student_id == oid)
                for ov in domains[oid]:
                    if ov == value or (st.group == ost.group and self._adjacent(seat, self.seats[ov])):
                        removed += 1
            return removed
        return sorted(values, key=impact)

    def solve(self):
        if not self.students:
            return SolverResult(True, {}, 0, 0, 0, "No students selected.", [])
        empty = [s.student_id for s in self.students if not self.domains[s.student_id]]
        if empty:
            self.conflicts.append({"category":"Eligibility/accessibility","students":empty,
                "explanation":"One or more students have no eligible available seats.",
                "severity":"High","suggestion":"Add suitable accessible seats, facilities, or eligible rooms."})
            return self._result(False, {}, "No eligible seat domain for at least one student.")
        if len(self.students) > len(self.seats):
            self.conflicts.append({"category":"Capacity","students":[],"explanation":"Selected students exceed available unblocked seats.",
                "severity":"High","suggestion":"Add rooms or unblock seats."})
            return self._result(False, {}, "Insufficient total seat capacity.")
        # Most constrained / accessibility-priority students are naturally selected early.
        domains = {k:list(v) for k,v in self.domains.items()}
        result = self._backtrack({}, set(domains), domains)
        return self._result(result is not None, result or {},
            "Allocation found." if result is not None else "No complete assignment satisfies all hard constraints.")

    def _backtrack(self, assignments, unassigned, domains):
        if not unassigned: return dict(assignments)
        self.nodes += 1
        sid = self._select_variable(unassigned, domains, assignments)
        values = domains[sid]
        if self.use_lcv: values = self._lcv_order(sid, values, unassigned, domains, assignments)
        # Prefer less-used rooms to spread occupancy without changing hard constraints.
        if self.balance_rooms:
            usage = defaultdict(int)
            for v in assignments.values(): usage[self.seats[v].room_id] += 1
            values = sorted(values, key=lambda v: (usage[self.seats[v].room_id], v))
        for value in values:
            if not self._consistent(sid, value, assignments): continue
            assignments[sid] = value
            remaining = unassigned - {sid}
            new_domains = {k:list(v) for k,v in domains.items()}
            failed = False
            # Forward checking: remove occupied seat and same-group neighboring seats.
            st = next(x for x in self.students if x.student_id == sid)
            for oid in remaining:
                ost = next(x for x in self.students if x.student_id == oid)
                before = len(new_domains[oid])
                new_domains[oid] = [v for v in new_domains[oid]
                    if v != value and not (st.group == ost.group and self._adjacent(self.seats[value], self.seats[v]))]
                self.pruned += before-len(new_domains[oid])
                if not new_domains[oid]:
                    failed = True
                    break
            if not failed:
                answer = self._backtrack(assignments, remaining, new_domains)
                if answer is not None: return answer
            del assignments[sid]
            self.backtracks += 1
        return None

    def _result(self, success, assignments, message):
        return SolverResult(success, assignments, self.nodes, self.backtracks, self.pruned, message, self.conflicts)
