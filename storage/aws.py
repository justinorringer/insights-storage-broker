import logging
import boto3
from botocore.exceptions import ClientError

from utils import config

logger = logging.getLogger(config.APP_NAME)

s3 = boto3.client("s3",
                  endpoint_url=config.S3_ENDPOINT_URL,
                  aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                  aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY)


def copy(key):
    copy_src = {"Bucket": config.STAGE_BUCKET,
                "Key": key}

    s3.copy(copy_src, config.REJECT_BUCKET, key)
    s3.delete_object(Bucket=config.STAGE_BUCKET, Key=key)
    logger.info("Request ID [%s] moved to [%s]", key, config.REJECT_BUCKET)


def get_url(key):
    try:
        response = s3.generate_presigned_url('get_object',
                                             Params={'Bucket': config.STAGE_BUCKET,
                                                     'Key': key},
                                             ExpiresIn=86400)
        logger.debug(response)
    except ClientError as e:
        logger.error("Failed to get url for %s", key)
        return None

    return response
