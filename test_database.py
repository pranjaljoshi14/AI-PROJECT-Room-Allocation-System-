from smartalloc.database import Database
from smartalloc.models import Student, Seat, Room

def test_persistence(tmp_path):
    db=Database(tmp_path/"test.db")
    db.add_student(Student("S1","Test Student","R1","G1"))
    assert db.students()[0].name=="Test Student"
    room=Room("A","A","Block","0",1,2,frozenset(),True,"Exam",
              [Seat("A-1","A",1,1),Seat("A-2","A",1,2)])
    db.add_room(room)
    assert db.rooms()[0].capacity==2
    db2=Database(tmp_path/"test.db")
    assert len(db2.students())==1 and len(db2.rooms())==1
