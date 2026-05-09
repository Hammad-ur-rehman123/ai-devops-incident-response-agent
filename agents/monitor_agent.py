import boto3
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

class MonitorAgent:
    def __init__(self):
        self.cloudwatch = boto3.client(
            'cloudwatch',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        # Thresholds — if exceeded, alert is triggered
        self.cpu_threshold = 80
        self.error_threshold = 10

    def check_lambda_errors(self):
        """Check AWS Lambda error count in last 5 minutes"""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(minutes=5)

            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Errors',
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Sum']
            )

            datapoints = response.get('Datapoints', [])
            if datapoints:
                error_count = datapoints[0]['Sum']
            else:
                error_count = 0

            print(f"Lambda Errors in last 5 min: {error_count}")
            return error_count

        except Exception as e:
            print(f"Error checking Lambda metrics: {e}")
            return 0

    def check_cpu_usage(self):
        """Check EC2 CPU usage — simulated for now"""
        simulated_cpu = 85
        print(f"CPU Usage: {simulated_cpu}%")
        return simulated_cpu

    def run(self):
        """Main monitor loop — checks all metrics"""
        print("=" * 50)
        print(f"Monitor Agent running at {datetime.now(timezone.utc)}")
        print("=" * 50)

        alerts = []

        # Check CPU
        cpu = self.check_cpu_usage()
        if cpu > self.cpu_threshold:
            alerts.append({
                "type": "HIGH_CPU",
                "value": cpu,
                "threshold": self.cpu_threshold,
                "message": f"CPU usage {cpu}% exceeds threshold {self.cpu_threshold}%"
            })

        # Check Lambda errors
        errors = self.check_lambda_errors()
        if errors > self.error_threshold:
            alerts.append({
                "type": "HIGH_ERRORS",
                "value": errors,
                "threshold": self.error_threshold,
                "message": f"Error count {errors} exceeds threshold {self.error_threshold}"
            })

        # Report results
        if alerts:
            print(f"\n🚨 {len(alerts)} ALERT(S) DETECTED!")
            for alert in alerts:
                print(f"  → {alert['message']}")
            print("\nTriggering Investigation Agent...")
        else:
            print("\n✅ All systems normal. No alerts.")

        return alerts


# Run the agent
if __name__ == "__main__":
    agent = MonitorAgent()
    agent.run()