"""
dashboard.py — AI DevOps Incident Response System
Now with Flask-Login Authentication + Role-Based Access Control
"""

from flask import Flask, jsonify, render_template_string, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = "devops-agent-secret-key-change-in-prod"  # ← change this in production!

# ─── Auth Setup ───────────────────────────────────────────────────────────────
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "🔒 Please log in to access the dashboard."

# ─── User Model ───────────────────────────────────────────────────────────────
class User(UserMixin):
    def __init__(self, id, username, password_hash, role):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role  # "admin" | "engineer" | "viewer"

    def check_password(self, pw):
        return bcrypt.check_password_hash(self.password_hash, pw)

    def is_admin(self):    return self.role == "admin"
    def is_engineer(self): return self.role in ("admin", "engineer")

# ─── Users DB (in-memory — swap with SQLite/Postgres for production) ──────────
USERS = {
    "1": User("1", "admin",    bcrypt.generate_password_hash("admin123").decode(),    "admin"),
    "2": User("2", "engineer", bcrypt.generate_password_hash("eng123").decode(),      "engineer"),
    "3": User("3", "viewer",   bcrypt.generate_password_hash("view123").decode(),     "viewer"),
}

def get_user_by_username(username):
    return next((u for u in USERS.values() if u.username == username), None)

@login_manager.user_loader
def load_user(user_id):
    return USERS.get(user_id)

# ─── Role Decorators ──────────────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin():
            return jsonify({"error": "⛔ Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated

def engineer_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_engineer():
            return jsonify({"error": "⛔ Engineer or Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated

# ─── Data Store ───────────────────────────────────────────────────────────────
incidents_db = []
system_status = {
    "status": "running",
    "last_check": str(datetime.now()),
    "total_incidents": 0,
    "agents_active": 5
}

# ─── HTML Templates ───────────────────────────────────────────────────────────

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>DevOps Agent — Login</title>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Syne:wght@700;800&display=swap" rel="stylesheet"/>
  <style>
    :root {
      --bg:#0a0e1a; --card:#0f1628; --border:#1e2d4a;
      --accent:#00d4ff; --accent2:#7c3aed;
      --text:#e2e8f0; --muted:#64748b;
    }
    *{margin:0;padding:0;box-sizing:border-box;}
    body{background:var(--bg);color:var(--text);font-family:'Syne',sans-serif;
         min-height:100vh;display:flex;align-items:center;justify-content:center;overflow:hidden;}
    body::before{content:'';position:fixed;inset:0;
      background-image:linear-gradient(rgba(0,212,255,.04) 1px,transparent 1px),
                       linear-gradient(90deg,rgba(0,212,255,.04) 1px,transparent 1px);
      background-size:40px 40px;animation:gridMove 20s linear infinite;}
    @keyframes gridMove{to{transform:translateY(40px);}}
    .orb{position:fixed;border-radius:50%;filter:blur(80px);opacity:.15;pointer-events:none;}
    .o1{width:400px;height:400px;background:var(--accent);top:-100px;right:-100px;animation:fl 8s ease-in-out infinite;}
    .o2{width:300px;height:300px;background:var(--accent2);bottom:-80px;left:-80px;animation:fl 10s ease-in-out infinite reverse;}
    @keyframes fl{0%,100%{transform:translate(0,0);}50%{transform:translate(30px,-30px);}}
    .wrap{position:relative;z-index:10;width:100%;max-width:420px;padding:20px;}
    .logo-row{text-align:center;margin-bottom:28px;}
    .logo-icon{width:52px;height:52px;background:linear-gradient(135deg,var(--accent),var(--accent2));
      border-radius:14px;display:inline-flex;align-items:center;justify-content:center;
      font-size:26px;box-shadow:0 0 24px rgba(0,212,255,.35);margin-bottom:12px;}
    .logo-title{font-size:22px;font-weight:800;background:linear-gradient(135deg,var(--accent),#fff);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;}
    .logo-sub{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);
      letter-spacing:2px;text-transform:uppercase;margin-top:4px;}
    .card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:32px;
      box-shadow:0 0 40px rgba(0,0,0,.5),0 0 80px rgba(0,212,255,.05);}
    .alert{padding:12px 16px;border-radius:8px;font-size:13px;margin-bottom:18px;
      font-family:'JetBrains Mono',monospace;}
    .alert-danger {background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:#fca5a5;}
    .alert-success{background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);color:#86efac;}
    .alert-warning{background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);color:#fcd34d;}
    .fg{margin-bottom:20px;}
    label{display:block;font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:1.5px;
      text-transform:uppercase;color:var(--muted);margin-bottom:8px;}
    input{width:100%;background:rgba(255,255,255,.03);border:1px solid var(--border);border-radius:8px;
      padding:12px 16px;color:var(--text);font-family:'JetBrains Mono',monospace;font-size:14px;
      transition:.2s;outline:none;}
    input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(0,212,255,.1);}
    input::placeholder{color:var(--muted);}
    .btn{width:100%;padding:14px;background:linear-gradient(135deg,var(--accent),#0099cc);border:none;
      border-radius:8px;color:#000;font-family:'Syne',sans-serif;font-size:15px;font-weight:700;
      cursor:pointer;transition:.2s;box-shadow:0 4px 20px rgba(0,212,255,.3);}
    .btn:hover{box-shadow:0 4px 30px rgba(0,212,255,.5);opacity:.9;}
    .demo{margin-top:22px;padding:16px;background:rgba(255,255,255,.02);
      border:1px solid var(--border);border-radius:10px;}
    .demo-title{font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:2px;
      color:var(--muted);text-transform:uppercase;margin-bottom:12px;}
    .cr{display:flex;align-items:center;gap:8px;margin-bottom:8px;
      font-family:'JetBrains Mono',monospace;font-size:12px;}
    .rb{padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;
      letter-spacing:1px;text-transform:uppercase;min-width:72px;text-align:center;}
    .ra{background:rgba(239,68,68,.2);color:#fca5a5;border:1px solid rgba(239,68,68,.3);}
    .re{background:rgba(245,158,11,.2);color:#fcd34d;border:1px solid rgba(245,158,11,.3);}
    .rv{background:rgba(34,197,94,.2);color:#86efac;border:1px solid rgba(34,197,94,.3);}
    .cm{color:var(--muted);}
  </style>
</head>
<body>
  <div class="orb o1"></div><div class="orb o2"></div>
  <div class="wrap">
    <div class="logo-row">
      <div class="logo-icon">🤖</div>
      <div class="logo-title">DevOps Agent</div>
      <div class="logo-sub">Autonomous Incident Response</div>
    </div>
    <div class="card">
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}{% for cat,msg in messages %}
          <div class="alert alert-{{cat}}">{{msg}}</div>
        {% endfor %}{% endif %}
      {% endwith %}
      <form method="POST">
        <div class="fg">
          <label>Username</label>
          <input type="text" name="username" placeholder="Enter username" required autofocus/>
        </div>
        <div class="fg">
          <label>Password</label>
          <input type="password" name="password" placeholder="Enter password" required/>
        </div>
        <button class="btn" type="submit">→ Sign In</button>
      </form>
      <div class="demo">
        <div class="demo-title">⚡ Demo Credentials</div>
        <div class="cr"><span class="rb ra">Admin</span><span>admin</span><span class="cm">/ admin123</span></div>
        <div class="cr"><span class="rb re">Engineer</span><span>engineer</span><span class="cm">/ eng123</span></div>
        <div class="cr"><span class="rb rv">Viewer</span><span>viewer</span><span class="cm">/ view123</span></div>
      </div>
    </div>
  </div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>AI DevOps Incident Response Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@600;700;800&display=swap" rel="stylesheet"/>
    <style>
        :root {
          --bg:#0a0e1a; --sidebar:#0d1220; --card:#0f1628;
          --border:#1e2d4a; --accent:#00d4ff; --accent2:#7c3aed;
          --danger:#ef4444; --success:#22c55e; --warning:#f59e0b;
          --text:#e2e8f0; --muted:#64748b;
        }
        *{margin:0;padding:0;box-sizing:border-box;}
        body{background:var(--bg);color:var(--text);font-family:'Syne',sans-serif;
             min-height:100vh;display:flex;}

        /* Sidebar */
        .sidebar{width:230px;min-height:100vh;background:var(--sidebar);
          border-right:1px solid var(--border);display:flex;flex-direction:column;
          padding:22px 14px;position:fixed;top:0;left:0;height:100vh;}
        .slogo{display:flex;align-items:center;gap:10px;margin-bottom:28px;padding:0 6px;}
        .slogo-icon{width:34px;height:34px;background:linear-gradient(135deg,var(--accent),var(--accent2));
          border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;}
        .slogo-name{font-size:14px;font-weight:800;background:linear-gradient(135deg,var(--accent),#fff);
          -webkit-background-clip:text;-webkit-text-fill-color:transparent;}
        .nsec{font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:2px;
          color:var(--muted);text-transform:uppercase;padding:0 6px;margin:14px 0 6px;}
        .nitem{display:flex;align-items:center;gap:8px;padding:9px 10px;border-radius:7px;
          color:var(--muted);font-size:13px;text-decoration:none;margin-bottom:2px;transition:.15s;}
        .nitem:hover,.nitem.active{background:rgba(0,212,255,.08);color:var(--accent);}
        .sf{margin-top:auto;padding:14px 6px 0;border-top:1px solid var(--border);}
        .uinfo{display:flex;align-items:center;gap:8px;margin-bottom:10px;}
        .avatar{width:30px;height:30px;border-radius:7px;
          background:linear-gradient(135deg,var(--accent2),var(--accent));
          display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;}
        .uname{font-size:13px;font-weight:700;}
        .urole{font-size:10px;font-family:'JetBrains Mono',monospace;}
        .role-admin   {color:#fca5a5;} .role-engineer{color:#fcd34d;} .role-viewer{color:#86efac;}
        .btnlo{width:100%;padding:7px;border-radius:6px;background:rgba(239,68,68,.1);
          border:1px solid rgba(239,68,68,.2);color:#fca5a5;font-size:12px;font-family:'Syne',sans-serif;
          cursor:pointer;transition:.15s;text-align:center;text-decoration:none;display:block;}
        .btnlo:hover{background:rgba(239,68,68,.2);}

        /* Main */
        .main{margin-left:230px;flex:1;padding:28px;overflow-y:auto;}
        .phead{display:flex;align-items:center;justify-content:space-between;margin-bottom:28px;}
        .ptitle{font-size:22px;font-weight:800;}
        .psub{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);margin-top:3px;}
        .rbadge{padding:4px 12px;border-radius:6px;font-family:'JetBrains Mono',monospace;
          font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;}
        .rbadge-admin   {background:rgba(239,68,68,.15);color:#fca5a5;border:1px solid rgba(239,68,68,.3);}
        .rbadge-engineer{background:rgba(245,158,11,.15);color:#fcd34d;border:1px solid rgba(245,158,11,.3);}
        .rbadge-viewer  {background:rgba(34,197,94,.15);color:#86efac;border:1px solid rgba(34,197,94,.3);}

        /* Flash */
        .flash{padding:12px 16px;border-radius:8px;margin-bottom:18px;
          font-family:'JetBrains Mono',monospace;font-size:13px;}
        .flash-success{background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);color:#86efac;}
        .flash-danger {background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:#fca5a5;}

        /* Permission notice */
        .pnotice{background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.2);
          border-radius:10px;padding:12px 16px;font-family:'JetBrains Mono',monospace;
          font-size:12px;color:#fcd34d;margin-bottom:20px;}

        /* Stats */
        .sgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px;}
        .sc{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;
          transition:.2s;}
        .sc:hover{border-color:rgba(0,212,255,.3);}
        .sc .num{font-size:30px;font-weight:800;}
        .sc .lbl{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);
          text-transform:uppercase;letter-spacing:1.5px;margin-bottom:6px;}
        .sc .sub{font-size:11px;color:var(--muted);margin-top:4px;}
        .td{color:var(--danger);} .ts{color:var(--success);} .tw{color:var(--warning);} .ta{color:var(--accent);}

        /* Agents */
        .agrid{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:24px;}
        .ac{background:var(--card);border:1px solid var(--border);border-radius:12px;
          padding:16px;text-align:center;}
        .ac .aicon{font-size:26px;margin-bottom:8px;}
        .ac .aname{font-size:11px;font-weight:700;color:var(--accent);}
        .ac .abadge{background:rgba(34,197,94,.15);color:#86efac;border:1px solid rgba(34,197,94,.3);
          font-size:10px;padding:2px 8px;border-radius:10px;margin-top:6px;display:inline-block;
          font-family:'JetBrains Mono',monospace;}

        /* Pipeline */
        .pipeline{background:var(--card);border:1px solid var(--border);
          border-radius:12px;padding:20px;margin-bottom:24px;}
        .psteps{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:14px;}
        .pstep{background:rgba(255,255,255,.03);border:1px solid var(--border);
          border-radius:8px;padding:10px 14px;font-size:12px;text-align:center;}
        .pstep .si{font-size:20px;}
        .pstep .sn{color:var(--accent);margin-top:4px;font-size:11px;}
        .parrow{color:var(--muted);font-size:18px;}

        /* Actions */
        .arow{display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap;}
        .abtn{padding:12px 22px;border-radius:8px;font-family:'Syne',sans-serif;
          font-size:13px;font-weight:700;cursor:pointer;border:none;transition:.15s;
          display:flex;align-items:center;gap:8px;}
        .abtn-run{background:linear-gradient(135deg,var(--accent),#0099cc);color:#000;
          box-shadow:0 4px 15px rgba(0,212,255,.3);}
        .abtn-run:hover{box-shadow:0 4px 25px rgba(0,212,255,.5);opacity:.9;}
        .abtn-eng{background:rgba(245,158,11,.15);border:1px solid rgba(245,158,11,.3);color:#fcd34d;}
        .abtn-eng:hover{background:rgba(245,158,11,.25);}
        .abtn-view{background:rgba(0,212,255,.1);border:1px solid rgba(0,212,255,.3);color:var(--accent);}
        .abtn-view:hover{background:rgba(0,212,255,.18);}
        .abtn-dis{background:rgba(255,255,255,.04);border:1px solid var(--border);
          color:var(--muted);cursor:not-allowed;opacity:.5;}

        /* Table */
        .stitle{font-size:15px;font-weight:700;margin-bottom:14px;
          display:flex;align-items:center;gap:8px;}
        .twrap{background:var(--card);border:1px solid var(--border);
          border-radius:12px;overflow:hidden;}
        table{width:100%;border-collapse:collapse;}
        th{background:rgba(255,255,255,.02);font-family:'JetBrains Mono',monospace;
          font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);
          padding:12px 18px;text-align:left;}
        td{padding:13px 18px;border-top:1px solid var(--border);font-size:13px;}
        tr:hover td{background:rgba(255,255,255,.02);}
        .sev-high    {background:rgba(239,68,68,.15);color:#fca5a5;padding:3px 8px;
          border-radius:4px;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;}
        .sev-critical{background:rgba(239,68,68,.2);color:#ef4444;padding:3px 8px;
          border-radius:4px;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;}
        .sev-medium  {background:rgba(96,165,250,.15);color:#93c5fd;padding:3px 8px;
          border-radius:4px;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;}
        .dot-ok {display:inline-flex;align-items:center;gap:5px;font-family:'JetBrains Mono',monospace;font-size:12px;}
        .dot-ok::before{content:'';width:6px;height:6px;border-radius:50%;
          background:var(--success);box-shadow:0 0 6px var(--success);display:inline-block;}
        .empty{text-align:center;padding:36px;color:var(--muted);
          font-family:'JetBrains Mono',monospace;font-size:12px;}
    </style>
</head>
<body>

<!-- Sidebar -->
<nav class="sidebar">
  <div class="slogo">
    <div class="slogo-icon">🤖</div>
    <div class="slogo-name">DevOps Agent</div>
  </div>

  <span class="nsec">Monitoring</span>
  <a class="nitem active" href="#">📊 Dashboard</a>
  <a class="nitem" href="#">🔔 Incidents</a>
  <a class="nitem" href="#">📈 Metrics</a>

  <span class="nsec">Agents</span>
  <a class="nitem" href="#">👁️ Monitor</a>
  <a class="nitem" href="#">🔍 Investigation</a>
  <a class="nitem" href="#">🔧 Remediation</a>
  <a class="nitem" href="#">📄 Post-Mortem</a>

  {% if current_user.is_admin() %}
  <span class="nsec">Admin</span>
  <a class="nitem" href="#">👥 Manage Users</a>
  <a class="nitem" href="#">⚙️ Settings</a>
  {% endif %}

  <div class="sf">
    <div class="uinfo">
      <div class="avatar">{{ current_user.username[0].upper() }}</div>
      <div>
        <div class="uname">{{ current_user.username }}</div>
        <div class="urole role-{{ current_user.role }}">{{ current_user.role.upper() }}</div>
      </div>
    </div>
    <a href="/logout" class="btnlo">⏏ Logout</a>
  </div>
</nav>

<!-- Main -->
<main class="main">

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}{% for cat,msg in messages %}
      <div class="flash flash-{{cat}}">{{msg}}</div>
    {% endfor %}{% endif %}
  {% endwith %}

  {% if current_user.role == 'viewer' %}
  <div class="pnotice">⚠️ Viewer access — you can monitor but cannot trigger actions.</div>
  {% endif %}

  <div class="phead">
    <div>
      <div class="ptitle">Incident Dashboard</div>
      <div class="psub">AUTONOMOUS DEVOPS RESPONSE SYSTEM · LIVE</div>
    </div>
    <span class="rbadge rbadge-{{ current_user.role }}">{{ current_user.role }}</span>
  </div>

  <!-- Stats -->
  <div class="sgrid">
    <div class="sc">
      <div class="lbl">Total Incidents</div>
      <div class="num ta" id="total-incidents">0</div>
      <div class="sub">since last restart</div>
    </div>
    <div class="sc">
      <div class="lbl">Active Agents</div>
      <div class="num ts">5</div>
      <div class="sub">all operational ✅</div>
    </div>
    <div class="sc">
      <div class="lbl">Check Interval</div>
      <div class="num tw">60s</div>
      <div class="sub">auto-monitoring</div>
    </div>
    <div class="sc">
      <div class="lbl">High Severity</div>
      <div class="num td" id="high-count">0</div>
      <div class="sub">critical + high</div>
    </div>
  </div>

  <!-- Agent status -->
  <div class="stitle">🤖 Agent Status</div>
  <div class="agrid">
    <div class="ac"><div class="aicon">👁️</div><div class="aname">Monitor</div><div class="abadge">● Active</div></div>
    <div class="ac"><div class="aicon">🔍</div><div class="aname">Investigation</div><div class="abadge">● Active</div></div>
    <div class="ac"><div class="aicon">🔧</div><div class="aname">Remediation</div><div class="abadge">● Active</div></div>
    <div class="ac"><div class="aicon">🚨</div><div class="aname">Escalation</div><div class="abadge">● Active</div></div>
    <div class="ac"><div class="aicon">📄</div><div class="aname">Post-Mortem</div><div class="abadge">● Active</div></div>
  </div>

  <!-- Pipeline -->
  <div class="pipeline">
    <div class="stitle">⚙️ Pipeline Flow</div>
    <div class="psteps">
      <div class="pstep"><div class="si">👁️</div><div class="sn">Monitor</div></div>
      <div class="parrow">→</div>
      <div class="pstep"><div class="si">🔍</div><div class="sn">Investigate</div></div>
      <div class="parrow">→</div>
      <div class="pstep"><div class="si">🔧</div><div class="sn">Remediate</div></div>
      <div class="parrow">→</div>
      <div class="pstep"><div class="si">🚨</div><div class="sn">Escalate</div></div>
      <div class="parrow">→</div>
      <div class="pstep"><div class="si">📄</div><div class="sn">Post-Mortem</div></div>
    </div>
  </div>

  <!-- Actions — role gated -->
  <div class="arow">
    {% if current_user.is_admin() %}
      <button class="abtn abtn-run" onclick="runPipeline()">🚀 Run Full Pipeline</button>
    {% else %}
      <button class="abtn abtn-dis" disabled>🔒 Run Pipeline (Admin only)</button>
    {% endif %}

    {% if current_user.is_engineer() %}
      <button class="abtn abtn-eng" onclick="triggerRemediation()">🔧 Trigger Remediation</button>
    {% else %}
      <button class="abtn abtn-dis" disabled>🔒 Remediation (Engineer+)</button>
    {% endif %}

    <button class="abtn abtn-view" onclick="loadIncidents()">📋 Refresh Incidents</button>
  </div>

  <!-- Incidents table -->
  <div class="stitle">📋 Incident History</div>
  <div class="twrap">
    <table>
      <thead>
        <tr>
          <th>Time</th><th>Root Cause</th><th>Severity</th><th>Jira Ticket</th><th>Status</th>
        </tr>
      </thead>
      <tbody id="incidents-body">
        <tr><td colspan="5" class="empty">No incidents yet — click Run Pipeline to start!</td></tr>
      </tbody>
    </table>
  </div>
</main>

<script>
  function runPipeline() {
  const btn = document.querySelector('.abtn-run');
  btn.textContent = '⏳ Running...';
  btn.disabled = true;
  fetch('/api/run-pipeline', {method:'POST'})
    .then(r => r.json())
    .then(data => {
      btn.textContent = '🚀 Run Full Pipeline';
      btn.disabled = false;
      if(data.error) {
        alert('❌ Error:\n' + data.error);
      } else if(data.status === 'healthy') {
        alert('✅ Pipeline ran!\n\nResult: All systems healthy — no incidents detected.\nCPU is normal, no Lambda errors.');
      } else {
        alert('🚨 Incident handled!\nRoot cause: ' + data.root_cause + '\nSeverity: ' + data.severity);
        loadIncidents();
      }
    }).catch(e => {
      btn.textContent = '🚀 Run Full Pipeline';
      btn.disabled = false;
      alert('❌ Network error: ' + e);
    });
}

  function triggerRemediation() {
    alert('🔧 Remediation triggered by ' + '{{ current_user.username }}');
  }

  function loadIncidents() {
    fetch('/api/incidents').then(r=>r.json()).then(incidents=>{
      document.getElementById('total-incidents').textContent = incidents.length;
      let high = incidents.filter(i=>['high','critical'].includes((i.severity||'').toLowerCase())).length;
      document.getElementById('high-count').textContent = high;
      let tbody = document.getElementById('incidents-body');
      if(!incidents.length){
        tbody.innerHTML='<tr><td colspan="5" class="empty">No incidents yet — click Run Pipeline to start!</td></tr>';
        return;
      }
      tbody.innerHTML = [...incidents].reverse().map(i=>`
        <tr>
          <td style="font-family:monospace;font-size:12px;color:var(--muted)">${i.time}</td>
          <td>${i.root_cause}</td>
          <td><span class="sev-${(i.severity||'medium').toLowerCase()}">${(i.severity||'MEDIUM').toUpperCase()}</span></td>
          <td style="font-family:monospace;font-size:12px">${i.jira_ticket||'N/A'}</td>
          <td><span class="dot-ok">Resolved</span></td>
        </tr>`).join('');
    });
  }

  setInterval(loadIncidents, 5000);
  loadIncidents();
</script>
</body>
</html>
"""

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = get_user_by_username(username)
        if user and user.check_password(password):
            login_user(user, remember=True)
            flash(f'✅ Welcome, {user.username}! Logged in as {user.role.upper()}.', 'success')
            return redirect(url_for('dashboard'))
        flash('❌ Invalid username or password.', 'danger')
    return render_template_string(LOGIN_HTML)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('👋 Logged out successfully.', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template_string(DASHBOARD_HTML)


# ─── API Routes ───────────────────────────────────────────────────────────────

@app.route('/api/run-pipeline', methods=['POST'])
@admin_required                          # ← Only Admin can trigger pipeline
def run_pipeline_api():
    try:
        import sys
        sys.path.append('.')
        from agents.monitor_agent import MonitorAgent
        from agents.investigation_agent import InvestigationAgent
        from agents.remediation_agent import RemediationAgent
        from agents.escalation_agent import EscalationAgent
        from agents.postmortem_agent import PostMortemAgent
        from factory import AgentFactory
        from observer import event_system
        from strategy import StrategySelector

        monitor = AgentFactory.create_agent("monitor")
        alerts = monitor.run()
        if not alerts:
            return jsonify({"message": "No alerts", "status": "healthy"})

        event_system.publish("alert_detected", alerts)

        investigator = AgentFactory.create_agent("investigation")
        diagnosis = investigator.investigate(alerts)
        event_system.publish("diagnosis_complete", diagnosis)

        if diagnosis.get('auto_fixable'):
            strategy = StrategySelector.select(diagnosis['root_cause'])
            result = strategy.execute(diagnosis['affected_service'])
        else:
            remediator = AgentFactory.create_agent("remediation")
            result = remediator.remediate(diagnosis)

        escalation = None
        if result.get('status') == 'escalate' or not diagnosis.get('auto_fixable'):
            escalator = AgentFactory.create_agent("escalation")
            escalation = escalator.escalate(diagnosis, alerts)
            event_system.publish("escalation_complete", escalation)

        postmortem = AgentFactory.create_agent("postmortem")
        postmortem.generate(diagnosis, alerts, result)

        incident = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "root_cause": diagnosis.get('root_cause', 'Unknown'),
            "severity": diagnosis.get('severity', 'medium'),
            "jira_ticket": escalation.get('jira_ticket') if escalation else 'Auto-Fixed',
            "status": "resolved",
            "triggered_by": current_user.username    # ← track who ran it
        }
        incidents_db.append(incident)
        return jsonify(incident)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/incidents')
@login_required                          # ← All roles can view incidents
def get_incidents():
    return jsonify(incidents_db)


@app.route('/api/status')
@login_required
def get_status():
    return jsonify({
        "status": "running",
        "agents": 5,
        "incidents": len(incidents_db),
        "last_check": str(datetime.now())
    })


# ─── Run ──────────────────────────────────────────────────────────────────────
@app.route('/api/demo-incident', methods=['POST'])
@login_required
def demo_incident():
    """Simulates a CRITICAL incident for demo purposes — all 5 agents fire."""
    try:
        import sys
        sys.path.append('.')
        from agents.monitor_agent import MonitorAgent
        from agents.investigation_agent import InvestigationAgent
        from agents.remediation_agent import RemediationAgent
        from agents.escalation_agent import EscalationAgent
        from agents.postmortem_agent import PostMortemAgent
        from factory import AgentFactory
        from observer import event_system

        # Force threshold low so alert triggers
        monitor = AgentFactory.create_agent("monitor")
        monitor.cpu_threshold = 0.1
        alerts = monitor.run()

        if not alerts:
            alerts = [{'type': 'HIGH_CPU', 'value': 99.9, 'threshold': 80,
                       'message': 'CPU usage 99.9% exceeds threshold 80%'}]

        event_system.publish("alert_detected", alerts)

        investigator = AgentFactory.create_agent("investigation")
        diagnosis = investigator.investigate(alerts)
        diagnosis['severity'] = 'CRITICAL'

        event_system.publish("diagnosis_complete", diagnosis)

        remediator = AgentFactory.create_agent("remediation")
        result = remediator.remediate(diagnosis)

        escalator = AgentFactory.create_agent("escalation")
        escalation = escalator.escalate(diagnosis, alerts)
        event_system.publish("escalation_complete", escalation)

        postmortem = AgentFactory.create_agent("postmortem")
        postmortem.generate(diagnosis, alerts, result)

        incident = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "root_cause": diagnosis.get('root_cause', 'High CPU — demo incident'),
            "severity": "CRITICAL",
            "jira_ticket": escalation.get('jira_ticket', 'DEMO-001') if escalation else 'DEMO-001',
            "status": "resolved",
            "triggered_by": current_user.username
        }
        incidents_db.append(incident)
        return jsonify({"success": True, "incident": incident})

    except Exception as e:
        return jsonify({"error": str(e)}), 500if __name__ == '__main__':
    print("=" * 50)
    print("  🤖 AI DevOps Dashboard  —  With Auth")
    print("=" * 50)
    print("  URL   : http://localhost:5000")
    print("  Admin : admin / admin123")
    print("  Eng   : engineer / eng123")
    print("  View  : viewer / view123")
    print("=" * 50)
    app.run(debug=True, port=5000)