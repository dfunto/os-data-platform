import os
from dagster_aws.s3 import S3Resource


class LakehouseResource(S3Resource):
    endpoint_url: str = os.environ["TODO_ADD_ENDPOINT_URL_FROM_HELM"]
    aws_access_key_id: str = os.environ["TODO_ADD_KEY_FROM_HELM"]
    aws_secret_access_key: str = os.environ["TODO_ADD_SECRET_FROM_HELM"]
