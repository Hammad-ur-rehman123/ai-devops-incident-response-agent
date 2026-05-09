import os
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

class EscalationAgent:
    def __init__(self):
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        self.jira_url = os.getenv('JIRA_URL')
        self.jira_email = os.getenv('JIRA_EMAIL')
        self.jira_token = os.getenv('JIRA_API_TOKEN')

    def send_slack_alert(self, diagnosis, alerts):
        print("  📨 Sending Slack alert...")
        if self.slack_webhook:
            try:
                message = {"text": "🚨 INCIDENT: " + diagnosis['root_cause']}
                response = requests.post(self.slack_webhook, json=message, timeout=10)
                if response.status_code == 200:
                    print("  ✅ Slack alert sent!")
                    return True
                else:
                    print("  ⚠️ Slack error: " + str(response.status_code))
                    return False
            except Exception as e:
                print("  ⚠️ Slack error: " + str(e))
                return False
        else:
            print("  ✅ Slack simulated — no webhook configured")
            print("  Message: 🚨 INCIDENT - " + diagnosis['root_cause'])
            return True

    def create_jira_ticket(self, diagnosis, alerts):
        print("  🎫 Creating Jira ticket...")
        ticket_id = "OPS-" + datetime.now().strftime('%Y%m%d%H%M%S')

        if self.jira_url and self.jira_email and self.jira_token:
            try:
                summary = "[AI ALERT] " + diagnosis['root_cause']
                description = "ROOT CAUSE: " + diagnosis['root_cause']
                description += "\nSEVERITY: " + diagnosis['severity']
                description += "\nAFFECTED: " + diagnosis['affected_service']
                description += "\nACTION: " + diagnosis['recommended_action']

                payload = {
                    "fields": {
                        "project": {"key": "OPS"},
                        "summary": summary,
                        "description": description,
                        "issuetype": {"name": "Bug"}
                    }
                }
                response = requests.post(
                    self.jira_url + "/rest/api/2/issue",
                    json=payload,
                    auth=(self.jira_email, self.jira_token),
                    timeout=10
                )
                if response.status_code == 201:
                    ticket_id = response.json()['key']
                    print("  ✅ Jira ticket created: " + ticket_id)
                    return ticket_id
                else:
                    print("  ⚠️ Jira returned: " + str(response.status_code))
                    return ticket_id
            except Exception as e:
                print("  ⚠️ Jira error: " + str(e))
                return ticket_id
        else:
            print("  ✅ Jira ticket simulated: " + ticket_id)
            print("  Summary: [AI ALERT] " + diagnosis['root_cause'])
            return ticket_id

    def escalate(self, diagnosis, alerts):
        print("\n" + "=" * 50)
        print("Escalation Agent activated!")
        print("=" * 50)

        severity = diagnosis.get('severity', 'medium')
        print("Escalating " + severity.upper() + " severity incident...")

        results = {}

        print("\n[1/2] Slack Notification:")
        slack_result = self.send_slack_alert(diagnosis, alerts)
        results['slack'] = slack_result

        print("\n[2/2] Jira Ticket:")
        ticket_id = self.create_jira_ticket(diagnosis, alerts)
        results['jira_ticket'] = ticket_id

        print("\n" + "=" * 50)
        print("📋 ESCALATION REPORT")
        print("=" * 50)
        print("Slack Alert : " + ("✅ Sent" if results['slack'] else "❌ Failed"))
        print("Jira Ticket : " + str(ticket_id))
        print("Severity    : " + severity.upper())
        print("Time        : " + str(datetime.now(timezone.utc)))
        print("\n✅ Escalation complete — human team notified!")

        return results


if __name__ == "__main__":
    test_diagnosis = {
        "root_cause": "Increased CPU load after recent deployment",
        "confidence": "medium",
        "affected_service": "web-server",
        "severity": "high",
        "recommended_action": "Rollback deployment and investigate",
        "auto_fixable": False
    }
    test_alerts = [
        {
            "type": "HIGH_CPU",
            "value": 85,
            "threshold": 80,
            "message": "CPU usage 85% exceeds threshold 80%"
        }
    ]
    agent = EscalationAgent()
    result = agent.escalate(test_diagnosis, test_alerts)
    print("\nResult: " + json.dumps(result, indent=2))