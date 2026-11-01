import sqlite3, json
from pathlib import Path
from dataclasses import asdict
from .models import Student, Seat, Room

class Database:
    def __init__(self, path="smartalloc.db"):
        self.path=str(path); self.init()
    def connect(self): return sqlite3.connect(self.path)
    def init(self):
        with self.connect() as c:
            c.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS students(student_id TEXT PRIMARY KEY,name TEXT NOT NULL,roll_number TEXT UNIQUE NOT NULL,group_name TEXT NOT NULL,department TEXT,course TEXT,semester TEXT,accessibility TEXT,priority INTEGER,facilities TEXT,instructions TEXT);
            CREATE TABLE IF NOT EXISTS rooms(room_id TEXT PRIMARY KEY,name TEXT,building TEXT,floor TEXT,rows INTEGER,columns_count INTEGER,facilities TEXT,available INTEGER,room_type TEXT);
            CREATE TABLE IF NOT EXISTS seats(seat_id TEXT PRIMARY KEY,room_id TEXT REFERENCES rooms(room_id) ON DELETE CASCADE,row_no INTEGER,col_no INTEGER,accessible INTEGER,blocked INTEGER,aisle INTEGER);
            CREATE TABLE IF NOT EXISTS examinations(exam_id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,date TEXT,session TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS allocations(allocation_id INTEGER PRIMARY KEY AUTOINCREMENT,exam_id INTEGER REFERENCES examinations(exam_id),student_id TEXT,seat_id TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS allocation_history(history_id INTEGER PRIMARY KEY AUTOINCREMENT,exam_name TEXT,status TEXT,student_count INTEGER,room_count INTEGER,solver_nodes INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP,details TEXT);
            CREATE TABLE IF NOT EXISTS conflict_reports(id INTEGER PRIMARY KEY AUTOINCREMENT,exam_name TEXT,category TEXT,explanation TEXT,severity TEXT,suggestion TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            """)
    def add_student(self,s):
        with self.connect() as c:
            c.execute("INSERT OR REPLACE INTO students VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (s.student_id,s.name,s.roll_number,s.group,s.department,s.course,s.semester,json.dumps(sorted(s.accessibility)),s.priority,json.dumps(sorted(s.required_facilities)),s.instructions))
    def delete_student(self,sid):
        with self.connect() as c: c.execute("DELETE FROM students WHERE student_id=?",(sid,))
    def students(self):
        with self.connect() as c: rows=c.execute("SELECT * FROM students ORDER BY roll_number").fetchall()
        return [Student(r[0],r[1],r[2],r[3],r[4] or "",r[5] or "",r[6] or "",frozenset(json.loads(r[7] or "[]")),r[8] or 0,frozenset(json.loads(r[9] or "[]")),r[10] or "") for r in rows]
    def add_room(self,r):
        with self.connect() as c:
            c.execute("INSERT OR REPLACE INTO rooms VALUES(?,?,?,?,?,?,?,?,?)",(r.room_id,r.name,r.building,r.floor,r.rows,r.columns,json.dumps(sorted(r.facilities)),int(r.available),r.room_type))
            c.execute("DELETE FROM seats WHERE room_id=?",(r.room_id,))
            c.executemany("INSERT INTO seats VALUES(?,?,?,?,?,?,?)",[(s.seat_id,s.room_id,s.row,s.column,int(s.accessible),int(s.blocked),int(s.aisle)) for s in r.seats])
    def rooms(self):
        with self.connect() as c:
            rr=c.execute("SELECT * FROM rooms").fetchall(); ss=c.execute("SELECT * FROM seats").fetchall()
        seats={}
        for x in ss: seats.setdefault(x[1],[]).append(Seat(x[0],x[1],x[2],x[3],bool(x[4]),bool(x[5]),bool(x[6])))
        return [Room(x[0],x[1],x[2],x[3],x[4],x[5],frozenset(json.loads(x[6] or "[]")),bool(x[7]),x[8],seats.get(x[0],[])) for x in rr]
    def save_history(self,name,status,nstudents,nrooms,nodes,details):
        with self.connect() as c: c.execute("INSERT INTO allocation_history(exam_name,status,student_count,room_count,solver_nodes,details) VALUES(?,?,?,?,?,?)",(name,status,nstudents,nrooms,nodes,json.dumps(details)))
    def history(self):
        with self.connect() as c: return c.execute("SELECT exam_name,status,student_count,room_count,solver_nodes,created_at FROM allocation_history ORDER BY history_id DESC").fetchall()
    def save_allocation(self,name,date,session,students,rooms,assignments,nodes):
        with self.connect() as c:
            cur=c.execute("INSERT INTO examinations(name,date,session) VALUES(?,?,?)",(name,date,session)); eid=cur.lastrowid
            c.executemany("INSERT INTO allocations(exam_id,student_id,seat_id) VALUES(?,?,?)",[(eid,sid,seat) for sid,seat in assignments.items()])
            c.execute("INSERT INTO allocation_history(exam_name,status,student_count,room_count,solver_nodes,details) VALUES(?,?,?,?,?,?)",(name,"SUCCESS",len(students),len(rooms),nodes,json.dumps(assignments)))
    def backup(self,destination):
        target=sqlite3.connect(destination)
        with self.connect() as source: source.backup(target)
        target.close()
