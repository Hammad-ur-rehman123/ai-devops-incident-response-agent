import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.monitor_agent import MonitorAgent
from agents.remediation_agent import RemediationAgent

def test_monitor_agent_runs():
    agent = MonitorAgent()
    alerts = agent.run()
    assert isinstance(alerts, list)
    print("Monitor Agent test passed!")

def test_monitor_detects_high_cpu():
    agent = MonitorAgent()
    agent.cpu_threshold = 80
    cpu = agent.check_cpu_usage()
    assert isinstance(cpu, float) or isinstance(cpu, int)
    assert cpu >= 0
    print("CPU detection test passed!")

def test_remediation_escalates_when_not_autofixable():
    agent = RemediationAgent()
    diagnosis = {
        "root_cause": "test issue",
        "severity": "high",
        "affected_service": "test-service",
        "recommended_action": "manual fix",
        "auto_fixable": False
    }
    result = agent.remediate(diagnosis)
    assert result['status'] == 'escalate'
    print("Remediation escalation test passed!")

def test_remediation_fixes_when_autofixable():
    agent = RemediationAgent()
    diagnosis = {
        "root_cause": "high cpu load",
        "severity": "medium",
        "affected_service": "web-server",
        "recommended_action": "scale up",
        "auto_fixable": True
    }
    result = agent.remediate(diagnosis)
    assert result['status'] == 'success'
    print("Remediation fix test passed!")