from agents.monitor_agent import MonitorAgent
from agents.investigation_agent import InvestigationAgent
from agents.remediation_agent import RemediationAgent
from agents.escalation_agent import EscalationAgent
from agents.postmortem_agent import PostMortemAgent


class AgentFactory:
    """
    Factory Pattern
    Creates AI agents based on type
    Instead of creating agents directly
    we use this factory class
    """

    @staticmethod
    def create_agent(agent_type):
        agents = {
            "monitor": MonitorAgent,
            "investigation": InvestigationAgent,
            "remediation": RemediationAgent,
            "escalation": EscalationAgent,
            "postmortem": PostMortemAgent
        }
        if agent_type not in agents:
            raise ValueError(f"Unknown agent type: {agent_type}")
        return agents[agent_type]()

    @staticmethod
    def create_all_agents():
        return {
            "monitor": MonitorAgent(),
            "investigation": InvestigationAgent(),
            "remediation": RemediationAgent(),
            "escalation": EscalationAgent(),
            "postmortem": PostMortemAgent()
        }