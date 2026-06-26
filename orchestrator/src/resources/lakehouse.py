import boto3
import dagster as dg
from botocore.config import Config
from dagster_aws.s3 import S3Resource


class LakehouseResource(S3Resource):
    endpoint_url: str = dg.EnvVar("SEAWEEDFS_ENDPOINT_URL")
    aws_access_key_id: str = dg.EnvVar("SEAWEEDFS_S3_ACCESS_KEY_ID")
    aws_secret_access_key: str = dg.EnvVar("SEAWEEDFS_S3_SECRET_ACCESS_KEY")
    region_name: str = "us-east-1"

    def get_client(self):
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name,
            config=Config(s3={"addressing_style": "path"}),
        )
