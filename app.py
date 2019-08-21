import traceback

from mq import consume
from storage import aws
from utils import broker_logging, config

from botocore.execeptions import ClientError


logger = broker_logging.initialize_logging()

def main():

    logger.info("Starting Storage Broker")

    config.log_config()

    consumer = consume.init_consumer()

    while True:
        for data in consumer:
            key = data.value["request_id"]
            try:
                aws.copy(key)
            except ClientError:
                logger.exception("Failed to copy request ID [%s] to reject bucket",
                                 key)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        the_error = traceback.format_exc()
        logger.error(f"Storage Broker failed with Error: {the_error}")
