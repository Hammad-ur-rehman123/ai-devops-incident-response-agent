# 🤖 AI DevOps Incident Response Agent

An autonomous multi-agent AI system that monitors AWS infrastructure, 
detects incidents, investigates root causes using LLM, attempts 
auto-remediation, and generates professional post-mortem reports — 
all without human intervention.

---

## 🚀 What This System Does

When a server problem is detected, this system:

1. **Monitors** AWS CloudWatch metrics every 60 seconds
2. **Investigates** root cause using Groq AI (Llama 3.3 70B)
3. **Remediates** automatically if possible
4. **Escalates** to human team via Jira + Slack if not
5. **Generates** a professional PDF post-mortem report

---

## 🏗️ Architecture