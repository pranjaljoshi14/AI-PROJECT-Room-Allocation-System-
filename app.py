import streamlit as st
import pandas as pd
import plotly.express as px
from smartalloc.models import Student, Seat, Room
from smartalloc.database import Database
from smartalloc.solver import CSPSolver
from smartalloc.validation import validate_allocation
from smartalloc.reports import allocation_frame,csv_bytes,excel_bytes,pdf_bytes
from pathlib import Path
import io, json, shutil

st.set_page_config(page_title="SmartAlloc",page_icon="🪑",layout="wide")
st.markdown("""<style>
:root{--sa:#3157d5} .stApp{background:linear-gradient(135deg,#f6f8ff 0%,#f8fbff 55%,#eef2ff 100%)}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#172554,#263b78);color:white}
[data-testid="stSidebar"] *{color:white!important}
.sa-hero{padding:1.3rem 1.5rem;border-radius:18px;background:linear-gradient(110deg,#1e3a8a,#526de0);color:white;margin-bottom:1rem}
.sa-card{background:white;padding:1rem 1.2rem;border-radius:14px;border:1px solid #e7eaf4;box-shadow:0 5px 18px #1e3a8a0c}
div[data-testid="stMetric"]{background:white;padding:14px;border-radius:12px;border:1px solid #e7eaf4}
.stButton>button{border-radius:9px;font-weight:600}
</style>""",unsafe_allow_html=True)
db=Database()
if "last_assignments" not in st.session_state: st.session_state.last_assignments={}
if "last_students" not in st.session_state: st.session_state.last_students=[]
if "last_rooms" not in st.session_state: st.session_state.last_rooms=[]

st.sidebar.markdown("# 🪑 SmartAlloc")
st.sidebar.caption("Intelligent examination seating")
page=st.sidebar.radio("NAVIGATION",["Overview Dashboard","Student Management","Room Management","Seat Configuration","Generate Allocation","Seating Charts","Conflict Analysis","Reports & Downloads","Settings & About"])
st.sidebar.divider()
if st.sidebar.button("Load demonstration data",use_container_width=True):
    for i in range(100):
        group=f"G{(i%5)+1}"
        access=frozenset({"wheelchair"}) if i in (2,37) else (frozenset({"mobility"}) if i in (11,65) else frozenset())
        db.add_student(Student(f"ST{i+1:03}",f"Student {i+1:03}",f"DIT{i+1:03}",group,
          ["CSE","IT","ECE","ME"][i%4],"BTech",str((i%6)+1),access,i in (2,37,11,65) and 2 or 0,
          frozenset({"lift"}) if "mobility" in access or "wheelchair" in access else frozenset()))
    for j in range(5):
        rid=f"R{j+1}"
        seats=[]
        for r in range(1,6):
            for c in range(1,9):
                seats.append(Seat(f"{rid}-{r:02}-{c:02}",rid,r,c,accessible=(r==1 and c in (1,8)),blocked=(r==5 and c==8),aisle=(c==4)))
        db.add_room(Room(rid,f"Room {j+1}",f"Block {chr(65+j)}","Ground",5,8,frozenset({"lift","ramp"}) if j==0 else frozenset({"lift"}),True,"Examination",seats))
    st.sidebar.success("Demo data loaded.")
    st.rerun()

students=db.students(); rooms=db.rooms()
st.markdown('<div class="sa-hero"><h1>SmartAlloc</h1><p>Intelligent Room Allocation & Examination Seating Management System</p></div>',unsafe_allow_html=True)

if page=="Overview Dashboard":
    allocations=db.history()
    available=sum(r.capacity for r in rooms if r.available)
    c=st.columns(4)
    for col,label,value in zip(c,["Students","Rooms","Available seats","Allocation runs"],[len(students),len(rooms),available,len(allocations)]): col.metric(label,value)
    c=st.columns(2)
    with c[0]:
        st.subheader("Room capacity")
        if rooms: st.plotly_chart(px.bar(pd.DataFrame([{"Room":r.name,"Available seats":r.capacity if r.available else 0} for r in rooms]),x="Room",y="Available seats",color="Room"),use_container_width=True)
        else: st.info("Add rooms to see capacity analytics.")
    with c[1]:
        st.subheader("Student examination groups")
        if students: st.plotly_chart(px.pie(pd.DataFrame([{"Group":s.group} for s in students]).groupby("Group").size().reset_index(name="Students"),names="Group",values="Students",hole=.45),use_container_width=True)
        else: st.info("Add students or load demo data.")
    st.subheader("Recent allocation history")
    st.dataframe(pd.DataFrame(allocations,columns=["Examination","Status","Students","Rooms","Solver nodes","Created"]),use_container_width=True,hide_index=True)
elif page=="Student Management":
    st.subheader("Student Management")
    with st.expander("Add student",expanded=True):
        with st.form("student_form"):
            a,b,c=st.columns(3); sid=a.text_input("Student ID"); name=b.text_input("Full name"); roll=c.text_input("Roll number")
            d,e,f=st.columns(3); group=d.text_input("Examination group","G1"); dept=e.text_input("Department","CSE"); sem=f.text_input("Semester","3")
            access=st.multiselect("Accessibility requirements",["wheelchair","mobility","near_exit","low_vision"])
            facilities=st.multiselect("Required room facilities",["lift","ramp","accessible_toilet"])
            instructions=st.text_input("Special seating instructions")
            if st.form_submit_button("Save student"):
                if not all([sid,name,roll,group]): st.error("Student ID, name, roll number and group are required.")
                else:
                    try: db.add_student(Student(sid,name,roll,group,dept,"BTech",sem,frozenset(access),1 if access else 0,frozenset(facilities),instructions)); st.success("Student saved."); st.rerun()
                    except Exception as ex: st.error(f"Could not save student: {ex}")
    q=st.text_input("Search students")
    filtered=[s for s in students if q.lower() in " ".join([s.student_id,s.name,s.roll_number,s.group,s.department]).lower()]
    st.dataframe(pd.DataFrame([{"ID":s.student_id,"Name":s.name,"Roll":s.roll_number,"Group":s.group,"Department":s.department,"Accessibility":", ".join(s.accessibility)} for s in filtered]),use_container_width=True,hide_index=True)
    x,y=st.columns(2)
    with x:
        sid=st.selectbox("Delete student",[""]+[s.student_id for s in students])
        if st.button("Delete selected student",disabled=not sid):
            db.delete_student(sid); st.success("Student deleted."); st.rerun()
    with y:
        uploaded=st.file_uploader("Import students CSV/XLSX",type=["csv","xlsx"])
        if uploaded and st.button("Import file"):
            frame=pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
            required={"student_id","name","roll_number","group"}
            if not required.issubset(frame.columns): st.error("Required columns: "+", ".join(sorted(required)))
            else:
                count=0
                for _,r in frame.iterrows():
                    db.add_student(Student(str(r.student_id),str(r["name"]),str(r.roll_number),str(r["group"]),str(r.get("department","CSE"))))
                    count+=1
                st.success(f"Imported {count} students."); st.rerun()
    template=pd.DataFrame(columns=["student_id","name","roll_number","group","department"])
    st.download_button("Download student CSV template",template.to_csv(index=False),"student_template.csv","text/csv")
elif page=="Room Management":
    st.subheader("Room Management")
    with st.form("room_form"):
        a,b,c=st.columns(3); rid=a.text_input("Room ID"); name=b.text_input("Room name"); building=c.text_input("Building")
        d,e,f=st.columns(3); floor=d.text_input("Floor","Ground"); rows=e.number_input("Rows",1,30,5); cols=f.number_input("Columns",1,30,8)
        facilities=st.multiselect("Facilities",["lift","ramp","accessible_toilet","power_backup"])
        available=st.checkbox("Room available",True)
        if st.form_submit_button("Create / update room"):
            if not rid or not name: st.error("Room ID and name are required.")
            else:
                seats=[Seat(f"{rid}-{r:02}-{c:02}",rid,r,c,accessible=(r==1 and c==1),aisle=False) for r in range(1,int(rows)+1) for c in range(1,int(cols)+1)]
                db.add_room(Room(rid,name,building,floor,int(rows),int(cols),frozenset(facilities),available,"Examination",seats)); st.success("Room saved."); st.rerun()
    st.dataframe(pd.DataFrame([{"Room ID":r.room_id,"Name":r.name,"Building":r.building,"Floor":r.floor,"Capacity":r.capacity,"Available":r.available,"Facilities":", ".join(r.facilities)} for r in rooms]),use_container_width=True,hide_index=True)
elif page=="Seat Configuration":
    st.subheader("Seat Configuration")
    if not rooms: st.info("Create a room first.")
    else:
        room=st.selectbox("Select room",[r.room_id for r in rooms]); obj=next(r for r in rooms if r.room_id==room)
        st.caption(f"{obj.name} · {obj.rows} rows × {obj.columns} columns · {obj.capacity} usable seats")
        df=pd.DataFrame([{"Seat":s.seat_id,"Row":s.row,"Column":s.column,"Accessible":s.accessible,"Blocked":s.blocked,"Aisle":s.aisle} for s in obj.seats])
        edited=st.data_editor(df,use_container_width=True,hide_index=True,disabled=["Seat","Row","Column"],key=f"seatedit_{room}")
        if st.button("Save seat configuration"):
            updated=[]
            for _,r in edited.iterrows():
                updated.append(Seat(r["Seat"],room,int(r["Row"]),int(r["Column"]),bool(r["Accessible"]),bool(r["Blocked"]),bool(r["Aisle"])))
            obj.seats=updated; db.add_room(obj); st.success("Seat configuration saved.")
elif page=="Generate Allocation":
    st.subheader("Generate examination allocation")
    with st.form("allocation_form"):
        name=st.text_input("Examination name","End Semester Examination")
        date=st.date_input("Examination date")
        session=st.selectbox("Session",["Morning","Afternoon","Evening"])
        selected_students=st.multiselect("Students",options=[s.student_id for s in students],default=[s.student_id for s in students],format_func=lambda x: next((s.roll_number+" — "+s.name for s in students if s.student_id==x),x))
        selected_rooms=st.multiselect("Rooms",options=[r.room_id for r in rooms if r.available],default=[r.room_id for r in rooms if r.available])
        distance=st.select_slider("Minimum Manhattan separation for same group",options=[1,2,3],value=1)
        lcv=st.checkbox("Use Least Constraining Value heuristic",True); balance=st.checkbox("Balance room utilization",True)
        submitted=st.form_submit_button("⚡ Generate Allocation",type="primary")
    if submitted:
        chosen=[s for s in students if s.student_id in selected_students]
        chosen_rooms=[r for r in rooms if r.room_id in selected_rooms and r.available]
        total=sum(r.capacity for r in chosen_rooms)
        accessible=sum(1 for r in chosen_rooms for seat in r.seats if seat.accessible and not seat.blocked)
        required=sum(bool(s.accessibility) for s in chosen)
        st.write(f"Pre-check: {len(chosen)} students · {total} usable seats · {required} students with accessibility requirements · {accessible} accessible seats")
        if len(chosen)>total: st.error("Capacity conflict: selected students exceed available seats.")
        elif required>accessible: st.error("Accessibility warning: accessible seats may be insufficient.")
        else:
            bar=st.progress(0.15,text="Preparing CSP domains…")
            solver=CSPSolver(chosen,chosen_rooms,int(distance),lcv,balance)
            bar.progress(0.35,text="Running MRV / degree / LCV backtracking with forward checking…")
            result=solver.solve()
            bar.progress(0.8,text="Independently validating assignment…")
            report=validate_allocation(chosen,chosen_rooms,result.assignments,int(distance)) if result.success else None
            bar.progress(1.0,text="Complete")
            st.session_state.last_students=chosen; st.session_state.last_rooms=chosen_rooms
            st.session_state.last_assignments=result.assignments if result.success and report["valid"] else {}
            st.session_state.conflicts=result.conflicts
            if result.success and report["valid"]:
                db.save_allocation(name,str(date),session,chosen,chosen_rooms,result.assignments,result.nodes)
                st.success("Allocation generated and independently validated.")
                st.metric("Allocated students",len(result.assignments))
            else:
                db.save_history(name,"FAILED",len(chosen),len(chosen_rooms),result.nodes,result.conflicts)
                st.error(result.message)
                if report and report["issues"]: st.error("\\n".join(report["issues"]))
                for conflict in result.conflicts: st.warning(conflict["explanation"]+" Suggested action: "+conflict["suggestion"])
            st.json({"search_nodes":result.nodes,"backtracks":result.backtracks,"values_pruned":result.pruned_values,"validation":report})
elif page=="Seating Charts":
    st.subheader("Interactive seating charts")
    assignments=st.session_state.last_assignments; ss=st.session_state.last_students; rr=st.session_state.last_rooms
    if not assignments: st.info("Generate a validated allocation to display its seating charts.")
    else:
        frame=allocation_frame(ss,rr,assignments)
        query=st.text_input("Find student by name or roll number")
        if query:
            st.dataframe(frame[frame["Name"].str.contains(query,case=False)|frame["Roll Number"].str.contains(query,case=False)],use_container_width=True,hide_index=True)
        room_id=st.selectbox("Room",[r.room_id for r in rr])
        room=next(r for r in rr if r.room_id==room_id)
        mapping={v:k for k,v in assignments.items()}
        grid=[]
        for row in range(1,room.rows+1):
            vals=[]
            for col in range(1,room.columns+1):
                seat=next(s for s in room.seats if s.row==row and s.column==col)
                sid=mapping.get(seat.seat_id); student=next((s for s in ss if s.student_id==sid),None)
                if seat.blocked: label="🚫 BLOCKED"
                elif student: label=f"🟦 {student.roll_number}\\n{student.group}"
                elif seat.accessible: label="♿ EMPTY"
                else: label="EMPTY"
                vals.append(label)
            grid.append(vals)
        st.dataframe(pd.DataFrame(grid,index=[f"Row {i}" for i in range(1,room.rows+1)],columns=[f"Col {i}" for i in range(1,room.columns+1)]),use_container_width=True)
        occupied=sum(v in assignments.values() for v in [s.seat_id for s in room.seats])
        st.metric("Room occupancy",f"{occupied/max(1,room.capacity)*100:.1f}%")
        st.dataframe(frame[frame.Room==room_id],use_container_width=True,hide_index=True)
elif page=="Conflict Analysis":
    st.subheader("Conflict analysis")
    conflicts=st.session_state.get("conflicts",[])
    if conflicts:
        for i,c in enumerate(conflicts,1):
            st.error(f"Conflict {i} · {c['category']} · {c['severity']}")
            st.write(c["explanation"]); st.caption("Suggested action: "+c["suggestion"])
    else: st.info("No recorded solver conflicts. Pre-search diagnostics are shown during allocation generation.")
    st.markdown("**Diagnostic categories:** capacity, accessibility, eligibility, adjacency and configuration. A diagnostic suggestion is not a proof of a unique mathematical cause.")
elif page=="Reports & Downloads":
    st.subheader("Reports & Downloads")
    assignments=st.session_state.last_assignments
    if assignments:
        df=allocation_frame(st.session_state.last_students,st.session_state.last_rooms,assignments)
        st.dataframe(df,use_container_width=True,hide_index=True)
        st.download_button("Download CSV",csv_bytes(df),"smartalloc_allocation.csv","text/csv")
        st.download_button("Download Excel",excel_bytes(df),"smartalloc_allocation.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button("Download PDF",pdf_bytes(df,"Examination Seating Allocation"),"smartalloc_allocation.pdf","application/pdf")
    else: st.info("A validated allocation is required before reports can be generated.")
    if st.button("Download SQLite database backup"):
        db.backup("smartalloc_backup.db")
        st.success("Backup created at smartalloc_backup.db in the project directory.")
elif page=="Settings & About":
    st.subheader("Settings & About")
    st.write("**SmartAlloc** is a local-first examination seating manager powered by a genuine constraint satisfaction solver.")
    st.markdown("""- **Variables:** students.
- **Domains:** eligible, available, unblocked seats.
- **Hard constraints:** unique seats, accessibility/facilities, room availability, same-group separation.
- **Search:** recursive backtracking, MRV, degree tie-break, LCV and forward checking.
- **Persistence:** SQLite database with parameterized SQL.
- **Reports:** PDF, XLSX and CSV.""")
    institution=st.text_input("Institution name","Your Institution")
    st.caption("Data is stored locally in smartalloc.db. Keep regular backups.")
    if st.button("Create database backup"):
        db.backup("smartalloc_backup.db"); st.success("Backup saved as smartalloc_backup.db.")
    backup_file=st.file_uploader("Restore from a SmartAlloc SQLite backup",type=["db","sqlite"])
    if backup_file and st.button("Restore uploaded backup"):
        import sqlite3, tempfile, os
        temp_path="smartalloc_restore_check.db"
        try:
            with open(temp_path,"wb") as target: target.write(backup_file.getvalue())
            check=sqlite3.connect(temp_path)
            tables={row[0] for row in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            check.close()
            required={"students","rooms","seats","examinations","allocations"}
            if not required.issubset(tables): st.error("This file does not look like a SmartAlloc database backup.")
            else:
                shutil.copyfile(temp_path,db.path); st.success("Database restored. Refresh the application to reload records.")
        except Exception as ex: st.error(f"Restore failed: {ex}")
        finally:
            if os.path.exists(temp_path): os.remove(temp_path)
    st.caption("Python 3.11+ · Streamlit · Pandas · Plotly · SQLite · ReportLab · OpenPyXL")
