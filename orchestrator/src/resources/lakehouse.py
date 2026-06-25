import dagster as dg
from dagster_aws.s3 import S3Resource


class LakehouseResource(S3Resource):
    endpoint_url: str = dg.EnvVar("SEAWEEDFS_ENDPOINT_URL")
    aws_access_key_id: str = dg.EnvVar("SEAWEEDFS_S3_ACCESS_KEY_ID")
    aws_secret_access_key: str = dg.EnvVar("SEAWEEDFS_S3_SECRET_ACCESS_KEY")
