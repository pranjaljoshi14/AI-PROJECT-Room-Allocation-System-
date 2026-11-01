import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

NAMES = ["Aarav", "Diya", "Rohan", "Meera", "Kabir", "Ananya", "Vihaan", "Isha", "Arjun", "Sana", "Dev", "Riya", "Karan", "Tara", "Neil",
         "Pooja", "Yash", "Nisha", "Aditya", "Kavya", "Rahul", "Simran", "Varun", "Tanya", "Harsh", "Mehak", "Ishaan", "Zoya", "Lakshmi", "Manav"]
BR = ["CSE", "ECE", "ME", "CE"]
COL = ["#8ecae6", "#b7e4c7", "#ffd6a5", "#cdb4db", "#ffadad", "#fdffb6", "#a0c4ff", "#caffbf"]
BG, DARK, PRI, GRN, ORG, RED, GRY, INK = "#f1f4f9", "#14213d", "#3a5ccc", "#2e9e5b", "#e08a2e", "#d62828", "#7d8699", "#1b1f2a"
FONT, BOLD, SMALL, HEAD = ("Helvetica", 10), ("Helvetica", 10, "bold"), ("Helvetica", 8), ("Helvetica", 13, "bold")
DELAY = {1: 700, 2: 350, 3: 180, 4: 90, 5: 45, 6: 22, 7: 12, 8: 8, 9: 5, 10: 2}
CW, CH = 108, 56
CHIPS = ["Allocated", "Unique seats", "Capacity", "Accessibility", "Group separation", "Priority"]
HELP = ("Click a seat to inspect | drag a student onto another seat to swap or move | right-click or Delete to unassign.\n"
        "Select an unseated student in the list, then click an empty seat (green outline) to place them. Click a group chip to focus it.")
S = lambda sid, name, group, pwd=False: {"id": sid, "name": name, "group": group, "pwd": pwd}
R = lambda name, rows, cols, ground=True, special=False: {"name": name, "rows": rows, "cols": cols, "ground": ground, "special": special}
acc = lambda room: room["ground"] or room["special"]
allseats = lambda rooms: [(r["name"], i, j) for r in rooms for i in range(r["rows"]) for j in range(r["cols"])]
nbrs = lambda seat: [(seat[0], seat[1], seat[2] - 1), (seat[0], seat[1], seat[2] + 1)]
label = lambda seat: "%s-%d%s" % (seat[0], seat[1] + 1, chr(65 + seat[2]))
P = lambda w, **k: (w.pack(**k), w)[1]
mk = lambda n, group, pwd: [S("S%02d" % (i + 1), NAMES[i % 30], group(i), i in pwd) for i in range(n)]
SCEN = {
    "Sample exam hall (solvable)": lambda: (mk(30, lambda i: BR[i % 4], {2, 7, 13, 20}), [R("G1", 3, 4), R("S1", 3, 4, 0, 1), R("F1", 4, 4, 0, 0)]),
    "Conflict: too many differently-abled": lambda: (mk(20, lambda i: BR[i % 4], set(range(8))), [R("G1", 2, 3), R("F1", 4, 4, 0, 0)]),
    "Conflict: one group too large": lambda: (mk(12, lambda i: "CSE" if i < 9 else "ECE", {10}), [R("H1", 2, 3), R("H2", 2, 3)]),
}

def hall_ok(dom):
    vals = list(dom.values())
    cands = {frozenset(d) for d in vals} | ({frozenset().union(*vals)} if vals else set())
    return all(sum(1 for d in vals if d <= c) <= len(c) for c in cands)

def settle(dom, queue, fixed, grp, adj, st):
    while queue:
        cur, cs = queue.pop()
        for o in list(dom):
            if o == cur:
                continue
            rem = {cs} | (set(nbrs(cs)) if adj and grp[o] == grp[cur] else set())
            if dom[o] & rem:
                new = dom[o] - rem
                st["pruned"] += len(dom[o]) - len(new)
                if not new:
                    return None
                dom[o] = new
                if len(new) == 1 and o not in fixed:
                    fixed.add(o)
                    queue.append((o, next(iter(new))))
    return dom if hall_ok(dom) else None

def find_conflicts(stu, rooms, access=True, adj=True):
    out, cap = [], lambda rs: sum(r["rows"] * r["cols"] for r in rs)
    ind = lambda rs: sum(r["rows"] * ((r["cols"] + 1) // 2) for r in rs)
    ar, pwd = [r for r in rooms if acc(r)], [s for s in stu if s["pwd"]]
    if len(stu) > cap(rooms):
        out.append(("Room capacity", "%d students but only %d seats exist." % (len(stu), cap(rooms))))
    if access and len(pwd) > cap(ar):
        out.append(("Accessibility", "%d differently-abled students but only %d accessible seats." % (len(pwd), cap(ar))))
    for g in sorted({s["group"] for s in stu}):
        n = sum(1 for s in stu if s["group"] == g)
        if adj and n > ind(rooms):
            out.append(("Group separation", "Group %s has %d students; at most %d can be kept apart." % (g, n, ind(rooms))))
    return out

def solve(stu, rooms, access=True, adj=True, limit=60000, trace=None):
    st = {"steps": 0, "back": 0, "pruned": 0, "limit": False}
    grp, pri = {s["id"]: s["group"] for s in stu}, {s["id"]: 0 if s["pwd"] else 1 for s in stu}
    size = {g: list(grp.values()).count(g) for g in grp.values()}
    rm, seats = {r["name"]: r for r in rooms}, allseats(rooms)
    order = {s: i for i, s in enumerate(seats)}
    dom = {s["id"]: {x for x in seats if acc(rm[x[0]])} if access and s["pwd"] else set(seats) for s in stu}
    if find_conflicts(stu, rooms, access, adj):
        return None, st
    ones = [(k, next(iter(d))) for k, d in dom.items() if len(d) == 1]
    dom = settle(dict(dom), ones, {k for k, _ in ones}, grp, adj, st)
    if dom is None:
        return None, st
    asg = {}

    def log(*e):
        if trace is not None and len(trace) < 4000:
            trace.append(e)

    def search(d):
        st["steps"] += 1
        st["limit"] = st["limit"] or st["steps"] > limit
        if st["limit"]:
            return False
        if not d:
            return True
        k = min(d, key=lambda x: (pri[x], len(d[x]), -size[grp[x]], x))
        for seat in sorted(d[k], key=lambda x: (pri[k] == 1 and acc(rm[x[0]]), order[x])):
            nd = settle({o: v for o, v in d.items() if o != k}, [(k, seat)], {k}, grp, adj, st)
            if nd is None:
                log("reject", k, seat)
            else:
                asg[k] = seat
                log("assign", k, seat)
                if search(nd):
                    return True
                del asg[k]
                log("undo", k)
            st["back"] += 1
        return False

    return (asg if search(dom) else None), st

def seat_conflicts(asg, stu, rooms):
    by, rm, own, out = {s["id"]: s for s in stu}, {r["name"]: r for r in rooms}, {v: k for k, v in asg.items()}, {}
    for k, v in asg.items():
        s, right = by[k], (v[0], v[1], v[2] + 1)
        if s["pwd"] and not acc(rm[v[0]]):
            out.setdefault(v, []).append(("acc", "%s needs an accessible room" % s["name"]))
        if right in own and by[own[right]]["group"] == s["group"]:
            m = ("adj", "%s and %s (both %s) sit side by side" % (s["name"], by[own[right]]["name"], s["group"]))
            out.setdefault(v, []).append(m)
            out.setdefault(right, []).append(m)
    return out

def validate(asg, stu, rooms):
    kind = lambda k: sorted({m[1] for ms in seat_conflicts(asg, stu, rooms).values() for m in ms if m[0] == k})
    miss = [s for s in stu if s["id"] not in asg]
    over = [r["name"] for r in rooms if sum(1 for v in asg.values() if v[0] == r["name"]) > r["rows"] * r["cols"]]
    lost, a, b = [s["name"] for s in miss if s["pwd"]], kind("acc"), kind("adj")
    return [("Every student allocated", not miss, "%d of %d students seated" % (len(asg), len(stu))),
            ("No seat used twice", len(set(asg.values())) == len(asg), "every seat is unique"),
            ("Room capacity respected", not over, "within capacity" if not over else "over capacity: " + ", ".join(over)),
            ("Accessibility requirements", not a, "; ".join(a) or "all differently-abled students are in accessible rooms"),
            ("No same-group side by side", not b, "; ".join(b) or "no neighbours share a group"),
            ("Priority rule honoured", not (lost and asg), "differently-abled students seated first" if not lost else "unseated: " + ", ".join(lost))]

def explain(stu, rooms):
    out = ["CONFLICT REPORT", "=" * 60, "1. Violations found by analysis"]
    out += ["   - [%s] %s" % p for p in find_conflicts(stu, rooms)] or ["   - none obvious; the rules interact"]
    out.append("2. Relaxation tests (drop a rule, search again)")
    ok = {}
    for lab, kw in (("group separation", {"adj": False}), ("accessibility", {"access": False}), ("both", {"adj": False, "access": False})):
        r, s = solve(stu, rooms, limit=20000, **kw)
        ok[lab] = bool(r)
        out.append("   - without %s: %s" % (lab, "solvable" if r else "undecided" if s["limit"] else "still unsolvable"))
    out.append("3. Constraints that caused the failure")
    g, a = ok["group separation"], ok["accessibility"]
    causes = [(g, "GROUP SEPARATION blocks the solution. Fix: add rooms/columns or move students of the biggest group."),
              (a, "ACCESSIBILITY blocks the solution. Fix: add ground-floor/special rooms or seats."),
              (ok["both"] and not g and not a, "GROUP SEPARATION + ACCESSIBILITY together are unsatisfiable. Relax one or add capacity."),
              (not any(ok.values()), "ROOM CAPACITY is insufficient even without the other rules. Fix: add rooms or seats.")]
    return "\n".join(out + ["  * " + t for c, t in causes if c])

def success_report(name, stu, rooms, asg, st, dt):
    out = ["ALLOCATION SUCCESSFUL", "=" * 60, "Scenario: %s | %d students" % (name, len(stu)),
           "Steps %d | backtracks/rejections %d | seats pruned %d | %.4f s" % (st["steps"], st["back"], st["pruned"], dt), "", "PRIORITY (seated first)"]
    out += ["  %s %-8s -> %s" % (s["id"], s["name"], label(asg[s["id"]])) for s in stu if s["pwd"]] + ["", "VALIDATION"]
    return "\n".join(out + ["  [%s] %s - %s" % ("PASS" if ok else "FAIL", t, d) for t, ok, d in validate(asg, stu, rooms)])

class App:
    def __init__(self, root):
        self.root = root
        root.title("Automated Room Allocation System (CSP)")
        root.geometry("1360x820")
        self.stu, self.rooms, self.asg, self.undo, self.colors, self.boxes, self.flash, self.checks = [], [], {}, [], {}, {}, {}, []
        self.sel = self.focus = self.drag = self.job = self.view = self.anim = self.hv = None
        self.ev, self.i, self.cnt = [], 0, [0, 0]
        self.build()
        self.load()

    def build(self):
        r, sty = self.root, ttk.Style()
        r.configure(bg=BG)
        sty.theme_use("clam")
        for k, kw in (("TFrame", {"background": BG}), ("TLabel", {"background": BG, "font": FONT}), ("TScale", {"background": BG}),
                      ("TButton", {"font": FONT, "padding": 6, "background": "#e4e9f4", "borderwidth": 0}), ("TNotebook", {"background": BG, "borderwidth": 0}),
                      ("A.TButton", {"background": PRI, "foreground": "white", "font": BOLD, "padding": 8, "borderwidth": 0}),
                      ("TNotebook.Tab", {"padding": (16, 8), "font": BOLD, "background": "#dfe5f1"})):
            sty.configure(k, **kw)
        sty.map("A.TButton", background=[("active", "#2a47a6")])
        sty.map("TButton", background=[("active", "#d3dbee")])
        sty.map("TNotebook.Tab", background=[("selected", "white")])
        head = P(tk.Frame(r, bg=DARK), fill="x")
        P(tk.Label(head, text="Automated Room Allocation System", bg=DARK, fg="white", font=("Helvetica", 16, "bold")), side="left", padx=16, pady=12)
        P(tk.Label(head, text="constraint satisfaction  |  backtracking  |  constraint propagation", bg=DARK, fg="#9fb3d9", font=FONT), side="left")
        self.badge = P(tk.Label(head, bg=GRY, fg="white", font=BOLD, padx=14, pady=5), side="right", padx=16)
        self.status = tk.StringVar(value="Press F5 to allocate or F6 to watch the solver search.")
        P(tk.Label(r, textvariable=self.status, anchor="w", bg="#dfe5f1", fg=INK, font=FONT, padx=12, pady=5), side="bottom", fill="x")
        strip = P(tk.Frame(r, bg=BG), fill="x", padx=10, pady=(10, 0))
        self.stat = {}
        for k in ("Students", "Seated", "Seats", "Priority seated"):
            f = P(tk.Frame(strip, bg="white", padx=14, pady=5, highlightthickness=1, highlightbackground="#dde3ef"), side="left", padx=(0, 8))
            self.stat[k] = P(tk.Label(f, bg="white", fg=PRI, font=("Helvetica", 16, "bold")), anchor="w")
            P(tk.Label(f, text=k, bg="white", fg=GRY, font=SMALL), anchor="w")
        self.chips = [P(tk.Label(strip, text=t, bg=GRY, fg="white", font=BOLD, padx=10, pady=8, cursor="hand2"), side="right", padx=3) for t in CHIPS[::-1]][::-1]
        for i, c in enumerate(self.chips):
            c.bind("<Button-1>", lambda e, i=i: self.status.set("%s: %s" % self.checks[i][::2]))
        pw = P(ttk.PanedWindow(r, orient="horizontal"), fill="both", expand=True, padx=10, pady=10)
        left, right = ttk.Frame(pw), ttk.Frame(pw)
        pw.add(left)
        pw.add(right, weight=1)
        self.scen = tk.StringVar(value=list(SCEN)[0])
        P(ttk.Combobox(left, textvariable=self.scen, values=list(SCEN), state="readonly", width=36), fill="x").bind("<<ComboboxSelected>>", lambda e: self.load())
        bf = P(ttk.Frame(left), fill="x", pady=8)
        btns = [("Run  F5", self.run, "A.TButton"), ("Animate  F6", self.animate, "A.TButton"), ("Skip animation", self.skip, "TButton"),
                ("Undo  Ctrl+Z", self.do_undo, "TButton"), ("Unassign  Del", lambda: self.rclick(None), "TButton"), ("Clear all", self.clear, "TButton")]
        for i, (t, c, st) in enumerate(btns):
            ttk.Button(bf, text=t, command=c, style=st).grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
        bf.columnconfigure((0, 1), weight=1)
        ttk.Label(left, text="Animation speed").pack(anchor="w")
        self.speed = tk.DoubleVar(value=4)
        P(ttk.Scale(left, from_=1, to=10, variable=self.speed), fill="x")
        nb = P(ttk.Notebook(left), fill="both", expand=True, pady=8)
        self.slist, self.rlist = self.pane(nb, "Students", self.add_student, "stu"), self.pane(nb, "Rooms", self.add_room, "rooms")
        self.slist.bind("<<ListboxSelect>>", self.pick)
        self.nb = P(ttk.Notebook(right), fill="both", expand=True)
        cf, af, rf = ttk.Frame(self.nb), ttk.Frame(self.nb), ttk.Frame(self.nb)
        for f, t in ((cf, "Seating Chart"), (af, "Analytics"), (rf, "Report / Conflicts")):
            self.nb.add(f, text=t)
        self.leg = P(ttk.Frame(cf, padding=8), fill="x")
        self.info = P(tk.Label(cf, anchor="nw", justify="left", bg="white", fg=INK, font=FONT, height=3, padx=12, pady=6, wraplength=950), side="bottom", fill="x")
        self.cv = P(tk.Canvas(cf, bg="#eaeef6", highlightthickness=0), fill="both", expand=True)
        self.ch = P(tk.Canvas(af, bg="#eaeef6", highlightthickness=0), fill="both", expand=True)
        for ev, fn in (("<ButtonPress-1>", self.press), ("<B1-Motion>", self.motion), ("<ButtonRelease-1>", self.release), ("<Motion>", self.hover),
                       ("<Button-3>", self.rclick), ("<Delete>", lambda e: self.rclick(None)), ("<Configure>", lambda e: self.root.after(100, self.draw))):
            self.cv.bind(ev, fn)
        self.rep = P(tk.Text(rf, font=("Courier", 10), bg="white", padx=12, pady=10, relief="flat"), fill="both", expand=True, padx=6, pady=6)
        for k, fn in (("<F5>", self.run), ("<F6>", self.animate), ("<Control-z>", self.do_undo)):
            r.bind(k, lambda e, fn=fn: fn())

    def pane(self, nb, title, add, attr):
        f = ttk.Frame(nb, padding=6)
        nb.add(f, text=title)
        b = P(ttk.Frame(f), side="bottom", fill="x", pady=(6, 0))
        P(ttk.Button(b, text="Add", command=add), side="left", expand=True, fill="x")
        P(ttk.Button(b, text="Delete selected", command=lambda: self.remove(attr, lb)), side="left", expand=True, fill="x", padx=(4, 0))
        lb = P(tk.Listbox(f, font=("Courier", 9), exportselection=False, activestyle="none", selectmode="extended", relief="flat", highlightthickness=1,
                          highlightbackground="#cfd7e8", selectbackground=PRI), fill="both", expand=True)
        return lb

    def by(self, sid):
        return next(s for s in self.stu if s["id"] == sid)
    def owner(self, seat):
        return next((k for k, v in self.asg.items() if v == seat), None)
    def text(self, t):
        self.rep.delete("1.0", "end")
        self.rep.insert("1.0", t)

    def load(self):
        self.stu, self.rooms = SCEN[self.scen.get()]()
        self.asg, self.sel, self.focus = {}, None, None
        self.text("Run the allocation (F5) to see the report.")
        self.changed()

    def changed(self):
        self.stop()
        ok, ids = set(allseats(self.rooms)), {s["id"] for s in self.stu}
        self.asg = {k: v for k, v in self.asg.items() if k in ids and v in ok}
        self.undo, self.sel = [], (self.sel if self.sel in ids else None)
        self.colors = {g: COL[i % len(COL)] for i, g in enumerate(sorted({s["group"] for s in self.stu}))}
        self.focus = self.focus if self.focus in self.colors else None
        self.rlist.delete(0, "end")
        for r in self.rooms:
            self.rlist.insert("end", "%-4s %dx%d  %s" % (r["name"], r["rows"], r["cols"], "accessible" if acc(r) else "-"))
        self.legend()
        self.refresh()

    def legend(self):
        for w in self.leg.winfo_children():
            w.destroy()
        ttk.Label(self.leg, text="Focus group:").pack(side="left", padx=(0, 8))
        for g, c in self.colors.items():
            lb = tk.Label(self.leg, text=g, bg=c, font=BOLD, padx=10, pady=2, bd=2, relief="sunken" if g == self.focus else "raised", cursor="hand2")
            lb.bind("<Button-1>", lambda e, g=g: (setattr(self, "focus", None if self.focus == g else g), self.legend(), self.draw()))
            lb.pack(side="left", padx=3)

    def refresh(self):
        self.checks = validate(self.asg, self.stu, self.rooms)
        good, pw = sum(1 for c in self.checks if c[1]), [s for s in self.stu if s["pwd"]]
        for c, (t, ok, d) in zip(self.chips, self.checks):
            c.config(bg=GRY if not self.asg else GRN if ok else RED)
        self.badge.config(text="%d/6 constraints satisfied" % good if self.asg else "No allocation yet", bg=((GRN if good == 6 else ORG) if self.asg else GRY))
        for k, v in (("Students", len(self.stu)), ("Seated", len(self.asg)), ("Seats", sum(r["rows"] * r["cols"] for r in self.rooms)),
                     ("Priority seated", "%d/%d" % (sum(1 for s in pw if s["id"] in self.asg), len(pw)))):
            self.stat[k].config(text=v)
        self.slist.delete(0, "end")
        for i, s in enumerate(self.stu):
            v = self.asg.get(s["id"])
            self.slist.insert("end", "%s %-8s %-4s %s %s" % (s["id"], s["name"], s["group"], "A" if s["pwd"] else " ", label(v) if v else "-"))
            self.slist.itemconfig(i, foreground=RED if s["pwd"] else INK)
        self.draw()
        self.charts()
        self.info.config(text=self.describe(None))

    def charts(self):
        c, y, own = self.ch, 26, self.asg.values()
        c.delete("all")
        rooms = [("Room " + r["name"], sum(1 for v in own if v[0] == r["name"]), r["rows"] * r["cols"], GRN if acc(r) else PRI) for r in self.rooms]
        groups = [(g, sum(1 for s in self.stu if s["group"] == g and s["id"] in self.asg), sum(1 for s in self.stu if s["group"] == g), col) for g, col in self.colors.items()]
        c.create_text(24, y, text="Constraint validation (live)", anchor="w", font=HEAD, fill=DARK)
        for t, ok, d in self.checks:
            y += 28
            c.create_oval(28, y - 8, 44, y + 8, fill=GRY if not self.asg else GRN if ok else RED, outline="")
            c.create_text(56, y, text=t, anchor="w", font=BOLD, fill=INK)
            c.create_text(280, y, text=d, anchor="w", font=FONT, fill=GRY)
        for title, data in (("Room occupancy", rooms), ("Allocation by group", groups)):
            y += 50
            c.create_text(24, y, text=title, anchor="w", font=HEAD, fill=DARK)
            for lab, v, tot, col in data:
                y += 28
                c.create_text(28, y, text=lab, anchor="w", font=BOLD, fill=INK)
                c.create_rectangle(150, y - 9, 550, y + 9, fill="#dde3ef", outline="")
                c.create_rectangle(150, y - 9, 150 + 400 * v / max(tot, 1), y + 9, fill=col, outline="")
                c.create_text(566, y, text="%d / %d" % (v, tot), anchor="w", font=FONT, fill=INK)

    def draw(self):
        cv, view = self.cv, self.view if self.view is not None else self.asg
        cv.delete("all")
        self.boxes = {}
        own, by = {v: k for k, v in view.items()}, {s["id"]: s for s in self.stu}
        cf = {} if self.view is not None else seat_conflicts(view, self.stu, self.rooms)
        W, x, y, rh = max(cv.winfo_width(), 700), 20, 20, 0
        for r in self.rooms:
            cap, a = r["rows"] * r["cols"], acc(r)
            bw, bh = r["cols"] * CW + 22, r["rows"] * CH + 72
            if x + bw > W - 20 and x > 20:
                x, y, rh = 20, y + rh + 20, 0
            used = sum(1 for v in own if v[0] == r["name"])
            cv.create_rectangle(x + 3, y + 3, x + bw + 3, y + bh + 3, fill="#d6dcea", outline="")
            cv.create_rectangle(x, y, x + bw, y + bh, fill="white", outline="#cfd7e8")
            cv.create_rectangle(x, y, x + 5, y + bh, fill=GRN if a else GRY, outline="")
            cv.create_text(x + 16, y + 10, anchor="nw", text="Room %s" % r["name"], font=HEAD, fill=DARK)
            cv.create_text(x + bw - 12, y + 12, anchor="ne", text="%d / %d seated" % (used, cap), font=BOLD, fill=PRI)
            cv.create_text(x + 16, y + 32, anchor="nw", font=SMALL, fill=GRN if a else GRY,
                           text=("Ground floor" if r["ground"] else "Upper floor") + (" + special" if r["special"] else "") + (" | accessible" if a else " | not accessible") + " | front at top")
            cv.create_rectangle(x + 16, y + 48, x + bw - 12, y + 54, fill="#e3e8f2", outline="")
            cv.create_rectangle(x + 16, y + 48, x + 16 + (bw - 28) * used / cap, y + 54, fill=GRN if used == cap else PRI, outline="")
            for i in range(r["rows"]):
                for j in range(r["cols"]):
                    b = (x + 14 + j * CW, y + 62 + i * CH, x + 8 + (j + 1) * CW, y + 56 + (i + 1) * CH)
                    self.boxes[(r["name"], i, j)] = b
                    self.seat((r["name"], i, j), b, own, by, cf)
            x, rh = x + bw + 20, max(rh, bh)
        cv.configure(scrollregion=(0, 0, W, y + rh + 20))

    def seat(self, seat, b, own, by, cf):
        cv, sid, m, fl = self.cv, own.get(seat), (b[0] + b[2]) / 2, self.flash.get(seat)
        tag = "%d%s" % (seat[1] + 1, chr(65 + seat[2]))
        if sid is None:
            pick = self.sel and self.sel not in self.asg and self.view is None
            cv.create_rectangle(*b, fill="#f8f9fc", outline=fl or (GRN if pick else "#c3cbdb"), width=5 if fl else 2, dash=(3, 3))
            cv.create_text(m, (b[1] + b[3]) / 2, text=tag + "  empty", font=SMALL, fill=GRY)
            return
        s = by[sid]
        dim, ol, w, d = self.focus and s["group"] != self.focus, "#c3cbdb", 1, None
        if sid == self.sel:
            ol, w = "#1f6feb", 4
        if seat in cf:
            ol, w, d = RED, 3, (4, 2)
        if fl:
            ol, w = fl, 5
        fg = "#9aa3b5" if dim else INK
        cv.create_rectangle(*b, fill="#f3f4f8" if dim else "white", outline=ol, width=w, dash=d)
        cv.create_rectangle(b[0] + 1, b[1] + 1, b[2] - 1, b[1] + 17, fill="#d5dbe8" if dim else self.colors[s["group"]], outline="")
        cv.create_text(b[0] + 5, b[1] + 9, anchor="w", text=tag, font=SMALL, fill=fg)
        cv.create_text(b[2] - 5, b[1] + 9, anchor="e", text=s["group"], font=("Helvetica", 8, "bold"), fill=fg)
        cv.create_text(m, b[1] + 31, text=s["name"][:12], font=BOLD, fill=fg)
        cv.create_text(m, b[1] + 44, text=s["id"], font=SMALL, fill=GRY)
        for on, cx, col, t in ((s["pwd"], b[2] - 10, RED, "A"), (seat in cf, b[0] + 10, ORG, "!")):
            if on:
                cv.create_oval(cx - 7, b[3] - 17, cx + 7, b[3] - 3, fill=col, outline="")
                cv.create_text(cx, b[3] - 10, text=t, fill="white", font=SMALL)

    def describe(self, seat):
        sid = self.owner(seat) if seat else self.sel
        if seat and sid is None:
            return "Empty seat %s. Select an unseated student in the list, then click here to place them." % label(seat)
        if sid is None:
            return HELP
        s, v = self.by(sid), self.asg.get(sid)
        out = "%s (%s) | group %s | %s | %s" % (s["name"], s["id"], s["group"], "differently-abled (priority)" if s["pwd"] else "regular", "seat " + label(v) if v else "not allocated")
        msgs = [m[1] for m in seat_conflicts(self.asg, self.stu, self.rooms).get(v, [])] if v else []
        return out + ("\nRULE VIOLATION: " + "; ".join(msgs) if msgs else "\nAll rules satisfied." if v else "")

    def at(self, e):
        x, y = self.cv.canvasx(e.x), self.cv.canvasy(e.y)
        return next((s for s, b in self.boxes.items() if b[0] <= x <= b[2] and b[1] <= y <= b[3]), None)

    def press(self, e):
        self.cv.focus_set()
        seat = self.at(e)
        sid = self.owner(seat) if seat else None
        if self.view is not None:
            return
        if seat and sid is None and self.sel and self.sel not in self.asg:
            return self.place(self.sel, seat)
        self.sel, self.drag = sid, ({"sid": sid, "p": (e.x, e.y), "moved": False} if sid else None)
        self.draw()
        self.info.config(text=self.describe(seat))

    def motion(self, e):
        d = self.drag
        if not d:
            return
        d["moved"] = d["moved"] or abs(e.x - d["p"][0]) + abs(e.y - d["p"][1]) > 8
        if d["moved"]:
            self.cv.delete("ghost")
            x, y, t, s = self.cv.canvasx(e.x), self.cv.canvasy(e.y), self.at(e), self.by(d["sid"])
            if t:
                b = self.boxes[t]
                self.cv.create_rectangle(b[0] - 3, b[1] - 3, b[2] + 3, b[3] + 3, outline="#1f6feb", width=3, dash=(4, 2), tags="ghost")
            self.cv.create_rectangle(x - 52, y - 18, x + 52, y + 18, fill=self.colors[s["group"]], outline="#1f6feb", width=2, tags="ghost")
            self.cv.create_text(x, y, text=s["name"], font=BOLD, tags="ghost")

    def release(self, e):
        d, self.drag = self.drag, None
        self.cv.delete("ghost")
        t = self.at(e)
        if d and d["moved"] and t and t != self.asg.get(d["sid"]):
            other, src, self.sel = self.owner(t), self.asg[d["sid"]], d["sid"]
            self.edit("Swapped with %s" % self.by(other)["name"] if other else "Moved to %s" % label(t), lambda: self.asg.update({**({other: src} if other else {}), d["sid"]: t}))

    def hover(self, e):
        seat = None if self.drag or self.view is not None else self.at(e)
        if seat != self.hv and not self.drag and self.view is None:
            self.hv = seat
            self.cv.config(cursor="hand2" if seat and self.owner(seat) else "")
            self.info.config(text=self.describe(seat))

    def rclick(self, e):
        sid = self.owner(self.at(e)) if e else self.sel
        if sid in self.asg:
            self.edit("Unassigned %s" % self.by(sid)["name"], lambda: self.asg.pop(sid))

    def edit(self, msg, fn):
        if self.view is None:
            self.undo.append(dict(self.asg))
            fn()
            self.commit(msg)

    def commit(self, msg):
        self.refresh()
        bad = sorted({m[1] for ms in seat_conflicts(self.asg, self.stu, self.rooms).values() for m in ms})
        self.status.set(msg + (" - WARNING: " + bad[0] if bad else " - no rule violated."))

    def place(self, sid, seat):
        self.edit("Placed %s at %s" % (self.by(sid)["name"], label(seat)), lambda: self.asg.update({sid: seat}))

    def do_undo(self):
        if self.undo and self.view is None:
            self.asg = self.undo.pop()
            self.commit("Undone")

    def clear(self):
        if self.asg:
            self.edit("Cleared all allocations (Undo restores them)", self.asg.clear)

    def pick(self, e):
        if self.slist.curselection():
            self.sel = self.stu[self.slist.curselection()[0]]["id"]
            self.draw()
            self.info.config(text=self.describe(None))

    def add_student(self):
        p = (simpledialog.askstring("Add student", "Name Group [A]\nA = differently-abled\nExample: Meera CSE A", parent=self.root) or "").split()
        if p:
            n = max([int("".join(c for c in s["id"] if c.isdigit()) or 0) for s in self.stu], default=0) + 1
            self.stu.append(S("S%02d" % n, p[0], (p[1] if len(p) > 1 else BR[0]).upper(), "A" in [x.upper() for x in p[2:]]))
            self.changed()

    def add_room(self):
        try:
            p = simpledialog.askstring("Add room", "Name Rows Cols [G=ground floor] [S=special]\nExample: G2 3 4 G", parent=self.root).split()
            name, rows, cols, fl = p[0], int(p[1]), int(p[2]), [x.upper() for x in p[3:]]
        except (AttributeError, IndexError, ValueError):
            return
        if name in {r["name"] for r in self.rooms} or not (1 <= rows <= 10 and 1 <= cols <= 8):
            return messagebox.showerror("Invalid room", "Use a unique name, rows 1-10 and seats per row 1-8.")
        self.rooms.append(R(name, rows, cols, "G" in fl, "S" in fl))
        self.changed()

    def remove(self, attr, lb):
        drop = set(lb.curselection())
        setattr(self, attr, [x for i, x in enumerate(getattr(self, attr)) if i not in drop])
        self.changed()

    def run(self):
        self.stop()
        t = time.time()
        self.conclude(solve(self.stu, self.rooms), time.time() - t)

    def animate(self):
        self.stop()
        tr, t = [], time.time()
        res = solve(self.stu, self.rooms, trace=tr)
        self.anim, self.ev, self.i, self.view, self.cnt, self.sel = (res, time.time() - t), tr, 0, {}, [0, 0], None
        self.nb.select(0)
        self.draw()
        self.job = self.root.after(300, self.tick)

    def tick(self):
        self.job = None
        if self.view is None:
            return
        sp, self.flash = max(1, min(10, int(round(self.speed.get())))), {}
        for _ in range(1 if sp <= 6 else (sp - 5) * 3):
            if self.i >= len(self.ev):
                break
            k, a, s = (self.ev[self.i] + (None,))[:3]
            self.i += 1
            if k == "assign":
                self.view[a], self.flash = s, {s: GRN}
            elif k == "undo":
                old = self.view.pop(a, None)
                self.cnt[0] += 1
                self.flash = {old: ORG} if old else {}
            else:
                self.cnt[1] += 1
                self.flash = {s: RED}
        self.draw()
        self.status.set("Searching: placed %d/%d | backtracks %d | rejected by propagation %d | step %d/%d" % (
            len(self.view), len(self.stu), self.cnt[0], self.cnt[1], self.i, len(self.ev)))
        done = self.i >= len(self.ev)
        self.job = self.root.after(700 if done else DELAY[sp], self.skip if done else self.tick)

    def skip(self):
        if self.view is not None and self.anim:
            res, dt = self.anim
            self.stop()
            self.conclude(res, dt)

    def stop(self):
        if self.job:
            self.root.after_cancel(self.job)
        self.job = self.view = self.anim = None
        self.flash, self.ev = {}, []

    def conclude(self, res, dt):
        asg, st = res
        self.undo, self.sel = [], None
        if asg:
            self.asg = dict(asg)
            self.text(success_report(self.scen.get(), self.stu, self.rooms, asg, st, dt))
            self.refresh()
            self.nb.select(0)
            return self.status.set("Allocation found in %d steps (%.3f s). Drag students to adjust; violations are flagged live." % (st["steps"], dt))
        self.asg = {}
        report = explain(self.stu, self.rooms)
        self.text("ALLOCATION FAILED - NO VALID SOLUTION\n\n" + report)
        self.refresh()
        self.nb.select(2)
        self.status.set("No valid allocation exists. See the conflict report.")
        messagebox.showwarning("No valid allocation", "\n".join(l for l in report.splitlines() if l.startswith("  *")) or "See the report tab.")

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()