import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch

load_dotenv()

class PostMortemAgent:

    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY")
        )

    def generate_report_text(self, incident_data):
        print("  AI writing post-mortem report...")
        system_prompt = "You are a senior DevOps engineer writing a professional post-mortem report. Include these sections: 1. Executive Summary 2. Timeline 3. Root Cause 4. Impact 5. Resolution 6. Prevention Recommendations"
        user_message = "Write a post-mortem report for this incident. ROOT CAUSE: " + incident_data['root_cause'] + ". SEVERITY: " + incident_data['severity'] + ". SERVICE: " + incident_data['affected_service'] + ". ACTION TAKEN: " + incident_data['action_taken']
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        response = self.llm.invoke(messages)
        print("  AI report generated!")
        return response.content

    def save_pdf(self, report_text, incident_data):
        print("  Generating PDF...")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = "postmortem_" + timestamp + ".pdf"
        filepath = os.path.join('/tmp', filename)
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph("AI DevOps Incident Post-Mortem Report", styles['Title']))
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph("Severity: " + incident_data['severity'].upper(), styles['Heading2']))
        story.append(Paragraph("Service: " + incident_data['affected_service'], styles['Heading3']))
        story.append(Spacer(1, 0.2 * inch))
        for line in report_text.split('\n'):
            if line.strip() == '':
                story.append(Spacer(1, 0.1 * inch))
            elif line.startswith('#'):
                clean = line.replace('#', '').strip()
                story.append(Paragraph(clean, styles['Heading2']))
            else:
                try:
                    story.append(Paragraph(line, styles['Normal']))
                except Exception:
                    pass
        doc.build(story)
        print("  PDF saved: " + filename)
        return filepath

    def generate(self, diagnosis, alerts, remediation_result):
        print("\n" + "=" * 50)
        print("Post-Mortem Agent activated!")
        print("=" * 50)
        incident_data = {
            "root_cause": diagnosis['root_cause'],
            "severity": diagnosis['severity'],
            "affected_service": diagnosis['affected_service'],
            "action_taken": str(remediation_result),
            "detected_at": str(datetime.now(timezone.utc)),
            "resolved_at": str(datetime.now(timezone.utc))
        }
        print("\n[1/2] Generating AI report...")
        report_text = self.generate_report_text(incident_data)
        print("\n[2/2] Saving PDF...")
        pdf_path = self.save_pdf(report_text, incident_data)
        print("\n" + "=" * 50)
        print("POST-MORTEM COMPLETE")
        print("=" * 50)
        print("PDF Location : " + pdf_path)
        print("Severity     : " + diagnosis['severity'].upper())
        print("Root Cause   : " + diagnosis['root_cause'])
        print("\nPost-mortem report generated successfully!")
        return {
            "pdf_path": pdf_path,
            "report_text": report_text
        }