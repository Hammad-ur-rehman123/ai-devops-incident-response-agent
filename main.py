import sys
import os
from datetime import datetime, timezone

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.monitor_agent import MonitorAgent
from agents.investigation_agent import InvestigationAgent

def run_pipeline():
    """
    Main pipeline — connects all agents together
    Monitor → Investigation → (Remediation coming soon)
    """
    print("\n" + "🤖 " * 20)
    print("AI DEVOPS INCIDENT RESPONSE SYSTEM")
    print(f"Started at: {datetime.now(timezone.utc)}")
    print("🤖 " * 20 + "\n")

    # Step 1 — Run Monitor Agent
    print("STEP 1: Running Monitor Agent...")
    monitor = MonitorAgent()
    alerts = monitor.run()

    # Step 2 — If alerts found, run Investigation Agent
    if alerts:
        print(f"\nSTEP 2: {len(alerts)} alert(s) found — Running Investigation Agent...")
        investigator = InvestigationAgent()
        diagnosis = investigator.investigate(alerts)

        # Step 3 — Show final summary
        print("\n" + "=" * 50)
        print("📊 INCIDENT SUMMARY")
        print("=" * 50)
        print(f"Alerts Detected  : {len(alerts)}")
        print(f"Root Cause       : {diagnosis['root_cause']}")
        print(f"Severity         : {diagnosis['severity']}")
        print(f"Auto-fixable     : {diagnosis['auto_fixable']}")

        if diagnosis['auto_fixable']:
            print("\n⚙️  Auto-fix available — Remediation Agent will handle this!")
        else:
            print("\n🚨 Manual fix required — Escalation Agent will alert the team!")

        print("\n✅ Pipeline complete!")
        return diagnosis

    else:
        print("\n✅ No alerts — all systems healthy!")
        return None


if __name__ == "__main__":
    run_pipeline()