import traceback

from mq import consume, produce, msgs
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
                if data.topic == config.CONSUME_TOPIC:
                    check_validation(data.value)
                else:
                    produce_available(data.value)
            except Exception:
                logger.exception("An error occurred during message processing")

        producer.flush()


# This is is a way to support legacy uploads that are expected to be on the
# platform.upload.available queue
def produce_available(msg):
    logger.debug("Incoming Egress Message Content: %s", msg)
    platform_metadata = msg.pop("platform_metadata")
    msg["id"] = msg["host"].get("id")
    if msg["host"].get("system_profile"):
        del msg["host"]["system_profile"]
    available_message = {**msg, **platform_metadata}
    tracker_msg = msgs.create_msg(available_message, "received", "received egress message")
    send_message(config.TRACKER_TOPIC, tracker_msg)
    send_message(config.ANNOUNCER_TOPIC, available_message)
    tracker_msg = msgs.create_msg(available_message, "success", "sent message to platform.upload.available")
    send_message(config.TRACKER_TOPIC, tracker_msg)


def check_validation(msg):
    if msg.get("validation") == "success":
        logger.info("Validation success for [%s]", msg.get("request_id"))
        send_message(config.ANNOUNCER_TOPIC, msg)
    elif msg.get("validation") == "failure":
        tracker_msg = msgs.create_msg(msg, "received", "received validation response")
        send_message(config.TRACKER_TOPIC, tracker_msg)
        try:
            aws.copy(msg.get("request_id"))
            tracker_msg = msgs.create_msg(msg, "success", "copied failed payload to reject bucket")
            send_message(config.TRACKER_TOPIC, tracker_msg)
        except ClientError:
            logger.exception("Unable to move %s to %s bucket", config.REJECT_BUCKET, msg.get("request_id"))
    else:
        logger.error("Validation status not supported: [%s]", msg.get("validation"))


def send_message(topic, msg):
    try:
        producer.send(topic=topic, value=msg)
        logger.debug("Message contents for %s: %s", topic, msg)
        logger.info("Sent message to %s for request_id %s", topic, msg.get("request_id"))
    except KafkaError:
        logger.exception("Unable to topic [%s] for request id [%s]", topic, msg.get("request_id"))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        the_error = traceback.format_exc()
        logger.error(f"Storage Broker failed with Error: {the_error}")
