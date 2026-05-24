"""
dashboard.py — AI DevOps Incident Response System
Flask-Login + RBAC + SQLite DB + Search/Filter + CSV Export
+ Flask-SocketIO Live Push Notifications + Bell Badge + Sound Alerts
+ Chart.js CPU History Line Chart + Incident Severity Pie Chart
"""

from flask import Flask, jsonify, render_template_string, redirect, url_for, request, flash, Response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from functools import wraps
from datetime import datetime
import csv
import io
import os
import random

app = Flask(__name__)
app.secret_key = "devops-agent-secret-key-change-in-prod"

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///devops_incidents.db')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db       = SQLAlchemy(app)
bcrypt   = Bcrypt(app)
socketio = SocketIO(app, cors_allowed_origins="*")

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access the dashboard."

# ── Models ────────────────────────────────────────────────────────────────────
class Incident(db.Model):
    __tablename__ = 'incidents'
    id           = db.Column(db.Integer, primary_key=True)
    time         = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    root_cause   = db.Column(db.String(500), nullable=False)
    severity     = db.Column(db.String(50), nullable=False)
    jira_ticket  = db.Column(db.String(100))
    status       = db.Column(db.String(50), default='resolved')
    triggered_by = db.Column(db.String(100))
    service_name = db.Column(db.String(200))

    def to_dict(self):
        return {
            'id':           self.id,
            'time':         self.time.strftime("%Y-%m-%d %H:%M:%S"),
            'root_cause':   self.root_cause,
            'severity':     self.severity,
            'jira_ticket':  self.jira_ticket or 'N/A',
            'status':       self.status,
            'triggered_by': self.triggered_by or 'system',
            'service_name': self.service_name or 'unknown',
        }

# In-memory CPU history (last 10 readings)
cpu_history = {"labels": [], "values": []}

with app.app_context():
    db.create_all()

# ── Users ─────────────────────────────────────────────────────────────────────
class User(UserMixin):
    def __init__(self, id, username, password_hash, role):
        self.id = id; self.username = username
        self.password_hash = password_hash; self.role = role
    def check_password(self, pw): return bcrypt.check_password_hash(self.password_hash, pw)
    def is_admin(self):    return self.role == "admin"
    def is_engineer(self): return self.role in ("admin", "engineer")

USERS = {
    "1": User("1", "admin",    bcrypt.generate_password_hash("admin123").decode(), "admin"),
    "2": User("2", "engineer", bcrypt.generate_password_hash("eng123").decode(),   "engineer"),
    "3": User("3", "viewer",   bcrypt.generate_password_hash("view123").decode(),  "viewer"),
}
def get_user_by_username(u): return next((x for x in USERS.values() if x.username == u), None)

@login_manager.user_loader
def load_user(user_id): return USERS.get(user_id)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated: return jsonify({"error": "Please log in"}), 401
        if not current_user.is_admin():       return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated

def save_and_push(root_cause, severity, jira_ticket, triggered_by, service_name):
    incident = Incident(root_cause=root_cause, severity=severity, jira_ticket=jira_ticket,
                        status='resolved', triggered_by=triggered_by, service_name=service_name)
    db.session.add(incident)
    db.session.commit()
    socketio.emit('new_incident', incident.to_dict())
    # Push updated chart data
    socketio.emit('severity_update', get_severity_counts())
    return incident

def get_severity_counts():
    counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    for inc in Incident.query.all():
        key = (inc.severity or '').upper()
        if key in counts: counts[key] += 1
    return counts

# ── LOGIN HTML ────────────────────────────────────────────────────────────────
LOGIN_HTML = """
<!DOCTYPE html><html lang="en"><head>
  <meta charset="UTF-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>DevOps Agent - Login</title>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Syne:wght@700;800&display=swap" rel="stylesheet"/>
  <style>
    :root{--bg:#0a0e1a;--card:#0f1628;--border:#1e2d4a;--accent:#00d4ff;--accent2:#7c3aed;--text:#e2e8f0;--muted:#64748b;}
    *{margin:0;padding:0;box-sizing:border-box;}
    body{background:var(--bg);color:var(--text);font-family:'Syne',sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;overflow:hidden;}
    body::before{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,212,255,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(0,212,255,.04) 1px,transparent 1px);background-size:40px 40px;animation:gridMove 20s linear infinite;}
    @keyframes gridMove{to{transform:translateY(40px);}}
    .orb{position:fixed;border-radius:50%;filter:blur(80px);opacity:.15;pointer-events:none;}
    .o1{width:400px;height:400px;background:var(--accent);top:-100px;right:-100px;}
    .o2{width:300px;height:300px;background:var(--accent2);bottom:-80px;left:-80px;}
    .wrap{position:relative;z-index:10;width:100%;max-width:420px;padding:20px;}
    .logo-row{text-align:center;margin-bottom:28px;}
    .logo-icon{width:52px;height:52px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:14px;display:inline-flex;align-items:center;justify-content:center;font-size:26px;box-shadow:0 0 24px rgba(0,212,255,.35);margin-bottom:12px;}
    .logo-title{font-size:22px;font-weight:800;background:linear-gradient(135deg,var(--accent),#fff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
    .logo-sub{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);letter-spacing:2px;text-transform:uppercase;margin-top:4px;}
    .card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:32px;box-shadow:0 0 40px rgba(0,0,0,.5);}
    .alert{padding:12px 16px;border-radius:8px;font-size:13px;margin-bottom:18px;font-family:'JetBrains Mono',monospace;}
    .alert-danger{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:#fca5a5;}
    .alert-success{background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);color:#86efac;}
    .fg{margin-bottom:20px;}
    label{display:block;font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);margin-bottom:8px;}
    input{width:100%;background:rgba(255,255,255,.03);border:1px solid var(--border);border-radius:8px;padding:12px 16px;color:var(--text);font-family:'JetBrains Mono',monospace;font-size:14px;transition:.2s;outline:none;}
    input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(0,212,255,.1);}
    input::placeholder{color:var(--muted);}
    .btn{width:100%;padding:14px;background:linear-gradient(135deg,var(--accent),#0099cc);border:none;border-radius:8px;color:#000;font-family:'Syne',sans-serif;font-size:15px;font-weight:700;cursor:pointer;}
    .demo{margin-top:22px;padding:16px;background:rgba(255,255,255,.02);border:1px solid var(--border);border-radius:10px;}
    .demo-title{font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:2px;color:var(--muted);text-transform:uppercase;margin-bottom:12px;}
    .cr{display:flex;align-items:center;gap:8px;margin-bottom:8px;font-family:'JetBrains Mono',monospace;font-size:12px;}
    .rb{padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;min-width:72px;text-align:center;}
    .ra{background:rgba(239,68,68,.2);color:#fca5a5;border:1px solid rgba(239,68,68,.3);}
    .re{background:rgba(245,158,11,.2);color:#fcd34d;border:1px solid rgba(245,158,11,.3);}
    .rv{background:rgba(34,197,94,.2);color:#86efac;border:1px solid rgba(34,197,94,.3);}
    .cm{color:var(--muted);}
  </style>
</head><body>
  <div class="orb o1"></div><div class="orb o2"></div>
  <div class="wrap">
    <div class="logo-row">
      <div class="logo-icon">&#x1F916;</div>
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
        <div class="fg"><label>Username</label><input type="text" name="username" placeholder="Enter username" required autofocus/></div>
        <div class="fg"><label>Password</label><input type="password" name="password" placeholder="Enter password" required/></div>
        <button class="btn" type="submit">Sign In</button>
      </form>
      <div class="demo">
        <div class="demo-title">Demo Credentials</div>
        <div class="cr"><span class="rb ra">Admin</span><span>admin</span><span class="cm">/ admin123</span></div>
        <div class="cr"><span class="rb re">Engineer</span><span>engineer</span><span class="cm">/ eng123</span></div>
        <div class="cr"><span class="rb rv">Viewer</span><span>viewer</span><span class="cm">/ view123</span></div>
      </div>
    </div>
  </div>
</body></html>
"""

# ── DASHBOARD HTML ────────────────────────────────────────────────────────────
DASHBOARD_HTML = """
<!DOCTYPE html><html lang="en"><head>
    <title>AI DevOps Incident Response Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@600;700;800&display=swap" rel="stylesheet"/>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.5/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        :root{--bg:#0a0e1a;--sidebar:#0d1220;--card:#0f1628;--border:#1e2d4a;--accent:#00d4ff;--accent2:#7c3aed;--danger:#ef4444;--success:#22c55e;--warning:#f59e0b;--text:#e2e8f0;--muted:#64748b;}
        *{margin:0;padding:0;box-sizing:border-box;}
        body{background:var(--bg);color:var(--text);font-family:'Syne',sans-serif;min-height:100vh;display:flex;}
        .sidebar{width:230px;min-height:100vh;background:var(--sidebar);border-right:1px solid var(--border);display:flex;flex-direction:column;padding:22px 14px;position:fixed;top:0;left:0;height:100vh;}
        .slogo{display:flex;align-items:center;gap:10px;margin-bottom:28px;padding:0 6px;}
        .slogo-icon{width:34px;height:34px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;}
        .slogo-name{font-size:14px;font-weight:800;background:linear-gradient(135deg,var(--accent),#fff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
        .nsec{font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:2px;color:var(--muted);text-transform:uppercase;padding:0 6px;margin:14px 0 6px;}
        .nitem{display:flex;align-items:center;gap:8px;padding:9px 10px;border-radius:7px;color:var(--muted);font-size:13px;text-decoration:none;margin-bottom:2px;transition:.15s;}
        .nitem:hover,.nitem.active{background:rgba(0,212,255,.08);color:var(--accent);}
        .sf{margin-top:auto;padding:14px 6px 0;border-top:1px solid var(--border);}
        .uinfo{display:flex;align-items:center;gap:8px;margin-bottom:10px;}
        .avatar{width:30px;height:30px;border-radius:7px;background:linear-gradient(135deg,var(--accent2),var(--accent));display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;}
        .uname{font-size:13px;font-weight:700;}.urole{font-size:10px;font-family:'JetBrains Mono',monospace;}
        .role-admin{color:#fca5a5;}.role-engineer{color:#fcd34d;}.role-viewer{color:#86efac;}
        .btnlo{width:100%;padding:7px;border-radius:6px;background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.2);color:#fca5a5;font-size:12px;font-family:'Syne',sans-serif;cursor:pointer;text-align:center;text-decoration:none;display:block;}
        .main{margin-left:230px;flex:1;padding:28px;overflow-y:auto;}
        .phead{display:flex;align-items:center;justify-content:space-between;margin-bottom:28px;}
        .ptitle{font-size:22px;font-weight:800;}
        .psub{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);margin-top:3px;}
        .head-right{display:flex;align-items:center;gap:12px;}
        .bell-wrap{position:relative;cursor:pointer;}
        .bell-btn{background:var(--card);border:1px solid var(--border);border-radius:8px;width:40px;height:40px;display:flex;align-items:center;justify-content:center;font-size:18px;transition:.2s;cursor:pointer;}
        .bell-btn:hover{border-color:var(--accent);}
        .bell-btn.ringing{animation:ring 0.5s ease-in-out;}
        @keyframes ring{0%{transform:rotate(0);}20%{transform:rotate(-20deg);}40%{transform:rotate(20deg);}60%{transform:rotate(-15deg);}80%{transform:rotate(10deg);}100%{transform:rotate(0);}}
        .bell-badge{position:absolute;top:-6px;right:-6px;background:var(--danger);color:#fff;font-size:10px;font-weight:700;font-family:'JetBrains Mono',monospace;min-width:18px;height:18px;border-radius:9px;display:none;align-items:center;justify-content:center;padding:0 4px;border:2px solid var(--bg);}
        .bell-badge.show{display:flex;}
        .notif-panel{position:fixed;top:70px;right:20px;width:360px;background:var(--card);border:1px solid var(--border);border-radius:12px;box-shadow:0 8px 40px rgba(0,0,0,.6);z-index:1000;display:none;max-height:480px;overflow:hidden;flex-direction:column;}
        .notif-panel.open{display:flex;}
        .notif-header{padding:14px 18px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
        .notif-title{font-size:14px;font-weight:700;}
        .notif-clear{font-family:'JetBrains Mono',monospace;font-size:11px;cursor:pointer;background:none;border:none;color:var(--accent);}
        .notif-list{overflow-y:auto;flex:1;}
        .notif-item{padding:14px 18px;border-bottom:1px solid var(--border);display:flex;gap:12px;align-items:flex-start;}
        .notif-item.unread{background:rgba(0,212,255,.04);}
        .notif-dot{width:8px;height:8px;border-radius:50%;margin-top:5px;flex-shrink:0;}
        .notif-dot-critical{background:var(--danger);box-shadow:0 0 6px var(--danger);}
        .notif-dot-high{background:var(--warning);}
        .notif-dot-medium{background:#60a5fa;}
        .notif-dot-low{background:var(--success);}
        .notif-body{flex:1;}
        .notif-msg{font-size:13px;margin-bottom:4px;}
        .notif-time{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);}
        .notif-empty{padding:30px;text-align:center;color:var(--muted);font-family:'JetBrains Mono',monospace;font-size:12px;}
        .live-dot{display:inline-flex;align-items:center;gap:6px;font-family:'JetBrains Mono',monospace;font-size:11px;color:#86efac;}
        .live-dot::before{content:'';width:7px;height:7px;border-radius:50%;background:var(--success);box-shadow:0 0 8px var(--success);display:inline-block;animation:livepulse 1.5s infinite;}
        @keyframes livepulse{0%,100%{opacity:1;}50%{opacity:.3;}}
        .toast-container{position:fixed;top:20px;right:20px;z-index:2000;display:flex;flex-direction:column;gap:10px;}
        .toast{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px 18px;min-width:300px;box-shadow:0 4px 20px rgba(0,0,0,.5);display:flex;gap:12px;align-items:flex-start;animation:slideIn .3s ease;border-left:3px solid var(--accent);}
        .toast.critical{border-left-color:var(--danger);}
        .toast.high{border-left-color:var(--warning);}
        @keyframes slideIn{from{transform:translateX(120%);opacity:0;}to{transform:translateX(0);opacity:1;}}
        .toast-icon{font-size:20px;}.toast-body{flex:1;}
        .toast-title{font-size:13px;font-weight:700;margin-bottom:3px;}
        .toast-msg{font-size:12px;color:var(--muted);}
        .toast-close{cursor:pointer;color:var(--muted);font-size:16px;background:none;border:none;}
        .rbadge{padding:4px 12px;border-radius:6px;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;}
        .rbadge-admin{background:rgba(239,68,68,.15);color:#fca5a5;border:1px solid rgba(239,68,68,.3);}
        .rbadge-engineer{background:rgba(245,158,11,.15);color:#fcd34d;border:1px solid rgba(245,158,11,.3);}
        .rbadge-viewer{background:rgba(34,197,94,.15);color:#86efac;border:1px solid rgba(34,197,94,.3);}
        .db-badge{display:inline-flex;align-items:center;gap:6px;font-family:'JetBrains Mono',monospace;font-size:11px;color:#86efac;background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);padding:4px 10px;border-radius:6px;}
        .flash{padding:12px 16px;border-radius:8px;margin-bottom:18px;font-family:'JetBrains Mono',monospace;font-size:13px;}
        .flash-success{background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);color:#86efac;}
        .flash-danger{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:#fca5a5;}
        .pnotice{background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.2);border-radius:10px;padding:12px 16px;font-family:'JetBrains Mono',monospace;font-size:12px;color:#fcd34d;margin-bottom:20px;}
        .sgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px;}
        .sc{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;transition:.2s;}
        .sc:hover{border-color:rgba(0,212,255,.3);}
        .sc .num{font-size:30px;font-weight:800;}
        .sc .lbl{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:6px;}
        .sc .sub{font-size:11px;color:var(--muted);margin-top:4px;}
        .td{color:var(--danger);}.ts{color:var(--success);}.tw{color:var(--warning);}.ta{color:var(--accent);}
        /* Charts grid */
        .charts-grid{display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:24px;}
        .chart-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;}
        .chart-title{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;}
        .chart-title span{color:var(--accent);}
        .chart-wrap{position:relative;height:200px;}
        .agrid{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:24px;}
        .ac{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;text-align:center;}
        .ac .aicon{font-size:26px;margin-bottom:8px;}
        .ac .aname{font-size:11px;font-weight:700;color:var(--accent);}
        .ac .abadge{background:rgba(34,197,94,.15);color:#86efac;border:1px solid rgba(34,197,94,.3);font-size:10px;padding:2px 8px;border-radius:10px;margin-top:6px;display:inline-block;font-family:'JetBrains Mono',monospace;}
        .pipeline{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:24px;}
        .psteps{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:14px;}
        .pstep{background:rgba(255,255,255,.03);border:1px solid var(--border);border-radius:8px;padding:10px 14px;font-size:12px;text-align:center;}
        .pstep .si{font-size:20px;}.pstep .sn{color:var(--accent);margin-top:4px;font-size:11px;}
        .parrow{color:var(--muted);font-size:18px;}
        .arow{display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap;}
        .abtn{padding:12px 22px;border-radius:8px;font-family:'Syne',sans-serif;font-size:13px;font-weight:700;cursor:pointer;border:none;transition:.15s;display:inline-flex;align-items:center;gap:8px;text-decoration:none;}
        .abtn-run{background:linear-gradient(135deg,var(--accent),#0099cc);color:#000;box-shadow:0 4px 15px rgba(0,212,255,.3);}
        .abtn-run:hover{box-shadow:0 4px 25px rgba(0,212,255,.5);opacity:.9;}
        .abtn-demo{background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.4);color:#fca5a5;}
        .abtn-demo:hover{background:rgba(239,68,68,.25);}
        .abtn-eng{background:rgba(245,158,11,.15);border:1px solid rgba(245,158,11,.3);color:#fcd34d;}
        .abtn-view{background:rgba(0,212,255,.1);border:1px solid rgba(0,212,255,.3);color:var(--accent);}
        .abtn-csv{background:rgba(34,197,94,.15);border:1px solid rgba(34,197,94,.3);color:#86efac;}
        .abtn-dis{background:rgba(255,255,255,.04);border:1px solid var(--border);color:var(--muted);cursor:not-allowed;opacity:.5;}
        .filter-bar{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 20px;margin-bottom:20px;display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;}
        .filter-group{display:flex;flex-direction:column;gap:6px;flex:1;min-width:140px;}
        .filter-label{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;}
        .filter-input{background:rgba(255,255,255,.03);border:1px solid var(--border);border-radius:7px;padding:8px 12px;color:var(--text);font-family:'JetBrains Mono',monospace;font-size:12px;outline:none;transition:.2s;}
        .filter-input:focus{border-color:var(--accent);}
        .filter-input option{background:var(--card);}
        .filter-btn{padding:9px 18px;border-radius:7px;font-family:'Syne',sans-serif;font-size:12px;font-weight:700;cursor:pointer;border:none;background:var(--accent);color:#000;}
        .filter-clear{padding:9px 14px;border-radius:7px;font-family:'Syne',sans-serif;font-size:12px;font-weight:700;cursor:pointer;border:1px solid var(--border);background:transparent;color:var(--muted);}
        .stitle{font-size:15px;font-weight:700;margin-bottom:14px;display:flex;align-items:center;justify-content:space-between;gap:8px;}
        .twrap{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;}
        table{width:100%;border-collapse:collapse;}
        th{background:rgba(255,255,255,.02);font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);padding:12px 18px;text-align:left;}
        td{padding:13px 18px;border-top:1px solid var(--border);font-size:13px;}
        tr:hover td{background:rgba(255,255,255,.02);}
        .sev-high{background:rgba(239,68,68,.15);color:#fca5a5;padding:3px 8px;border-radius:4px;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;}
        .sev-critical{background:rgba(239,68,68,.25);color:#ef4444;padding:3px 8px;border-radius:4px;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;}
        .sev-medium{background:rgba(96,165,250,.15);color:#93c5fd;padding:3px 8px;border-radius:4px;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;}
        .sev-low{background:rgba(34,197,94,.1);color:#86efac;padding:3px 8px;border-radius:4px;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;}
        .dot-ok{display:inline-flex;align-items:center;gap:5px;font-family:'JetBrains Mono',monospace;font-size:12px;}
        .dot-ok::before{content:'';width:6px;height:6px;border-radius:50%;background:var(--success);box-shadow:0 0 6px var(--success);display:inline-block;}
        .empty{text-align:center;padding:36px;color:var(--muted);font-family:'JetBrains Mono',monospace;font-size:12px;}
        .result-count{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);}
        @keyframes rowFlash{from{background:rgba(0,212,255,.15);}to{background:transparent;}}
        .new-row td{animation:rowFlash 2s ease;}
    </style>
</head>
<body>

<div class="toast-container" id="toast-container"></div>

<div class="notif-panel" id="notif-panel">
  <div class="notif-header">
    <span class="notif-title">&#x1F514; Notifications</span>
    <button class="notif-clear" onclick="clearNotifications()">Clear all</button>
  </div>
  <div class="notif-list" id="notif-list">
    <div class="notif-empty">No notifications yet</div>
  </div>
</div>

<nav class="sidebar">
  <div class="slogo"><div class="slogo-icon">&#x1F916;</div><div class="slogo-name">DevOps Agent</div></div>
  <span class="nsec">Monitoring</span>
  <a class="nitem active" href="#">&#x1F4CA; Dashboard</a>
  <a class="nitem" href="#">&#x1F514; Incidents</a>
  <a class="nitem" href="#">&#x1F4C8; Metrics</a>
  <span class="nsec">Agents</span>
  <a class="nitem" href="#">&#x1F441; Monitor</a>
  <a class="nitem" href="#">&#x1F50D; Investigation</a>
  <a class="nitem" href="#">&#x1F527; Remediation</a>
  <a class="nitem" href="#">&#x1F4C4; Post-Mortem</a>
  {% if current_user.is_admin() %}
  <span class="nsec">Admin</span>
  <a class="nitem" href="#">&#x1F465; Manage Users</a>
  <a class="nitem" href="#">&#x2699; Settings</a>
  {% endif %}
  <div class="sf">
    <div class="uinfo">
      <div class="avatar">{{ current_user.username[0].upper() }}</div>
      <div><div class="uname">{{ current_user.username }}</div>
      <div class="urole role-{{ current_user.role }}">{{ current_user.role.upper() }}</div></div>
    </div>
    <a href="/logout" class="btnlo">Logout</a>
  </div>
</nav>

<main class="main">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}{% for cat,msg in messages %}
      <div class="flash flash-{{cat}}">{{msg}}</div>
    {% endfor %}{% endif %}
  {% endwith %}

  {% if current_user.role == 'viewer' %}
  <div class="pnotice">Viewer access - you can monitor but cannot trigger actions.</div>
  {% endif %}

  <div class="phead">
    <div><div class="ptitle">Incident Dashboard</div>
    <div class="psub">AUTONOMOUS DEVOPS RESPONSE SYSTEM - LIVE</div></div>
    <div class="head-right">
      <span class="live-dot">LIVE</span>
      <span class="db-badge">&#x1F4BE; DB Connected</span>
      <div class="bell-wrap">
        <div class="bell-btn" id="bell-btn" onclick="toggleNotifPanel()">&#x1F514;</div>
        <div class="bell-badge" id="bell-badge">0</div>
      </div>
      <span class="rbadge rbadge-{{ current_user.role }}">{{ current_user.role }}</span>
    </div>
  </div>

  <div class="sgrid">
    <div class="sc"><div class="lbl">Total Incidents</div><div class="num ta" id="total-incidents">0</div><div class="sub">saved in database</div></div>
    <div class="sc"><div class="lbl">Active Agents</div><div class="num ts">5</div><div class="sub">all operational</div></div>
    <div class="sc"><div class="lbl">Check Interval</div><div class="num tw">60s</div><div class="sub">auto-monitoring</div></div>
    <div class="sc"><div class="lbl">High Severity</div><div class="num td" id="high-count">0</div><div class="sub">critical + high</div></div>
  </div>

  <!-- CHARTS -->
  <div class="charts-grid">
    <div class="chart-card">
      <div class="chart-title">CPU Usage History <span id="cpu-current">-- %</span></div>
      <div class="chart-wrap"><canvas id="cpuChart"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">Incident Severity Breakdown</div>
      <div class="chart-wrap"><canvas id="sevChart"></canvas></div>
    </div>
  </div>

  <div class="stitle">Agent Status</div>
  <div class="agrid">
    <div class="ac"><div class="aicon">&#x1F441;</div><div class="aname">Monitor</div><div class="abadge">Active</div></div>
    <div class="ac"><div class="aicon">&#x1F50D;</div><div class="aname">Investigation</div><div class="abadge">Active</div></div>
    <div class="ac"><div class="aicon">&#x1F527;</div><div class="aname">Remediation</div><div class="abadge">Active</div></div>
    <div class="ac"><div class="aicon">&#x1F6A8;</div><div class="aname">Escalation</div><div class="abadge">Active</div></div>
    <div class="ac"><div class="aicon">&#x1F4C4;</div><div class="aname">Post-Mortem</div><div class="abadge">Active</div></div>
  </div>

  <div class="pipeline">
    <div class="stitle">Pipeline Flow</div>
    <div class="psteps">
      <div class="pstep"><div class="si">&#x1F441;</div><div class="sn">Monitor</div></div><div class="parrow">-&gt;</div>
      <div class="pstep"><div class="si">&#x1F50D;</div><div class="sn">Investigate</div></div><div class="parrow">-&gt;</div>
      <div class="pstep"><div class="si">&#x1F527;</div><div class="sn">Remediate</div></div><div class="parrow">-&gt;</div>
      <div class="pstep"><div class="si">&#x1F6A8;</div><div class="sn">Escalate</div></div><div class="parrow">-&gt;</div>
      <div class="pstep"><div class="si">&#x1F4C4;</div><div class="sn">Post-Mortem</div></div>
    </div>
  </div>

  <div class="arow">
    {% if current_user.is_admin() %}
      <button class="abtn abtn-run" id="btn-pipeline" onclick="runPipeline()">Run Full Pipeline</button>
      <button class="abtn abtn-demo" id="btn-demo" onclick="runDemo()">Demo CRITICAL Incident</button>
    {% else %}
      <button class="abtn abtn-dis" disabled>Run Pipeline (Admin only)</button>
    {% endif %}
    {% if current_user.is_engineer() %}
      <button class="abtn abtn-eng" onclick="triggerRemediation()">Trigger Remediation</button>
    {% else %}
      <button class="abtn abtn-dis" disabled>Remediation (Engineer+)</button>
    {% endif %}
    <button class="abtn abtn-view" onclick="loadIncidents()">Refresh</button>
    <a href="/api/export-csv" class="abtn abtn-csv">Export CSV</a>
  </div>

  <div class="filter-bar">
    <div class="filter-group"><span class="filter-label">Search</span><input class="filter-input" type="text" id="search-text" placeholder="root cause, service..."/></div>
    <div class="filter-group"><span class="filter-label">Severity</span>
      <select class="filter-input" id="filter-severity">
        <option value="">All</option><option value="CRITICAL">Critical</option>
        <option value="HIGH">High</option><option value="MEDIUM">Medium</option><option value="LOW">Low</option>
      </select>
    </div>
    <div class="filter-group"><span class="filter-label">From Date</span><input class="filter-input" type="date" id="filter-date-from"/></div>
    <div class="filter-group"><span class="filter-label">To Date</span><input class="filter-input" type="date" id="filter-date-to"/></div>
    <button class="filter-btn" onclick="loadIncidents()">Search</button>
    <button class="filter-clear" onclick="clearFilters()">Clear</button>
  </div>

  <div class="stitle"><span>Incident History</span><span class="result-count" id="result-count"></span></div>
  <div class="twrap">
    <table>
      <thead><tr><th>#</th><th>Time</th><th>Root Cause</th><th>Severity</th><th>Jira Ticket</th><th>Service</th><th>Triggered By</th><th>Status</th></tr></thead>
      <tbody id="incidents-body">
        <tr><td colspan="8" class="empty">No incidents yet - click Demo CRITICAL Incident to start!</td></tr>
      </tbody>
    </table>
  </div>
</main>

<script>
// ── Chart.js Setup ────────────────────────────────────────────────────────────
var cpuChart, sevChart;

function initCharts() {
  // CPU Line Chart
  var cpuCtx = document.getElementById('cpuChart').getContext('2d');
  cpuChart = new Chart(cpuCtx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'CPU %',
        data: [],
        borderColor: '#00d4ff',
        backgroundColor: 'rgba(0,212,255,0.08)',
        borderWidth: 2,
        pointBackgroundColor: '#00d4ff',
        pointRadius: 4,
        tension: 0.4,
        fill: true
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {legend: {display: false}},
      scales: {
        x: {ticks: {color: '#64748b', font: {family: 'JetBrains Mono', size: 10}}, grid: {color: 'rgba(255,255,255,0.04)'}},
        y: {ticks: {color: '#64748b', font: {family: 'JetBrains Mono', size: 10}, callback: function(v){return v+'%';}}, grid: {color: 'rgba(255,255,255,0.04)'}, min: 0, max: 100}
      }
    }
  });

  // Severity Pie Chart
  var sevCtx = document.getElementById('sevChart').getContext('2d');
  sevChart = new Chart(sevCtx, {
    type: 'doughnut',
    data: {
      labels: ['Critical', 'High', 'Medium', 'Low'],
      datasets: [{
        data: [0, 0, 0, 0],
        backgroundColor: ['rgba(239,68,68,0.8)', 'rgba(245,158,11,0.8)', 'rgba(96,165,250,0.8)', 'rgba(34,197,94,0.8)'],
        borderColor: ['#ef4444', '#f59e0b', '#60a5fa', '#22c55e'],
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {position: 'bottom', labels: {color: '#94a3b8', font: {family: 'JetBrains Mono', size: 10}, padding: 12}}
      }
    }
  });

  // Load initial data
  loadCpuHistory();
  loadSeverityCounts();
}

function loadCpuHistory() {
  fetch('/api/cpu-history')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      cpuChart.data.labels = data.labels;
      cpuChart.data.datasets[0].data = data.values;
      cpuChart.update();
      if (data.values.length > 0) {
        var latest = data.values[data.values.length - 1];
        document.getElementById('cpu-current').textContent = latest.toFixed(1) + '%';
      }
    });
}

function loadSeverityCounts() {
  fetch('/api/severity-counts')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      sevChart.data.datasets[0].data = [data.CRITICAL, data.HIGH, data.MEDIUM, data.LOW];
      sevChart.update();
    });
}

function updateCpuChart(label, value) {
  var labels = cpuChart.data.labels;
  var values = cpuChart.data.datasets[0].data;
  labels.push(label);
  values.push(value);
  if (labels.length > 10) { labels.shift(); values.shift(); }
  cpuChart.update();
  document.getElementById('cpu-current').textContent = value.toFixed(1) + '%';
}

function updateSevChart(counts) {
  sevChart.data.datasets[0].data = [counts.CRITICAL, counts.HIGH, counts.MEDIUM, counts.LOW];
  sevChart.update();
}

// ── SocketIO ──────────────────────────────────────────────────────────────────
var socket = io();
var unreadCount = 0;

socket.on('connect', function() { console.log('Live connected'); });

socket.on('new_incident', function(incident) {
  prependIncidentRow(incident);
  var total = parseInt(document.getElementById('total-incidents').textContent) + 1;
  document.getElementById('total-incidents').textContent = total;
  var sev = (incident.severity || '').toLowerCase();
  if (sev === 'critical' || sev === 'high') {
    var h = parseInt(document.getElementById('high-count').textContent) + 1;
    document.getElementById('high-count').textContent = h;
  }
  addNotification(incident);
  showToast(incident);
  if (sev === 'critical') playCriticalSound();
  ringBell();
});

socket.on('severity_update', function(counts) { updateSevChart(counts); });

socket.on('cpu_update', function(data) { updateCpuChart(data.label, data.value); });

// ── Bell ──────────────────────────────────────────────────────────────────────
function ringBell() {
  var bell = document.getElementById('bell-btn');
  bell.classList.remove('ringing');
  void bell.offsetWidth;
  bell.classList.add('ringing');
  setTimeout(function() { bell.classList.remove('ringing'); }, 600);
  unreadCount++;
  var badge = document.getElementById('bell-badge');
  badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
  badge.classList.add('show');
}

function toggleNotifPanel() {
  var panel = document.getElementById('notif-panel');
  panel.classList.toggle('open');
  if (panel.classList.contains('open')) {
    unreadCount = 0;
    document.getElementById('bell-badge').classList.remove('show');
    var items = document.querySelectorAll('.notif-item.unread');
    for (var i = 0; i < items.length; i++) items[i].classList.remove('unread');
  }
}

function addNotification(incident) {
  var list = document.getElementById('notif-list');
  var empty = list.querySelector('.notif-empty');
  if (empty) empty.remove();
  var sev = (incident.severity || 'low').toLowerCase();
  var icon = sev === 'critical' ? '&#x1F6A8;' : sev === 'high' ? '&#x26A0;' : '&#x2139;';
  var div = document.createElement('div');
  div.className = 'notif-item unread';
  div.innerHTML = '<div class="notif-dot notif-dot-' + sev + '"></div>' +
    '<div class="notif-body"><div class="notif-msg">' + icon + ' ' + incident.severity.toUpperCase() + ': ' + incident.root_cause + '</div>' +
    '<div class="notif-time">' + incident.time + ' &bull; ' + (incident.service_name||'unknown') + '</div></div>';
  list.insertBefore(div, list.firstChild);
}

function clearNotifications() {
  unreadCount = 0;
  document.getElementById('bell-badge').classList.remove('show');
  document.getElementById('notif-list').innerHTML = '<div class="notif-empty">No notifications yet</div>';
}

document.addEventListener('click', function(e) {
  var panel = document.getElementById('notif-panel');
  var bell  = document.getElementById('bell-btn');
  if (!panel.contains(e.target) && !bell.contains(e.target)) panel.classList.remove('open');
});

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(incident) {
  var container = document.getElementById('toast-container');
  var sev  = (incident.severity || '').toLowerCase();
  var icon = sev === 'critical' ? '&#x1F6A8;' : sev === 'high' ? '&#x26A0;&#xFE0F;' : '&#x2139;&#xFE0F;';
  var toast = document.createElement('div');
  toast.className = 'toast ' + sev;
  toast.innerHTML = '<div class="toast-icon">' + icon + '</div>' +
    '<div class="toast-body"><div class="toast-title">New ' + incident.severity.toUpperCase() + ' Incident</div>' +
    '<div class="toast-msg">' + incident.root_cause + '</div></div>' +
    '<button class="toast-close" onclick="this.parentElement.remove()">x</button>';
  container.appendChild(toast);
  setTimeout(function() { if (toast.parentElement) toast.remove(); }, 5000);
}

// ── Sound ─────────────────────────────────────────────────────────────────────
function playCriticalSound() {
  try {
    var ctx = new (window.AudioContext || window.webkitAudioContext)();
    function beep(freq, start, dur, vol) {
      var osc = ctx.createOscillator(); var gain = ctx.createGain();
      osc.connect(gain); gain.connect(ctx.destination);
      osc.frequency.value = freq; osc.type = 'sine';
      gain.gain.setValueAtTime(vol, ctx.currentTime + start);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + dur);
      osc.start(ctx.currentTime + start); osc.stop(ctx.currentTime + start + dur);
    }
    beep(880, 0.0, 0.15, 0.4); beep(660, 0.2, 0.15, 0.4); beep(440, 0.4, 0.25, 0.4);
  } catch(e) { console.log('Audio not available'); }
}

// ── Table ─────────────────────────────────────────────────────────────────────
function prependIncidentRow(inc) {
  var tbody = document.getElementById('incidents-body');
  var empty = tbody.querySelector('.empty');
  if (empty) tbody.innerHTML = '';
  var sev = (inc.severity || 'medium').toLowerCase();
  var tr = document.createElement('tr');
  tr.className = 'new-row';
  tr.innerHTML =
    '<td style="color:var(--muted);font-family:monospace;font-size:11px">#' + inc.id + '</td>' +
    '<td style="font-family:monospace;font-size:12px;color:var(--muted)">' + inc.time + '</td>' +
    '<td>' + inc.root_cause + '</td>' +
    '<td><span class="sev-' + sev + '">' + (inc.severity||'MEDIUM').toUpperCase() + '</span></td>' +
    '<td style="font-family:monospace;font-size:12px">' + (inc.jira_ticket||'N/A') + '</td>' +
    '<td style="color:var(--muted);font-size:12px">' + (inc.service_name||'unknown') + '</td>' +
    '<td style="color:var(--muted);font-size:12px">' + (inc.triggered_by||'system') + '</td>' +
    '<td><span class="dot-ok">Resolved</span></td>';
  tbody.insertBefore(tr, tbody.firstChild);
}

// ── Pipeline & Demo ───────────────────────────────────────────────────────────
function runPipeline() {
  var btn = document.getElementById('btn-pipeline');
  btn.textContent = 'Running...'; btn.disabled = true;
  fetch('/api/run-pipeline', {method: 'POST'})
    .then(function(r) { return r.json(); })
    .then(function(data) {
      btn.textContent = 'Run Full Pipeline'; btn.disabled = false;
      if (data.error) alert('Error: ' + data.error);
      else if (data.status === 'healthy') alert('Pipeline ran! All systems healthy.');
    })
    .catch(function(e) { btn.textContent = 'Run Full Pipeline'; btn.disabled = false; alert('Error: '+e); });
}

function runDemo() {
  if (!confirm('Simulate a CRITICAL incident through all 5 agents?')) return;
  var btn = document.getElementById('btn-demo');
  btn.textContent = 'Simulating...'; btn.disabled = true;
  fetch('/api/demo-incident', {method: 'POST'})
    .then(function(r) { return r.json(); })
    .then(function(data) {
      btn.textContent = 'Demo CRITICAL Incident'; btn.disabled = false;
      if (data.error) alert('Error: ' + data.error);
    })
    .catch(function(e) { btn.textContent = 'Demo CRITICAL Incident'; btn.disabled = false; alert('Error: '+e); });
}

function triggerRemediation() { alert('Remediation triggered!'); }

function clearFilters() {
  document.getElementById('search-text').value = '';
  document.getElementById('filter-severity').value = '';
  document.getElementById('filter-date-from').value = '';
  document.getElementById('filter-date-to').value = '';
  loadIncidents();
}

function loadIncidents() {
  var search   = document.getElementById('search-text').value;
  var severity = document.getElementById('filter-severity').value;
  var dateFrom = document.getElementById('filter-date-from').value;
  var dateTo   = document.getElementById('filter-date-to').value;
  var params = [];
  if (search)   params.push('search='    + encodeURIComponent(search));
  if (severity) params.push('severity='  + encodeURIComponent(severity));
  if (dateFrom) params.push('date_from=' + encodeURIComponent(dateFrom));
  if (dateTo)   params.push('date_to='   + encodeURIComponent(dateTo));
  var url = '/api/incidents' + (params.length ? '?' + params.join('&') : '');
  fetch(url).then(function(r) { return r.json(); }).then(function(data) {
    var incidents = data.incidents;
    document.getElementById('total-incidents').textContent = data.total;
    var high = incidents.filter(function(i) { return ['high','critical'].indexOf((i.severity||'').toLowerCase()) !== -1; }).length;
    document.getElementById('high-count').textContent = high;
    document.getElementById('result-count').textContent = incidents.length + ' of ' + data.total + ' shown';
    var tbody = document.getElementById('incidents-body');
    if (!incidents.length) { tbody.innerHTML = '<tr><td colspan="8" class="empty">No incidents match your filter.</td></tr>'; return; }
    var rows = '';
    for (var i = 0; i < incidents.length; i++) {
      var inc = incidents[i]; var sev = (inc.severity||'medium').toLowerCase();
      rows += '<tr><td style="color:var(--muted);font-family:monospace;font-size:11px">#' + inc.id + '</td>' +
        '<td style="font-family:monospace;font-size:12px;color:var(--muted)">' + inc.time + '</td>' +
        '<td>' + inc.root_cause + '</td>' +
        '<td><span class="sev-' + sev + '">' + (inc.severity||'MEDIUM').toUpperCase() + '</span></td>' +
        '<td style="font-family:monospace;font-size:12px">' + (inc.jira_ticket||'N/A') + '</td>' +
        '<td style="color:var(--muted);font-size:12px">' + (inc.service_name||'unknown') + '</td>' +
        '<td style="color:var(--muted);font-size:12px">' + (inc.triggered_by||'system') + '</td>' +
        '<td><span class="dot-ok">Resolved</span></td></tr>';
    }
    tbody.innerHTML = rows;
  });
}

// Init everything
window.addEventListener('load', function() {
  initCharts();
  loadIncidents();
  // Refresh CPU chart every 30 seconds
  setInterval(loadCpuHistory, 30000);
});
</script>
</body></html>
"""

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        user = get_user_by_username(username)
        if user and user.check_password(password):
            login_user(user, remember=True)
            flash('Welcome, ' + user.username + '! Logged in as ' + user.role.upper() + '.', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/run-pipeline', methods=['POST'])
@admin_required
def run_pipeline_api():
    try:
        import sys; sys.path.append('.')
        from factory import AgentFactory
        from observer import event_system

        monitor = AgentFactory.create_agent("monitor")
        monitor.cpu_threshold = 0.1
        alerts = monitor.run()

        # Update CPU chart
        cpu_val = alerts[0]['value'] if alerts else 0.2
        label = datetime.now().strftime("%H:%M:%S")
        cpu_history['labels'].append(label)
        cpu_history['values'].append(cpu_val)
        if len(cpu_history['labels']) > 10:
            cpu_history['labels'].pop(0)
            cpu_history['values'].pop(0)
        socketio.emit('cpu_update', {'label': label, 'value': cpu_val})

        if not alerts:
            return jsonify({"message": "No alerts", "status": "healthy"})

        event_system.publish("alert_detected", alerts)
        investigator = AgentFactory.create_agent("investigation")
        diagnosis = investigator.investigate(alerts)
        event_system.publish("diagnosis_complete", diagnosis)

        if diagnosis.get('auto_fixable'):
            from strategy import StrategySelector
            result = StrategySelector.select(diagnosis['root_cause']).execute(diagnosis['affected_service'])
        else:
            result = AgentFactory.create_agent("remediation").remediate(diagnosis)

        escalation = None
        if result.get('status') == 'escalate' or not diagnosis.get('auto_fixable'):
            escalator = AgentFactory.create_agent("escalation")
            escalation = escalator.escalate(diagnosis, alerts)
            event_system.publish("escalation_complete", escalation)

        AgentFactory.create_agent("postmortem").generate(diagnosis, alerts, result)

        incident = save_and_push(
            root_cause   = diagnosis.get('root_cause', 'Unknown'),
            severity     = diagnosis.get('severity', 'medium'),
            jira_ticket  = escalation.get('jira_ticket') if escalation else 'Auto-Fixed',
            triggered_by = current_user.username,
            service_name = diagnosis.get('affected_service', 'unknown'),
        )
        return jsonify(incident.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/demo-incident', methods=['POST'])
@login_required
def demo_incident():
    try:
        import sys; sys.path.append('.')
        from factory import AgentFactory
        from observer import event_system

        monitor = AgentFactory.create_agent("monitor")
        monitor.cpu_threshold = 0.1
        alerts = monitor.run()
        if not alerts:
            alerts = [{'type':'HIGH_CPU','value':99.9,'threshold':80,'message':'CPU 99.9% exceeds threshold'}]

        # Update CPU chart with the alert value
        cpu_val = alerts[0]['value']
        label = datetime.now().strftime("%H:%M:%S")
        cpu_history['labels'].append(label)
        cpu_history['values'].append(cpu_val)
        if len(cpu_history['labels']) > 10:
            cpu_history['labels'].pop(0); cpu_history['values'].pop(0)
        socketio.emit('cpu_update', {'label': label, 'value': cpu_val})

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
        AgentFactory.create_agent("postmortem").generate(diagnosis, alerts, result)

        incident = save_and_push(
            root_cause   = diagnosis.get('root_cause', 'High CPU - simulated CRITICAL'),
            severity     = 'CRITICAL',
            jira_ticket  = escalation.get('jira_ticket','DEMO-001') if escalation else 'DEMO-001',
            triggered_by = current_user.username,
            service_name = diagnosis.get('affected_service', 'ec2-instance'),
        )
        return jsonify({"success": True, "incident": incident.to_dict()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cpu-history')
@login_required
def get_cpu_history():
    # If no real data yet, generate sample data for demo
    if not cpu_history['values']:
        import random
        now = datetime.now()
        for i in range(10, 0, -1):
            from datetime import timedelta
            t = now - timedelta(seconds=i*30)
            cpu_history['labels'].append(t.strftime("%H:%M:%S"))
            cpu_history['values'].append(round(random.uniform(0.1, 5.0), 2))
    return jsonify(cpu_history)

@app.route('/api/severity-counts')
@login_required
def severity_counts():
    return jsonify(get_severity_counts())

@app.route('/api/incidents')
@login_required
def get_incidents():
    query     = Incident.query
    search    = request.args.get('search','').strip()
    severity  = request.args.get('severity','').strip()
    date_from = request.args.get('date_from','').strip()
    date_to   = request.args.get('date_to','').strip()
    if search:
        query = query.filter(db.or_(
            Incident.root_cause.ilike('%'+search+'%'),
            Incident.service_name.ilike('%'+search+'%'),
            Incident.jira_ticket.ilike('%'+search+'%'),
        ))
    if severity:   query = query.filter(Incident.severity.ilike(severity))
    if date_from:  query = query.filter(Incident.time >= datetime.strptime(date_from,'%Y-%m-%d'))
    if date_to:    query = query.filter(Incident.time <= datetime.strptime(date_to+' 23:59:59','%Y-%m-%d %H:%M:%S'))
    total     = Incident.query.count()
    incidents = query.order_by(Incident.time.desc()).all()
    return jsonify({"total": total, "incidents": [i.to_dict() for i in incidents]})

@app.route('/api/export-csv')
@login_required
def export_csv():
    incidents = Incident.query.order_by(Incident.time.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID','Time','Root Cause','Severity','Jira Ticket','Service','Triggered By','Status'])
    for inc in incidents:
        writer.writerow([inc.id, inc.time.strftime("%Y-%m-%d %H:%M:%S"), inc.root_cause,
                         inc.severity, inc.jira_ticket or 'N/A', inc.service_name or 'unknown',
                         inc.triggered_by or 'system', inc.status])
    output.seek(0)
    filename = 'incidents_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.csv'
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename='+filename})

@app.route('/api/status')
@login_required
def get_status():
    return jsonify({"status":"running","agents":5,"incidents":Incident.query.count(),"last_check":str(datetime.now())})

if __name__ == '__main__':
    print("=" * 55)
    print("  AI DevOps Dashboard - Charts + Live + Sound + DB")
    print("=" * 55)
    print("  URL      : http://localhost:5000")
    print("  Admin    : admin / admin123")
    print("  Engineer : engineer / eng123")
    print("  Viewer   : viewer / view123")
    print("=" * 55)
    socketio.run(app, debug=True, port=5000)