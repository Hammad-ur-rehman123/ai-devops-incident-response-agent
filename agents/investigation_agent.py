import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

class InvestigationAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY")
        )

    def investigate(self, alerts):
        """Takes alerts from Monitor Agent and asks AI for root cause"""

        print("\n" + "=" * 50)
        print("Investigation Agent activated!")
        print(f"Analyzing {len(alerts)} alert(s)...")
        print("=" * 50)

        # Build alert summary for AI
        alert_summary = ""
        for alert in alerts:
            alert_summary += f"- {alert['message']}\n"

        # System prompt — tells AI how to behave
        system_prompt = """You are an expert DevOps AI agent specializing in 
incident investigation. When given server alerts, you analyze them and return 
a diagnosis in JSON format only. 

Your response must be valid JSON with exactly these fields:
{
    "root_cause": "brief description of most likely cause",
    "confidence": "high/medium/low",
    "affected_service": "which service is affected",
    "severity": "critical/high/medium/low",
    "recommended_action": "what to do to fix it",
    "auto_fixable": true or false
}

Return ONLY the JSON. No extra text."""

        # User message with alert data
        user_message = f"""
Server alerts detected at {datetime.now(timezone.utc)}:

{alert_summary}

Additional context:
- Server has been running for 48 hours
- Last deployment was 2 hours ago
- No recent configuration changes

Investigate and provide your diagnosis.
"""

        print("\nSending alerts to AI for analysis...")

        # Call Groq AI
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]

        response = self.llm.invoke(messages)
        raw_response = response.content

        print(f"AI Response received!")

        # Parse JSON response
        try:
            # Clean response in case AI adds extra text
            clean_response = raw_response.strip()
            if "```json" in clean_response:
                clean_response = clean_response.split("```json")[1].split("```")[0]
            elif "```" in clean_response:
                clean_response = clean_response.split("```")[1].split("```")[0]

            diagnosis = json.loads(clean_response)

            print("\n📋 DIAGNOSIS REPORT:")
            print(f"  Root Cause    : {diagnosis['root_cause']}")
            print(f"  Confidence    : {diagnosis['confidence']}")
            print(f"  Severity      : {diagnosis['severity']}")
            print(f"  Affected      : {diagnosis['affected_service']}")
            print(f"  Fix Action    : {diagnosis['recommended_action']}")
            print(f"  Auto-fixable  : {diagnosis['auto_fixable']}")

            return diagnosis

        except json.JSONDecodeError:
            print("Could not parse JSON — returning raw response")
            return {
                "root_cause": raw_response,
                "confidence": "low",
                "affected_service": "unknown",
                "severity": "high",
                "recommended_action": "Manual investigation required",
                "auto_fixable": False
            }


# Test the agent
if __name__ == "__main__":
    # Simulate alerts from Monitor Agent
    test_alerts = [
        {
            "type": "HIGH_CPU",
            "value": 85,
            "threshold": 80,
            "message": "CPU usage 85% exceeds threshold 80%"
        }
    ]

    agent = InvestigationAgent()
    diagnosis = agent.investigate(test_alerts)
    print("\n✅ Investigation complete!")