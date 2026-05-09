import sys
import os
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.monitor_agent import MonitorAgent
from agents.investigation_agent import InvestigationAgent
from agents.remediation_agent import RemediationAgent

def run_pipeline():
    print("\n" + "🤖 " * 20)
    print("AI DEVOPS INCIDENT RESPONSE SYSTEM")
    print(f"Started at: {datetime.now(timezone.utc)}")
    print("🤖 " * 20 + "\n")

    # STEP 1 — Monitor
    print("STEP 1: Running Monitor Agent...")
    monitor = MonitorAgent()
    alerts = monitor.run()

    if not alerts:
        print("\n✅ No alerts — all systems healthy!")
        return None

    # STEP 2 — Investigate
    print(f"\nSTEP 2: Running Investigation Agent...")
    investigator = InvestigationAgent()
    diagnosis = investigator.investigate(alerts)

    # STEP 3 — Remediate or Escalate
    print(f"\nSTEP 3: Running Remediation Agent...")
    remediator = RemediationAgent()
    result = remediator.remediate(diagnosis)

    # STEP 4 — Final Summary
    print("\n" + "=" * 50)
    print("📊 FINAL INCIDENT SUMMARY")
    print("=" * 50)
    print(f"Alerts Found  : {len(alerts)}")
    print(f"Root Cause    : {diagnosis['root_cause']}")
    print(f"Severity      : {diagnosis['severity']}")

    if result.get('status') == 'escalate':
        print(f"Resolution    : ❌ Escalated to human team")
    else:
        print(f"Resolution    : ✅ Auto-fixed by Remediation Agent")
        print(f"Action Taken  : {result.get('message')}")

    print("\n🎉 Pipeline complete!")
    return result


if __name__ == "__main__":
    run_pipeline()