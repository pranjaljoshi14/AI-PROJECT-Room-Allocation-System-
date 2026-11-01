from dataclasses import dataclass, field
from typing import FrozenSet

@dataclass(frozen=True)
class Student:
    student_id: str
    name: str
    roll_number: str
    group: str
    department: str = "CSE"
    course: str = "BTech"
    semester: str = "3"
    accessibility: FrozenSet[str] = frozenset()
    priority: int = 0
    required_facilities: FrozenSet[str] = frozenset()
    instructions: str = ""

@dataclass(frozen=True)
class Seat:
    seat_id: str
    room_id: str
    row: int
    column: int
    accessible: bool = False
    blocked: bool = False
    aisle: bool = False

@dataclass
class Room:
    room_id: str
    name: str
    building: str
    floor: str
    rows: int
    columns: int
    facilities: FrozenSet[str] = frozenset()
    available: bool = True
    room_type: str = "Examination"
    seats: list[Seat] = field(default_factory=list)

    @property
    def capacity(self):
        return sum(not s.blocked for s in self.seats)
