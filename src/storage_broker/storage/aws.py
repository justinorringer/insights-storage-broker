import logging
import boto3
from botocore.exceptions import ClientError

from storage_broker.utils import config

logger = logging.getLogger(config.APP_NAME)

s3 = boto3.client(
    "s3",
    endpoint_url=config.S3_ENDPOINT_URL,
    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
)


def copy(key, src, dest, new_key):
    copy_src = {"Bucket": src, "Key": key}

    s3.copy(copy_src, dest, new_key)
    s3.delete_object(Bucket=src, Key=key)
    logger.info("Request ID [%s] moved to [%s]", new_key, dest)


def get_url(key, src):
    try:
        response = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": src, "Key": key},
            ExpiresIn=86400,
        )
        logger.debug(response)
    except ClientError:
        logger.error("Failed to get url for %s", key)
        return None

    return response
