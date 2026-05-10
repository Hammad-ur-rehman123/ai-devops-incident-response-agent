import boto3
import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

class RemediationAgent:
    def __init__(self):
        self.region = os.getenv('AWS_REGION', 'us-east-1')

    def restart_service(self, service_name):
        """Simulate restarting a service"""
        print(f"  🔄 Restarting service: {service_name}...")
        # In production this calls AWS ECS or Systems Manager
        # Simulated for now
        return {
            "action": "restart_service",
            "service": service_name,
            "status": "success",
            "message": f"Service {service_name} restarted successfully"
        }

    def scale_up(self, service_name):
        """Simulate scaling up resources"""
        print(f"  📈 Scaling up: {service_name}...")
        return {
            "action": "scale_up",
            "service": service_name,
            "status": "success",
            "message": f"Scaled up {service_name} by 1 instance"
        }

    def rollback_deployment(self, service_name):
        """Simulate rolling back last deployment"""
        print(f"  ⏪ Rolling back deployment: {service_name}...")
        return {
            "action": "rollback",
            "service": service_name,
            "status": "success",
            "message": f"Rolled back {service_name} to previous version"
        }

    def remediate(self, diagnosis):
        """
        Takes diagnosis from Investigation Agent
        Decides what action to take and executes it
        """
        print("\n" + "=" * 50)
        print("Remediation Agent activated!")
        print("=" * 50)

        # Only run if auto-fixable
        if not diagnosis.get('auto_fixable', False):
            print("❌ Issue is NOT auto-fixable")
            print("→ Passing to Escalation Agent...")
            return {
                "status": "escalate",
                "reason": "Issue requires manual intervention",
                "diagnosis": diagnosis
            }

        severity = diagnosis.get('severity', 'low')
        affected = diagnosis.get('affected_service', 'unknown')
        action = diagnosis.get('recommended_action', '')
        root_cause = diagnosis.get('root_cause', '')

        print(f"Severity      : {severity}")
        print(f"Affected      : {affected}")
        print(f"Root Cause    : {root_cause}")
        print(f"\nSelecting fix action...")

        result = None

        # Decide action based on root cause keywords
        if 'deployment' in root_cause.lower():
            print("→ Deployment issue detected — rolling back")
            result = self.rollback_deployment(affected)

        elif 'cpu' in root_cause.lower() or 'load' in root_cause.lower():
            print("→ High load detected — scaling up")
            result = self.scale_up(affected)

        elif 'crash' in root_cause.lower() or 'restart' in root_cause.lower():
            print("→ Service crash detected — restarting")
            result = self.restart_service(affected)

        else:
            print("→ Unknown issue — attempting service restart")
            result = self.restart_service(affected)

        if result:
            print(f"\n✅ Remediation Result: {result['message']}")

        return result


# Test the agent
if __name__ == "__main__":
    # Simulate diagnosis from Investigation Agent
    test_diagnosis = {
        "root_cause": "Increased CPU load after recent deployment",
        "confidence": "medium",
        "affected_service": "web-server",
        "severity": "medium",
        "recommended_action": "Scale up or rollback deployment",
        "auto_fixable": True
    }

    agent = RemediationAgent()
    result = agent.remediate(test_diagnosis)
    print(f"\nFinal result: {json.dumps(result, indent=2)}")