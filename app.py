import traceback
import requests

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
                handle_message(data.value)
            except Exception:
                logger.exception("An error occurred during message processing")

        producer.flush()


def handle_message(msg):
    logger.debug("Message Contents: %s", msg)
    tracker_msg = msgs.create_msg(msg, "received", "received validation response")
    send_message(config.TRACKER_TOPIC, tracker_msg)
    if msg.get("validation") == "success":
        if msg.get("url") is None:
            url = aws.get_url(msg.get("request_id"))
            if url:
                msg["url"] = url
        if msg.get("id") is None:
            msg["id"] = get_inv_id(msg)
        send_message(config.ANNOUNCER_TOPIC, msg)
        tracker_msg = msgs.create_msg(msg, "success", "sent message to available topic")
        send_message(config.TRACKER_TOPIC, tracker_msg)
        logger.info("Sent success message to %s for request %s", config.ANNOUNCER_TOPIC, msg.get("request_id"))
    elif msg.get("validation") == "failure":
        try:
            aws.copy(msg.get("request_id"))
            tracker_msg = msgs.create_msg(msg, "success", "copied rejected payload to rejected bucket")
            send_message(config.TRACKER_TOPIC, tracker_msg)
        except ClientError:
            logger.exception("Unable to move %s to rejected bucket", msg.get("request_id"))
    else:
        logger.error("Validation key not found or incorrect for %s: [%s]", msg.get("request_id"), msg.get("validation"))


def send_message(topic, msg):
    try:
        producer.send(topic=topic, value=msg)
    except KafkaError:
        logger.exception("Unable to topic [%s] for request id [%s]", topic, msg.get("request_id"))


def get_inv_id(msg):
    headers = {"x-rh-identity": msg["b64_identity"]}
    query_string = "?insights_id={}".format(msg.get("insights_id"))
    r = requests.get(config.INVENTORY_URL + query_string, headers=headers).json()
    try:
        result = r["results"][0]["id"]
        logger.debug("Got inventory ID successfully for [%s] - [%s]", msg.get("request_id"), result)
    except (KeyError, IndexError):
        logger.error("unable to get inventory ID for request: %s", msg["request_id"])
        result = None

    return result


if __name__ == "__main__":
    try:
        main()
    except Exception:
        the_error = traceback.format_exc()
        logger.error(f"Storage Broker failed with Error: {the_error}")
