import boto3
import datetime
from commons.logs import get_logger

logger = get_logger("aws_monitoring")

class AwsMonitoring:
    def __init__(self, context, **module_config):
        self.context = context
        self.client = boto3.client("cloudwatch")

    def get_metric_data(self, namespace, metric_name, dimensions, start_time, end_time, period=300, stat="Average"):
        try:
            result = self.client.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=[stat]
            )
            datapoints = sorted(result.get("Datapoints", []), key=lambda x: x["Timestamp"])
            values = [point[stat] for point in datapoints]
            timestamps = [point["Timestamp"].isoformat() for point in datapoints]
            unit = result["Label"]

            return {
                "status": "ok",
                "message": f"{metric_name} from {namespace} retrieved",
                "data": {
                    "metric": metric_name,
                    "values": values,
                    "timestamps": timestamps,
                    "unit": unit
                }
            }
        except Exception as e:
            logger.error(f"get_metric_data failed: {e}")
            return {"status": "fail", "message": str(e)}

    def get_recent_utilization(self, namespace, metric_name, dimensions, stat="Average"):
        try:
            end_time = datetime.datetime.utcnow()
            start_time = end_time - datetime.timedelta(minutes=5)
            return self.get_metric_data(
                namespace=namespace,
                metric_name=metric_name,
                dimensions=dimensions,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                period=60,
                stat=stat
            )
        except Exception as e:
            logger.error(f"get_recent_utilization failed: {e}")
            return {"status": "fail", "message": str(e)}

    def check_alarm_status(self, alarm_name):
        try:
            result = self.client.describe_alarms(AlarmNames=[alarm_name])
            alarms = result.get("MetricAlarms", [])
            if not alarms:
                return {"status": "fail", "message": f"Alarm '{alarm_name}' not found"}
            alarm = alarms[0]
            return {
                "status": "ok",
                "message": f"Alarm {alarm_name} state: {alarm['StateValue']}",
                "data": {
                    "state": alarm["StateValue"],
                    "last_updated": alarm["StateUpdatedTimestamp"].isoformat(),
                    "metric_name": alarm["MetricName"],
                    "namespace": alarm["Namespace"]
                }
            }
        except Exception as e:
            logger.error(f"check_alarm_status failed: {e}")
            return {"status": "fail", "message": str(e)}
