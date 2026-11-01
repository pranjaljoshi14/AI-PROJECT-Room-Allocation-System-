from smartalloc.models import Student, Seat, Room
from smartalloc.solver import CSPSolver
from smartalloc.validation import validate_allocation

def make_room(rid="R1", accessible=(1,1), blocked=()):
    seats=[]
    for r in range(1,3):
        for c in range(1,4):
            seats.append(Seat(f"{rid}-{r}-{c}",rid,r,c,(r,c) in accessible,(r,c) in blocked,False))
    return Room(rid,rid,"A","0",2,3,frozenset({"lift"}),True,"Exam",seats)

def test_basic_success_and_validation():
    students=[Student("1","A","01","G1"),Student("2","B","02","G2")]
    rooms=[make_room()]
    result=CSPSolver(students,rooms).solve()
    assert result.success and len(result.assignments)==2
    assert validate_allocation(students,rooms,result.assignments)["valid"]

def test_same_group_not_adjacent():
    students=[Student(str(i),str(i),str(i),"G1") for i in range(3)]
    rooms=[make_room()]
    result=CSPSolver(students,rooms).solve()
    assert result.success
    seats={s.seat_id:s for s in rooms[0].seats}
    chosen=[seats[v] for v in result.assignments.values()]
    for i,a in enumerate(chosen):
        for b in chosen[i+1:]:
            assert abs(a.row-b.row)+abs(a.column-b.column)>=2

def test_accessible_seat_required():
    students=[Student("1","A","01","G1",accessibility=frozenset({"wheelchair"}))]
    rooms=[make_room(accessible=((1,1),))]
    result=CSPSolver(students,rooms).solve()
    assert result.success
    seat=next(s for s in rooms[0].seats if s.seat_id==result.assignments["1"])
    assert seat.accessible

def test_insufficient_accessible_seats():
    students=[Student(str(i),str(i),str(i),"G1",accessibility=frozenset({"wheelchair"})) for i in range(2)]
    result=CSPSolver(students,[make_room(accessible=((1,1),))]).solve()
    assert not result.success

def test_capacity_conflict():
    students=[Student(str(i),str(i),str(i),"G1") for i in range(7)]
    result=CSPSolver(students,[make_room()]).solve()
    assert not result.success

def test_multiple_rooms_and_backtracking_stats():
    students=[Student(str(i),str(i),str(i),"G1") for i in range(6)]
    rooms=[make_room("R1"),make_room("R2")]
    result=CSPSolver(students,rooms).solve()
    assert result.success and result.nodes>0
    assert len(set(result.assignments.values()))==6

def test_unavailable_room_excluded():
    room=make_room(); room.available=False
    result=CSPSolver([Student("1","A","01","G1")],[room]).solve()
    assert not result.success

def test_blocked_seat_not_used():
    room=make_room(blocked=((1,1),(1,2),(1,3),(2,1),(2,2)))
    student=Student("1","A","01","G1")
    result=CSPSolver([student],[room]).solve()
    assert result.success
    assert result.assignments["1"] != "R1-1-1"
