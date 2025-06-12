import boto3
from commons.logs import get_logger

logger = get_logger("aws_costs")

class AwsCosts:
    def __init__(self, context, **module_config):
        self.context = context
        self.client = boto3.client("ce", region_name="us-east-1")  # Cost Explorer is region-locked
        self.budget_client = boto3.client("budgets")

    def get_costs(self, start, end, granularity="MONTHLY", filter=None):
        try:
            aws_filter = self._build_filter(filter)
            result = self.client.get_cost_and_usage(
                TimePeriod={"Start": start, "End": end},
                Granularity=granularity.upper(),
                Metrics=["UnblendedCost"],
                Filter=aws_filter if aws_filter else {}
            )
            total = result["ResultsByTime"]
            return {
                "status": "ok",
                "message": f"Retrieved costs for {start} to {end}",
                "data": {
                    "results": total,
                    "unit": result.get("Unit", "USD")
                }
            }
        except Exception as e:
            logger.error(f"get_costs failed: {e}")
            return {"status": "fail", "message": str(e)}

    def get_forecast(self, start, end, metric="UNBLENDED_COST"):
        try:
            result = self.client.get_cost_forecast(
                TimePeriod={"Start": start, "End": end},
                Metric=metric.upper(),
                Granularity="MONTHLY"
            )
            return {
                "status": "ok",
                "message": f"Forecast from {start} to {end}",
                "data": result["ForecastResultsByTime"]
            }
        except Exception as e:
            logger.error(f"get_forecast failed: {e}")
            return {"status": "fail", "message": str(e)}

    def list_services(self, start, end):
        try:
            result = self.client.get_cost_and_usage(
                TimePeriod={"Start": start, "End": end},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}]
            )
            services = [{
                "service": group["Keys"][0],
                "amount": group["Metrics"]["UnblendedCost"]["Amount"]
            } for group in result["ResultsByTime"][0]["Groups"]]

            return {
                "status": "ok",
                "message": f"Found {len(services)} services with usage",
                "data": services
            }
        except Exception as e:
            logger.error(f"list_services failed: {e}")
            return {"status": "fail", "message": str(e)}

    def get_budget_status(self, budget_name):
        try:
            result = self.budget_client.describe_budget(
                AccountId=self._get_account_id(),
                BudgetName=budget_name
            )
            budget = result.get("Budget", {})
            return {
                "status": "ok",
                "message": f"Budget {budget_name} details retrieved",
                "data": {
                    "limit": budget.get("BudgetLimit", {}),
                    "time_unit": budget.get("TimeUnit"),
                    "actual_spend": budget.get("CalculatedSpend", {}).get("ActualSpend", {}),
                    "forecasted_spend": budget.get("CalculatedSpend", {}).get("ForecastedSpend", {})
                }
            }
        except Exception as e:
            logger.error(f"get_budget_status failed: {e}")
            return {"status": "fail", "message": str(e)}

    def _get_account_id(self):
        sts = boto3.client("sts")
        return sts.get_caller_identity()["Account"]

    def _build_filter(self, wf_filter):
        if not wf_filter:
            return None
        and_conditions = []
        for key, value in wf_filter.items():
            if key == "tag":
                tag_key, tag_value = value.split(":")
                and_conditions.append({
                    "Tags": {
                        "Key": tag_key,
                        "Values": [tag_value]
                    }
                })
            else:
                dimension = key.upper()
                and_conditions.append({
                    "Dimensions": {
                        "Key": dimension,
                        "Values": [value]
                    }
                })
        return {"And": and_conditions}
