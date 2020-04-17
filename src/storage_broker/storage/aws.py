import logging
import boto3
from botocore.exceptions import ClientError

from storage_broker.utils import config
from storage_broker.utils import metrics

logger = logging.getLogger(config.APP_NAME)

s3 = boto3.client(
    "s3",
    endpoint_url=config.S3_ENDPOINT_URL,
    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
)


@metrics.storage_copy_time.time()
def copy(key, src, dest, new_key):
    copy_src = {"Bucket": src, "Key": key}
    try:
        s3.copy(copy_src, dest, new_key)
        s3.delete_object(Bucket=src, Key=key)
        logger.info("Request ID [%s] moved to [%s]", new_key, dest)
        metrics.storage_copy_success.inc()
    except Exception:
        logger.exception("Failed to copy Request ID [%s]")
        metrics.storage_copy_error.inc()


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
