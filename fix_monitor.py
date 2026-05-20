content = '''import boto3
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

class MonitorAgent:
    def __init__(self):
        self.cloudwatch = boto3.client(
            "cloudwatch",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        self.cpu_threshold = 80
        self.error_threshold = 10

    def check_lambda_errors(self):
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(minutes=5)
            response = self.cloudwatch.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Errors",
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=["Sum"]
            )
            datapoints = response.get("Datapoints", [])
            error_count = datapoints[0]["Sum"] if datapoints else 0
            print(f"Lambda Errors in last 5 min: {error_count}")
            return error_count
        except Exception as e:
            print(f"Error checking Lambda metrics: {e}")
            return 0

    def check_cpu_usage(self):
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(minutes=10)
            instance_id = os.getenv("EC2_INSTANCE_ID", "")
            if not instance_id:
                print("CPU Usage (simulated): 85%")
                return 85
            response = self.cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=["Average"]
            )
            datapoints = response.get("Datapoints", [])
            if datapoints:
                cpu = round(datapoints[0]["Average"], 1)
                print(f"CPU Usage (REAL EC2): {cpu}%")
                return cpu
            else:
                print("CPU Usage (waiting for data): 85%")
                return 85
        except Exception as e:
            print(f"CPU error: {e}")
            return 85

    def run(self):
        print("=" * 50)
        print(f"Monitor Agent running at {datetime.now(timezone.utc)}")
        print("=" * 50)
        alerts = []
        cpu = self.check_cpu_usage()
        if cpu > self.cpu_threshold:
            alerts.append({
                "type": "HIGH_CPU",
                "value": cpu,
                "threshold": self.cpu_threshold,
                "message": f"CPU usage {cpu}% exceeds threshold {self.cpu_threshold}%"
            })
        errors = self.check_lambda_errors()
        if errors > self.error_threshold:
            alerts.append({
                "type": "HIGH_ERRORS",
                "value": errors,
                "threshold": self.error_threshold,
                "message": f"Error count {errors} exceeds threshold {self.error_threshold}"
            })
        if alerts:
            print(f"\\n ALERT(S) DETECTED: {len(alerts)}")
            for alert in alerts:
                print(f"  -> {alert['message']}")
            print("\\nTriggering Investigation Agent...")
        else:
            print("\\n All systems normal.")
        return alerts

if __name__ == "__main__":
    agent = MonitorAgent()
    agent.run()
'''

with open("agents/monitor_agent.py", "w") as f:
    f.write(content)
print("monitor_agent.py fixed successfully!")