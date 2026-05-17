from flask import Flask, jsonify, render_template_string
from datetime import datetime
import threading
import json

app = Flask(__name__)

# Store incidents in memory
incidents_db = []
system_status = {
    "status": "running",
    "last_check": str(datetime.now()),
    "total_incidents": 0,
    "agents_active": 5
}

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AI DevOps Incident Response Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', sans-serif; 
            background: #0a0e1a; 
            color: #e0e0e0;
        }
        .header {
            background: linear-gradient(135deg, #1a1f3a, #0d1117);
            padding: 20px 30px;
            border-bottom: 1px solid #30363d;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 { 
            color: #58a6ff; 
            font-size: 22px;
        }
        .header .status {
            background: #1f6feb;
            color: white;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
        }
        .container { padding: 30px; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }
        .stat-card .number {
            font-size: 36px;
            font-weight: bold;
            color: #58a6ff;
        }
        .stat-card .label {
            font-size: 13px;
            color: #8b949e;
            margin-top: 5px;
        }
        .agents-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }
        .agent-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }
        .agent-card .icon { font-size: 28px; margin-bottom: 8px; }
        .agent-card .name { 
            font-size: 12px; 
            font-weight: bold;
            color: #58a6ff;
        }
        .agent-card .status-badge {
            background: #1f6323;
            color: #3fb950;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 10px;
            margin-top: 6px;
            display: inline-block;
        }
        .section-title {
            font-size: 16px;
            font-weight: bold;
            color: #58a6ff;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 1px solid #30363d;
        }
        .incidents-table {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 30px;
        }
        table { width: 100%; border-collapse: collapse; }
        th {
            background: #1f2937;
            padding: 12px 15px;
            text-align: left;
            font-size: 13px;
            color: #8b949e;
            font-weight: 500;
        }
        td {
            padding: 12px 15px;
            font-size: 13px;
            border-top: 1px solid #21262d;
        }
        .severity-high {
            background: #3d1f1f;
            color: #f85149;
            padding: 3px 8px;
            border-radius: 5px;
            font-size: 11px;
        }
        .severity-medium {
            background: #3d2f1f;
            color: #e3b341;
            padding: 3px 8px;
            border-radius: 5px;
            font-size: 11px;
        }
        .btn {
            background: #1f6feb;
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
        }
        .btn:hover { background: #388bfd; }
        .btn-run {
            background: #1f6323;
            color: #3fb950;
            border: 1px solid #3fb950;
        }
        .pipeline-status {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
        }
        .pipeline-steps {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 15px;
        }
        .pipeline-step {
            background: #1f2937;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 10px 15px;
            font-size: 12px;
            text-align: center;
        }
        .pipeline-step .step-icon { font-size: 20px; }
        .pipeline-step .step-name { color: #58a6ff; margin-top: 4px; }
        .pipeline-arrow { color: #30363d; font-size: 20px; }
        .run-btn-container { text-align: center; margin: 20px 0; }
        .empty-state { 
            text-align: center; 
            padding: 40px; 
            color: #8b949e;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 AI DevOps Incident Response System</h1>
        <span class="status">🟢 System Active — AWS Lambda Running</span>
    </div>

    <div class="container">
        <!-- Stats -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="number" id="total-incidents">0</div>
                <div class="label">Total Incidents</div>
            </div>
            <div class="stat-card">
                <div class="number" style="color:#3fb950">5</div>
                <div class="label">Active Agents</div>
            </div>
            <div class="stat-card">
                <div class="number" style="color:#e3b341">60s</div>
                <div class="label">Check Interval</div>
            </div>
            <div class="stat-card">
                <div class="number" style="color:#f85149" id="high-count">0</div>
                <div class="label">High Severity</div>
            </div>
        </div>

        <!-- Agents Status -->
        <div class="section-title">🤖 Agent Status</div>
        <div class="agents-grid">
            <div class="agent-card">
                <div class="icon">👁️</div>
                <div class="name">Monitor Agent</div>
                <div class="status-badge">● Active</div>
            </div>
            <div class="agent-card">
                <div class="icon">🔍</div>
                <div class="name">Investigation Agent</div>
                <div class="status-badge">● Active</div>
            </div>
            <div class="agent-card">
                <div class="icon">🔧</div>
                <div class="name">Remediation Agent</div>
                <div class="status-badge">● Active</div>
            </div>
            <div class="agent-card">
                <div class="icon">🚨</div>
                <div class="name">Escalation Agent</div>
                <div class="status-badge">● Active</div>
            </div>
            <div class="agent-card">
                <div class="icon">📄</div>
                <div class="name">Post-Mortem Agent</div>
                <div class="status-badge">● Active</div>
            </div>
        </div>

        <!-- Pipeline -->
        <div class="pipeline-status">
            <div class="section-title">⚙️ Agent Pipeline Flow</div>
            <div class="pipeline-steps">
                <div class="pipeline-step">
                    <div class="step-icon">👁️</div>
                    <div class="step-name">Monitor</div>
                </div>
                <div class="pipeline-arrow">→</div>
                <div class="pipeline-step">
                    <div class="step-icon">🔍</div>
                    <div class="step-name">Investigate</div>
                </div>
                <div class="pipeline-arrow">→</div>
                <div class="pipeline-step">
                    <div class="step-icon">🔧</div>
                    <div class="step-name">Remediate</div>
                </div>
                <div class="pipeline-arrow">→</div>
                <div class="pipeline-step">
                    <div class="step-icon">🚨</div>
                    <div class="step-name">Escalate</div>
                </div>
                <div class="pipeline-arrow">→</div>
                <div class="pipeline-step">
                    <div class="step-icon">📄</div>
                    <div class="step-name">Post-Mortem</div>
                </div>
            </div>
        </div>

        <!-- Run Pipeline Button -->
        <div class="run-btn-container">
            <button class="btn btn-run" onclick="runPipeline()">
                ▶ Run Full AI Pipeline Now
            </button>
        </div>

        <!-- Incidents Table -->
        <div class="section-title">📋 Incident History</div>
        <div class="incidents-table">
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Root Cause</th>
                        <th>Severity</th>
                        <th>Jira Ticket</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="incidents-body">
                    <tr>
                        <td colspan="5" class="empty-state">
                            No incidents yet. Click "Run Pipeline" to start!
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function runPipeline() {
            document.querySelector('.btn-run').textContent = '⏳ Running Pipeline...';
            fetch('/api/run-pipeline', {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    document.querySelector('.btn-run').textContent = '▶ Run Full AI Pipeline Now';
                    loadIncidents();
                })
                .catch(e => {
                    document.querySelector('.btn-run').textContent = '▶ Run Full AI Pipeline Now';
                    alert('Pipeline error: ' + e);
                });
        }

        function loadIncidents() {
            fetch('/api/incidents')
                .then(r => r.json())
                .then(incidents => {
                    document.getElementById('total-incidents').textContent = incidents.length;
                    let high = incidents.filter(i => i.severity === 'high' || i.severity === 'HIGH').length;
                    document.getElementById('high-count').textContent = high;
                    
                    let tbody = document.getElementById('incidents-body');
                    if (incidents.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No incidents yet. Click "Run Pipeline" to start!</td></tr>';
                        return;
                    }
                    tbody.innerHTML = incidents.map(i => `
                        <tr>
                            <td>${i.time}</td>
                            <td>${i.root_cause}</td>
                            <td><span class="severity-${i.severity.toLowerCase()}">${i.severity.toUpperCase()}</span></td>
                            <td>${i.jira_ticket || 'N/A'}</td>
                            <td>✅ Resolved</td>
                        </tr>
                    `).reverse().join('');
                });
        }

        setInterval(loadIncidents, 5000);
        loadIncidents();
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/run-pipeline', methods=['POST'])
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

        # Use Factory Pattern to create agents
        monitor = AgentFactory.create_agent("monitor")
        alerts = monitor.run()

        if not alerts:
            return jsonify({"message": "No alerts", "status": "healthy"})

        # Publish event using Observer Pattern
        event_system.publish("alert_detected", alerts)

        investigator = AgentFactory.create_agent("investigation")
        diagnosis = investigator.investigate(alerts)

        event_system.publish("diagnosis_complete", diagnosis)

        # Use Strategy Pattern for remediation
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
            "time": str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "root_cause": diagnosis.get('root_cause', 'Unknown'),
            "severity": diagnosis.get('severity', 'medium'),
            "jira_ticket": escalation.get('jira_ticket') if escalation else 'Auto-Fixed',
            "status": "resolved"
        }
        incidents_db.append(incident)

        return jsonify(incident)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/incidents')
def get_incidents():
    return jsonify(incidents_db)

@app.route('/api/status')
def get_status():
    return jsonify({
        "status": "running",
        "agents": 5,
        "incidents": len(incidents_db),
        "last_check": str(datetime.now())
    })

if __name__ == '__main__':
    print("Starting AI DevOps Dashboard...")
    print("Open browser at: http://localhost:5000")
    app.run(debug=True, port=5000)