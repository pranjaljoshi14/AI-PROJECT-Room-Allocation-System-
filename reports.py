import io, csv
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def allocation_frame(students, rooms, assignments):
    sm={s.student_id:s for s in students}; seats={x.seat_id:x for r in rooms for x in r.seats}
    data=[]
    for sid,seat_id in assignments.items():
        s=sm[sid]; seat=seats[seat_id]
        data.append({"Student ID":sid,"Name":s.name,"Roll Number":s.roll_number,"Group":s.group,
          "Room":seat.room_id,"Seat":seat.seat_id,"Row":seat.row,"Column":seat.column,
          "Accessible Seat":seat.accessible})
    return pd.DataFrame(data)

def csv_bytes(df): return df.to_csv(index=False).encode("utf-8")
def excel_bytes(df):
    b=io.BytesIO()
    with pd.ExcelWriter(b,engine="openpyxl") as writer: df.to_excel(writer,index=False,sheet_name="Allocation")
    return b.getvalue()
def pdf_bytes(df,title,institution="Institution"):
    b=io.BytesIO(); c=canvas.Canvas(b,pagesize=A4); w,h=A4
    c.setTitle(title); y=h-48
    c.setFont("Helvetica-Bold",16); c.drawString(40,y,institution); y-=24
    c.setFont("Helvetica-Bold",12); c.drawString(40,y,title); y-=25
    c.setFont("Helvetica",8)
    for _,row in df.iterrows():
        line=" | ".join(str(row[k]) for k in ["Roll Number","Name","Room","Seat","Group"])
        c.drawString(40,y,line[:115]); y-=13
        if y<45: c.showPage(); y=h-45; c.setFont("Helvetica",8)
    c.save(); return b.getvalue()
