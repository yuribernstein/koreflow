import boto3
from commons.logs import get_logger

logger = get_logger("aws_ec2")

class AwsEc2:
    def __init__(self, context, **module_config):
        self.context = context

    def _client(self, region=None):
        return boto3.client("ec2", region_name=region or "us-east-1")

    def create_instance(self, ami_id, instance_type, key_name=None,
                        subnet_id=None, security_group_ids=None,
                        tag_name=None, region=None):
        ec2 = self._client(region)
        try:
            params = {
                "ImageId": ami_id,
                "InstanceType": instance_type,
                "MinCount": 1,
                "MaxCount": 1
            }
            if key_name:
                params["KeyName"] = key_name
            if subnet_id:
                params["SubnetId"] = subnet_id
            if security_group_ids:
                params["SecurityGroupIds"] = security_group_ids
            if tag_name:
                params["TagSpecifications"] = [{
                    "ResourceType": "instance",
                    "Tags": [{"Key": "Name", "Value": tag_name}]
                }]

            resp = ec2.run_instances(**params)
            instance_id = resp["Instances"][0]["InstanceId"]
            return {
                "status": "ok",
                "message": f"Instance {instance_id} launched",
                "data": {"instance_id": instance_id}
            }
        except Exception as e:
            logger.error(f"create_instance failed: {e}")
            return {"status": "fail", "message": str(e)}

    def get_instance_status(self, instance_id, region=None):
        ec2 = self._client(region)
        try:
            resp = ec2.describe_instances(InstanceIds=[instance_id])
            if not resp["Reservations"]:
                return {
                    "status": "fail",
                    "message": f"Instance {instance_id} not found"
                }

            instance = resp["Reservations"][0]["Instances"][0]
            return {
                "status": "ok",
                "message": f"Instance {instance_id} info retrieved",
                "data": {
                    "instance_id": instance.get("InstanceId"),
                    "state": instance.get("State", {}).get("Name"),
                    "public_ip": instance.get("PublicIpAddress"),
                    "private_ip": instance.get("PrivateIpAddress"),
                    "instance_type": instance.get("InstanceType"),
                    "launch_time": instance.get("LaunchTime").isoformat() if instance.get("LaunchTime") else None,
                    "subnet_id": instance.get("SubnetId"),
                    "vpc_id": instance.get("VpcId"),
                    "availability_zone": instance.get("Placement", {}).get("AvailabilityZone"),
                    "tags": {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])},
                    "image_id": instance.get("ImageId"),
                    "key_name": instance.get("KeyName"),
                    "security_groups": [sg["GroupName"] for sg in instance.get("SecurityGroups", [])]
                }
            }
        except Exception as e:
            logger.error(f"get_instance_status failed: {e}")
            return {"status": "fail", "message": str(e)}


    def terminate_instance(self, instance_id, region=None):
        ec2 = self._client(region)
        try:
            ec2.terminate_instances(InstanceIds=[instance_id])
            return {
                "status": "ok",
                "message": f"Instance {instance_id} termination started",
                "data": {"terminated": True}
            }
        except Exception as e:
            logger.error(f"terminate_instance failed: {e}")
            return {"status": "fail", "message": str(e)}

    def upgrade_instance_type(self, instance_id, new_instance_type, region=None):
        ec2 = self._client(region)
        try:
            # Stop the instance
            ec2.stop_instances(InstanceIds=[instance_id])
            waiter = ec2.get_waiter("instance_stopped")
            waiter.wait(InstanceIds=[instance_id])

            # Modify instance type
            ec2.modify_instance_attribute(
                InstanceId=instance_id,
                InstanceType={"Value": new_instance_type}
            )

            # Start the instance
            ec2.start_instances(InstanceIds=[instance_id])

            return {
                "status": "ok",
                "message": f"Instance {instance_id} upgraded to {new_instance_type}",
                "data": {"upgraded": True}
            }
        except Exception as e:
            logger.error(f"upgrade_instance_type failed: {e}")
            return {"status": "fail", "message": str(e)}
