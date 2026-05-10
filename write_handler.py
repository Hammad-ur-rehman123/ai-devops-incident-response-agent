content = """import json
import sys
import os

sys.path.append('/var/task')

from agents.monitor_agent import MonitorAgent
from agents.investigation_agent import InvestigationAgent
from agents.remediation_agent import RemediationAgent
from agents.escalation_agent import EscalationAgent
from agents.postmortem_agent import PostMortemAgent

def handler(event, context):
    print("Lambda triggered!")
    try:
        monitor = MonitorAgent()
        alerts = monitor.run()
        if not alerts:
            return {"statusCode": 200, "body": "No alerts!"}
        investigator = InvestigationAgent()
        diagnosis = investigator.investigate(alerts)
        remediator = RemediationAgent()
        remediation = remediator.remediate(diagnosis)
        escalation = None
        if remediation.get("status") == "escalate":
            escalator = EscalationAgent()
            escalation = escalator.escalate(diagnosis, alerts)
        postmortem = PostMortemAgent()
        postmortem.generate(diagnosis, alerts, remediation)
        return {"statusCode": 200, "body": "Pipeline completed!"}
    except Exception as e:
        return {"statusCode": 500, "body": str(e)}
"""

with open("lambda_handler.py", "w") as f:
    f.write(content)

print("lambda_handler.py written successfully!")