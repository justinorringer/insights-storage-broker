import traceback

from mq import consume, produce
from storage import aws
from utils import broker_logging, config

from botocore.exceptions import ClientError
from kafka.errors import KafkaError


logger = broker_logging.initialize_logging()

producer = None


def main():

    logger.info("Starting Storage Broker")

    config.log_config()

    consumer = consume.init_consumer()
    global producer
    producer = produce.init_producer()

    while True:
        for data in consumer:
            try:
                handle_message(data.value)
            except Exception:
                logger.exception("An error occurred during message processing")

        producer.flush()


def handle_message(msg):
    logger.debug("Message Contents: %s", msg)
    if msg.get("validation") == "success":
        if msg.get("url") is None:
            url = aws.get_url(msg.get("request_id"))
            if url:
                msg["url"] = url
        send_message(config.ANNOUNCER_TOPIC, msg)
        logger.info("Sent success message to %s for request %s", config.ANNOUNCER_TOPIC, msg.get("request_id"))
    elif msg.get("validation") == "failure":
        try:
            aws.copy(msg.get("request_id"))
        except ClientError:
            logger.exception("Unable to move %s to rejected bucket", msg.get("request_id"))
    else:
        logger.error("Validation key not found or incorrect for %s: [%s]", msg.get("request_id"), msg.get("validation"))


def send_message(topic, msg):
    try:
        producer.send(topic=topic, value=msg)
    except KafkaError:
        logger.exception("Unable to topic [%s] for request id [%s]", topic, msg.get("request_id"))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        the_error = traceback.format_exc()
        logger.error(f"Storage Broker failed with Error: {the_error}")
