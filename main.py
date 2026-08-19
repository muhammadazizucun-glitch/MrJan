import os
import socket
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, flash, redirect, render_template_string, request, session, url_for
from markupsafe import escape
from werkzeug.security import check_password_hash, generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "korxona.db")
app = Flask(__name__)
app.secret_key = "poyabzal-lan-2026"


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today():
    return datetime.now().strftime("%Y-%m-%d")


def e(v):
    return escape("" if v is None else str(v))


def pul(n):
    try:
        return f"{int(round(float(n or 0))):,}".replace(",", " ")
    except Exception:
        return "0"


def son(v):
    try:
        return int(v)
    except Exception:
        return 0


def db():
    con = sqlite3.connect(DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def ips():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return [ip]
    except Exception:
        pass
    return []


def init_db():
    con = db()
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login_id TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            position TEXT,
            work_type TEXT DEFAULT 'ishbay',
            status TEXT DEFAULT 'active',
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            title TEXT,
            qty INTEGER DEFAULT 0,
            status TEXT DEFAULT 'ochiq',
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS work_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            work_date TEXT NOT NULL,
            party TEXT,
            operation TEXT,
            sewed INTEGER DEFAULT 0,
            accepted INTEGER DEFAULT 0,
            defect INTEGER DEFAULT 0,
            price REAL DEFAULT 0,
            amount REAL DEFAULT 0,
            note TEXT,
            status TEXT DEFAULT 'kiritildi',
            confirmed_by INTEGER,
            confirmed_at TEXT,
            created_at TEXT,
            is_deleted INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS daily_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            work_date TEXT NOT NULL,
            status TEXT DEFAULT 'tekshirilmagan',
            reviewed_by INTEGER,
            reviewed_at TEXT,
            UNIQUE(user_id, work_date)
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER,
            actor_role TEXT,
            action TEXT,
            target_user_id INTEGER,
            work_entry_id INTEGER,
            work_date TEXT,
            old_value TEXT,
            new_value TEXT,
            created_at TEXT
        );
        """
    )
    cur = con.cursor()
    if cur.execute("SELECT COUNT(*) n FROM users WHERE role='EGA'").fetchone()["n"] == 0:
        cur.execute(
            "INSERT INTO users (login_id,password_hash,full_name,role,phone,address,position,work_type,status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("1000", generate_password_hash("ega1234"), "Korxona egasi", "EGA", "", "", "Ega", "", "active", now()),
        )
    if cur.execute("SELECT COUNT(*) n FROM operations").fetchone()["n"] == 0:
        cur.executemany(
            "INSERT INTO operations (name,price,active) VALUES (?,?,1)",
            [
                ("Charm kesish", 3000),
                ("Astar kesish", 1500),
                ("Yuza tikish", 6000),
                ("Bezak tikish", 2000),
                ("Kolodkaga tortish", 5000),
                ("Tag yelimlash", 4000),
                ("Taglik presslash", 3000),
                ("Tozalash / pardoz", 1500),
                ("Qadoqlash", 1000),
            ],
        )
    if cur.execute("SELECT COUNT(*) n FROM parties").fetchone()["n"] == 0:
        cur.execute(
            "INSERT INTO parties (code,title,qty,status,created_at) VALUES (?,?,?,?,?)",
            ("P-001", "Namuna partiya", 500, "ochiq", now()),
        )
    con.commit()
    con.close()


def me():
    if "uid" not in session:
        return None
    con = db()
    u = con.execute("SELECT * FROM users WHERE id=?", (session["uid"],)).fetchone()
    con.close()
    return u


def login_required(fn):
    @wraps(fn)
    def w(*a, **k):
        if not me():
            return redirect(url_for("login"))
        return fn(*a, **k)
    return w


def roles(*ok):
    def deco(fn):
        @wraps(fn)
        def w(*a, **k):
            u = me()
            if not u:
                return redirect(url_for("login"))
            if u["role"] not in ok:
                flash("Bu bolim yopiq.", "xato")
                return redirect(url_for("home"))
            return fn(*a, **k)
        return w
    return deco


def audit(u, action, target=None, entry=None, wdate=None, old="", new=""):
    con = db()
    con.execute(
        "INSERT INTO audit_log (actor_id,actor_role,action,target_user_id,work_entry_id,work_date,old_value,new_value,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (u["id"] if u else None, u["role"] if u else "", action, target, entry, wdate, old, new, now()),
    )
    con.commit()
    con.close()


def holat(s):
    d = {
        "kiritildi": "Tekshirilmagan",
        "tasdiqlandi": "Tasdiqlangan",
        "ega_tahrirladi": "Ega tahrirlagan",
        "tekshirilmagan": "Tekshirilmagan",
        "ochiq": "Ochiq",
    }
    return d.get(s or "", s or "-")


def confirmed(s):
    return s in ("tasdiqlandi", "ega_tahrirladi")


TPL = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Arial,sans-serif;background:#f3ead6;color:#1f2937}
.top{padding:14px;color:#fff}
.ega{background:#7c2d12}.admin{background:#1e3a5f}.ishchi{background:#14532d}.guest{background:#111827}
.wrap{max-width:860px;margin:0 auto;padding:12px}
.card{background:#fffaf0;border:1px solid #e8d7b0;border-radius:16px;padding:14px;margin:0 0 12px}
h2{margin:0 0 8px}
.muted{color:#6b7280;font-size:14px}
.big{font-size:26px;font-weight:800}
.addr{background:#111;color:#fff;padding:12px;border-radius:12px;text-align:center;font-weight:800;word-break:break-all}
input,select,textarea,button{width:100%;padding:12px;margin:5px 0 10px;border-radius:12px;border:1px solid #d6d3d1;font-size:16px}
button,.btn{display:block;text-align:center;text-decoration:none;background:#111;color:#fff;border:0;font-weight:700}
.ok{background:#166534}
.light{background:#fff;color:#111;border:1px solid #e8d7b0}
.pill{display:inline-block;padding:3px 9px;border-radius:999px;font-size:12px;font-weight:700}
.y{background:#fef3c7;color:#92400e}.g{background:#dcfce7;color:#166534}
.flash{padding:10px;border-radius:12px;margin:0 0 10px}
.okx{background:#dcfce7}.xato{background:#fee2e2}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:8px 4px;border-bottom:1px solid #e8d7b0}
nav a{display:inline-block;margin:5px 5px 0 0;color:#fff;text-decoration:none;font-size:13px;background:rgba(255,255,255,.18);padding:6px 10px;border-radius:999px}
</style>
</head>
<body>
<div class="top {{ theme }}">
<b>{{ head }}</b>
{% if u %}
<div class="muted" style="color:#fff">{{ u.full_name }} · ID {{ u.login_id }} · {{ u.role }}</div>
<nav>
<a href="{{ url_for('home') }}">Bosh</a>
{% if u.role in ['EGA','ADMIN'] %}
<a href="{{ url_for('xodimlar') }}">+ Xodim</a>
<a href="{{ url_for('tekshir') }}">Tekshir</a>
<a href="{{ url_for('partiyalar') }}">Partiya</a>
{% endif %}
{% if u.role=='EGA' %}
<a href="{{ url_for('narxlar') }}">Narx</a>
<a href="{{ url_for('jurnal') }}">Jurnal</a>
{% endif %}
{% if u.role=='ISHCHI' %}
<a href="{{ url_for('ish') }}">Ish</a>
<a href="{{ url_for('hisob') }}">Hisob</a>
{% endif %}
<a href="{{ url_for('chiqish') }}">Chiqish</a>
</nav>
{% endif %}
</div>
<div class="wrap">
{% with msgs = get_flashed_messages(with_categories=true) %}
{% for c,m in msgs %}<div class="flash {{ c }}">{{ m }}</div>{% endfor %}
{% endwith %}
{{ body|safe }}
</div>
</body></html>
"""


def page(title, body, u=None):
    theme, head = "guest", "Poyabzal"
    if u:
        theme = u["role"].lower()
        head = {"EGA": "Ega paneli", "ADMIN": "Admin paneli"}.get(u["role"], "Ishchi paneli")
    return render_template_string(TPL, title=title, body=body, u=u, theme=theme, head=head)


def addr_html():
    lst = ips()
    if not lst:
        return '<div class="addr">http://127.0.0.1:5000</div>'
    out = ""
    for ip in lst:
        out += '<div class="addr">http://' + str(e(ip)) + ":5000</div>"
    return out


@app.route("/")
def home():
    u = me()
    if not u:
        return redirect(url_for("login"))
    if u["role"] == "EGA":
        return ega_home(u)
    if u["role"] == "ADMIN":
        return admin_home(u)
    return ishchi_home(u)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        lid = (request.form.get("login_id") or "").strip()
        pw = request.form.get("password") or ""
        con = db()
        u = con.execute("SELECT * FROM users WHERE login_id=? AND status='active'", (lid,)).fetchone()
        con.close()
        if u and check_password_hash(u["password_hash"], pw):
            session["uid"] = u["id"]
            flash("Xush kelibsiz.", "okx")
            return redirect(url_for("home"))
        flash("ID yoki parol xato.", "xato")
    body = (
        '<div class="card"><h2>Tizimga kirish</h2>'
        '<p class="muted">Lokal tarmoq. Internet kerak emas.</p>'
        '<form method="post">'
        "<label>ID</label><input name=\"login_id\" inputmode=\"numeric\" placeholder=\"1000\" required>"
        "<label>Parol</label><input name=\"password\" type=\"password\" placeholder=\"ega1234\" required>"
        '<button class="ok">Kirish</button></form></div>'
    )
    return page("Kirish", body)


@app.route("/chiqish")
def chiqish():
    session.clear()
    return redirect(url_for("login"))


def ega_home(u):
    con = db()
    ishchi = con.execute("SELECT COUNT(*) n FROM users WHERE role='ISHCHI' AND status='active'").fetchone()["n"]
    admin = con.execute("SELECT COUNT(*) n FROM users WHERE role='ADMIN' AND status='active'").fetchone()["n"]
    bugun = con.execute(
        "SELECT COALESCE(SUM(amount),0) s, COALESCE(SUM(accepted),0) a FROM work_entries WHERE work_date=? AND is_deleted=0",
        (today(),),
    ).fetchone()
    kut = con.execute("SELECT COUNT(*) n FROM work_entries WHERE status='kiritildi' AND is_deleted=0").fetchone()["n"]
    con.close()
    body = (
        '<div class="card"><h2>Xodim qoshish</h2>'
        '<a class="btn ok" href="' + url_for("xodimlar") + '">+ XODIM QOSHISH</a></div>'
        '<div class="card"><h2>Tarmoq manzili</h2>' + addr_html() +
        '<p class="muted">https emas. :5000 bolsin.</p></div>'
        '<div class="card"><h2>Bugun</h2>'
        "<p>Ishchi: <b>" + str(ishchi) + "</b> · Admin: <b>" + str(admin) + "</b></p>"
        "<p>Qabul: <b>" + str(bugun["a"]) + "</b> juft</p>"
        '<p class="big">' + pul(bugun["s"]) + " som</p>"
        "<p>Tekshirilmagan: <b>" + str(kut) + "</b></p></div>"
        '<a class="btn" href="' + url_for("tekshir") + '">Tekshirish</a>'
        '<a class="btn light" href="' + url_for("partiyalar") + '">Partiya</a>'
        '<a class="btn light" href="' + url_for("narxlar") + '">Narxlar</a>'
        '<a class="btn light" href="' + url_for("jurnal") + '">Jurnal</a>'
    )
    return page("Ega", body, u)


def admin_home(u):
    con = db()
    kut = con.execute("SELECT COUNT(*) n FROM work_entries WHERE status='kiritildi' AND is_deleted=0").fetchone()["n"]
    con.close()
    body = (
        '<div class="card"><h2>Admin</h2>'
        "<p>Ishchi qoshasiz. Tasdiqlagan kunni keyin ozgartira olmaysiz.</p>"
        "<p>Tekshirilmagan: <b>" + str(kut) + "</b></p></div>"
        '<a class="btn ok" href="' + url_for("xodimlar") + '">+ ISHCHI QOSHISH</a>'
        '<a class="btn" href="' + url_for("tekshir") + '">Tekshirish</a>'
    )
    return page("Admin", body, u)


def ishchi_home(u):
    con = db()
    r = con.execute(
        "SELECT COALESCE(SUM(accepted),0) a, COALESCE(SUM(amount),0) s FROM work_entries WHERE user_id=? AND work_date=? AND is_deleted=0",
        (u["id"], today()),
    ).fetchone()
    h = con.execute("SELECT status FROM daily_reviews WHERE user_id=? AND work_date=?", (u["id"], today())).fetchone()
    con.close()
    st = h["status"] if h else "tekshirilmagan"
    cls = "g" if confirmed(st) else "y"
    body = (
        '<div class="card"><h2>' + str(e(u["full_name"])) + "</h2>"
        "<p>Lavozim: " + str(e(u["position"] or "-")) + "</p>"
        "<p>Bugun qabul: <b>" + str(r["a"]) + "</b> juft</p>"
        '<p class="big">' + pul(r["s"]) + " som</p>"
        '<span class="pill ' + cls + '">' + holat(st) + "</span></div>"
        '<a class="btn ok" href="' + url_for("ish") + '">ISH KIRITISH</a>'
        '<a class="btn light" href="' + url_for("hisob") + '">Hisobim</a>'
    )
    return page("Ishchi", body, u)


@app.route("/xodimlar", methods=["GET", "POST"])
@roles("EGA", "ADMIN")
def xodimlar():
    u = me()
    if request.method == "POST":
        lid = (request.form.get("login_id") or "").strip()
        name = (request.form.get("full_name") or "").strip()
        pw = request.form.get("password") or ""
        role = (request.form.get("role") or "ISHCHI").strip()
        phone = (request.form.get("phone") or "").strip()
        address = (request.form.get("address") or "").strip()
        position = (request.form.get("position") or "").strip()
        wtype = (request.form.get("work_type") or "ishbay").strip()
        if u["role"] == "ADMIN":
            role = "ISHCHI"
        if role not in ("ADMIN", "ISHCHI") or not lid or not name or not pw:
            flash("Ism, ID, parol majburiy.", "xato")
            return redirect(url_for("xodimlar"))
        con = db()
        if con.execute("SELECT id FROM users WHERE login_id=?", (lid,)).fetchone():
            con.close()
            flash("Bu ID band.", "xato")
            return redirect(url_for("xodimlar"))
        con.execute(
            "INSERT INTO users (login_id,password_hash,full_name,role,phone,address,position,work_type,status,created_at) VALUES (?,?,?,?,?,?,?,?, 'active', ?)",
            (lid, generate_password_hash(pw), name, role, phone, address, position, wtype, now()),
        )
        con.commit()
        nid = con.execute("SELECT id FROM users WHERE login_id=?", (lid,)).fetchone()["id"]
        con.close()
        audit(u, "xodim_qoshildi", target=nid, new=role + " " + name + " ID " + lid)
        flash("Qoshildi: " + name + " ID " + lid, "okx")
        return redirect(url_for("xodimlar"))

    con = db()
    rows = con.execute("SELECT * FROM users WHERE status='active' ORDER BY role, login_id").fetchall()
    con.close()
    role_html = ""
    if u["role"] == "EGA":
        role_html = (
            "<label>Kim?</label><select name=\"role\">"
            '<option value="ISHCHI">Ishchi</option>'
            '<option value="ADMIN">Admin</option></select>'
        )
    tr = ""
    for r in rows:
        tr += (
            "<tr><td>" + str(e(r["login_id"])) + "</td><td>" + str(e(r["full_name"]))
            + "<br><span class='muted'>" + str(e(r["role"])) + "</span></td><td>"
            + str(e(r["position"] or "-")) + "</td><td>" + str(e(r["phone"] or "-")) + "</td></tr>"
        )
    if not tr:
        tr = "<tr><td colspan=4>Hali yoq</td></tr>"
    body = (
        '<div class="card"><h2>+ Yangi xodim</h2>'
        '<form method="post">'
        "<label>Ism-familiya</label><input name=\"full_name\" required>"
        "<label>ID</label><input name=\"login_id\" inputmode=\"numeric\" required>"
        "<label>Parol</label><input name=\"password\" required>"
        + role_html
        + "<label>Telefon</label><input name=\"phone\">"
        "<label>Manzil</label><input name=\"address\">"
        "<label>Lavozim</label><input name=\"position\">"
        "<label>Ish turi</label><select name=\"work_type\">"
        '<option value="ishbay">Ishbay</option>'
        '<option value="soatbay">Soatbay</option></select>'
        '<button class="ok">SAQLASH</button></form></div>'
        '<div class="card"><h2>Xodimlar</h2><table>'
        "<tr><th>ID</th><th>Ism</th><th>Lavozim</th><th>Telefon</th></tr>"
        + tr + "</table></div>"
    )
    return page("Xodimlar", body, u)


@app.route("/partiyalar", methods=["GET", "POST"])
@roles("EGA", "ADMIN")
def partiyalar():
    u = me()
    con = db()
    if request.method == "POST":
        code = (request.form.get("code") or "").strip().upper()
        title = (request.form.get("title") or "").strip()
        qty = son(request.form.get("qty"))
        if not code:
            flash("Kod kerak.", "xato")
        elif con.execute("SELECT id FROM parties WHERE code=?", (code,)).fetchone():
            flash("Bu kod bor.", "xato")
        else:
            con.execute(
                "INSERT INTO parties (code,title,qty,status,created_at) VALUES (?,?,?,'ochiq',?)",
                (code, title, qty, now()),
            )
            con.commit()
            audit(u, "partiya_ochildi", new=code)
            flash("Partiya ochildi.", "okx")
        con.close()
        return redirect(url_for("partiyalar"))
    rows = con.execute("SELECT * FROM parties ORDER BY id DESC").fetchall()
    con.close()
    items = ""
    for r in rows:
        items += (
            '<div class="card"><b>' + str(e(r["code"])) + "</b> "
            + str(e(r["title"] or "")) + "<br>" + str(r["qty"]) + " juft</div>"
        )
    body = (
        '<div class="card"><h2>Yangi partiya</h2><form method="post">'
        "<label>Kod</label><input name=\"code\" placeholder=\"P-105\" required>"
        "<label>Nomi</label><input name=\"title\">"
        "<label>Necha juft</label><input name=\"qty\" type=\"number\" value=\"0\">"
        '<button class="ok">Ochish</button></form></div>' + (items or '<div class="card">Hali yoq</div>')
    )
    return page("Partiya", body, u)


@app.route("/narxlar", methods=["GET", "POST"])
@roles("EGA")
def narxlar():
    u = me()
    con = db()
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        price = son(request.form.get("price"))
        if name and price >= 0:
            con.execute("INSERT INTO operations (name,price,active) VALUES (?,?,1)", (name, price))
            con.commit()
            audit(u, "narx_qoshildi", new=name)
            flash("Qoshildi.", "okx")
        con.close()
        return redirect(url_for("narxlar"))
    rows = con.execute("SELECT * FROM operations WHERE active=1 ORDER BY name").fetchall()
    con.close()
    items = ""
    for r in rows:
        items += "<tr><td>" + str(e(r["name"])) + "</td><td>" + pul(r["price"]) + "</td></tr>"
    body = (
        '<div class="card"><h2>Yangi vazifa</h2><form method="post">'
        "<label>Nomi</label><input name=\"name\" required>"
        "<label>1 juft narxi</label>"
        )