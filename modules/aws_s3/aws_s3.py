import boto3
import os
from botocore.exceptions import ClientError
from commons.logs import get_logger

logger = get_logger("aws_s3")

class AwsS3:
    def __init__(self, context, **module_config):
        self.context = context
        self.s3 = boto3.client("s3")

    def upload_file(self, bucket, key, file_path):
        try:
            self.s3.upload_file(file_path, bucket, key)
            return {
                "status": "ok",
                "message": f"Uploaded {file_path} to s3://{bucket}/{key}",
                "data": {"bucket": bucket, "key": key}
            }
        except Exception as e:
            logger.error(f"upload_file failed: {e}")
            return {"status": "fail", "message": str(e)}

    def download_file(self, bucket, key, destination_path):
        try:
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            self.s3.download_file(bucket, key, destination_path)
            return {
                "status": "ok",
                "message": f"Downloaded s3://{bucket}/{key} to {destination_path}",
                "data": {"local_path": destination_path}
            }
        except Exception as e:
            logger.error(f"download_file failed: {e}")
            return {"status": "fail", "message": str(e)}

    def generate_presigned_url(self, bucket, key, expires_in=3600):
        try:
            url = self.s3.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expires_in
            )
            return {
                "status": "ok",
                "message": f"Presigned URL generated for s3://{bucket}/{key}",
                "data": {"url": url}
            }
        except Exception as e:
            logger.error(f"generate_presigned_url failed: {e}")
            return {"status": "fail", "message": str(e)}

    def list_objects(self, bucket, prefix=""):
        try:
            result = self.s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            files = [obj["Key"] for obj in result.get("Contents", [])]
            return {
                "status": "ok",
                "message": f"Found {len(files)} objects in s3://{bucket}/{prefix}",
                "data": {"files": files}
            }
        except Exception as e:
            logger.error(f"list_objects failed: {e}")
            return {"status": "fail", "message": str(e)}

    def object_exists(self, bucket, key):
        try:
            self.s3.head_object(Bucket=bucket, Key=key)
            return {
                "status": "ok",
                "message": f"s3://{bucket}/{key} exists",
                "data": {"exists": True}
            }
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                return {
                    "status": "ok",
                    "message": f"s3://{bucket}/{key} does not exist",
                    "data": {"exists": False}
                }
            logger.error(f"object_exists failed: {e}")
            return {"status": "fail", "message": str(e)}

    def get_object_metadata(self, bucket, key):
        try:
            result = self.s3.head_object(Bucket=bucket, Key=key)
            return {
                "status": "ok",
                "message": f"Metadata retrieved for s3://{bucket}/{key}",
                "data": {
                    "size": result["ContentLength"],
                    "last_modified": result["LastModified"].isoformat(),
                    "content_type": result.get("ContentType"),
                    "etag": result.get("ETag")
                }
            }
        except Exception as e:
            logger.error(f"get_object_metadata failed: {e}")
            return {"status": "fail", "message": str(e)}

    def delete_object(self, bucket, key):
        try:
            self.s3.delete_object(Bucket=bucket, Key=key)
            return {
                "status": "ok",
                "message": f"Deleted s3://{bucket}/{key}",
                "data": {"deleted": True}
            }
        except Exception as e:
            logger.error(f"delete_object failed: {e}")
            return {"status": "fail", "message": str(e)}
