from agents.postmortem_agent import PostMortemAgent

test_diagnosis = {
    "root_cause": "Increased CPU load after recent deployment",
    "confidence": "medium",
    "affected_service": "web-server",
    "severity": "high",
    "recommended_action": "Rollback deployment",
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

test_remediation = {
    "status": "escalate",
    "reason": "Manual intervention required"
}

agent = PostMortemAgent()
result = agent.generate(test_diagnosis, test_alerts, test_remediation)
print("PDF created at: " + result['pdf_path'])