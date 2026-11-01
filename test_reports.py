from smartalloc.models import Student, Seat, Room
from smartalloc.reports import allocation_frame,csv_bytes,excel_bytes,pdf_bytes

def test_exports():
    s=[Student("1","A","R1","G1")]
    r=[Room("X","X","B","0",1,1,frozenset(),True,"Exam",[Seat("X-1","X",1,1)])]
    df=allocation_frame(s,r,{"1":"X-1"})
    assert b"R1" in csv_bytes(df)
    assert excel_bytes(df)[:2]==b"PK"
    assert pdf_bytes(df,"Test")[:4]==b"%PDF"
