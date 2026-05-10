import sys
import os
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.monitor_agent import MonitorAgent
from agents.investigation_agent import InvestigationAgent
from agents.remediation_agent import RemediationAgent
from agents.escalation_agent import EscalationAgent
from agents.postmortem_agent import PostMortemAgent

def run_pipeline():
    print("\n" + "=" * 60)
    print("   AI DEVOPS INCIDENT RESPONSE SYSTEM")
    print("   All 5 Agents Active")
    print(f"   Started: {datetime.now(timezone.utc)}")
    print("=" * 60 + "\n")

    # STEP 1 — Monitor
    print("STEP 1: Monitor Agent checking systems...")
    monitor = MonitorAgent()
    alerts = monitor.run()

    if not alerts:
        print("\n✅ All systems healthy — no action needed!")
        return None

    # STEP 2 — Investigate
    print(f"\nSTEP 2: Investigation Agent analyzing {len(alerts)} alert(s)...")
    investigator = InvestigationAgent()
    diagnosis = investigator.investigate(alerts)

    # STEP 3 — Remediate
    print(f"\nSTEP 3: Remediation Agent attempting fix...")
    remediator = RemediationAgent()
    remediation = remediator.remediate(diagnosis)

    # STEP 4 — Escalate if needed
    escalation = None
    if remediation.get('status') == 'escalate':
        print(f"\nSTEP 4: Escalation Agent notifying team...")
        escalator = EscalationAgent()
        escalation = escalator.escalate(diagnosis, alerts)
    else:
        print(f"\nSTEP 4: Skipped — issue was auto-fixed!")

    # STEP 5 — Post-Mortem
    print(f"\nSTEP 5: Post-Mortem Agent generating report...")
    postmortem = PostMortemAgent()
    report = postmortem.generate(diagnosis, alerts, remediation)

    # FINAL SUMMARY
    print("\n" + "=" * 60)
    print("   FINAL INCIDENT SUMMARY")
    print("=" * 60)
    print(f"Alerts Detected  : {len(alerts)}")
    print(f"Root Cause       : {diagnosis['root_cause']}")
    print(f"Severity         : {diagnosis['severity'].upper()}")
    print(f"Auto Fixed       : {remediation.get('status') != 'escalate'}")
    if escalation:
        print(f"Jira Ticket      : {escalation.get('jira_ticket')}")
        print(f"Slack Alert      : Sent")
    print(f"PDF Report       : {report['pdf_path']}")
    print("\n🎉 ALL 5 AGENTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)

    return report


if __name__ == "__main__":
    run_pipeline()