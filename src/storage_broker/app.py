import signal
import json
import yaml

from storage_broker.mq import consume, produce, msgs
from storage_broker.storage import aws
from storage_broker.utils import broker_logging, config
from storage_broker import KeyMap

from botocore.exceptions import ClientError
from confluent_kafka import KafkaError
from prometheus_client import start_http_server
from functools import partial
from datetime import datetime

logger = broker_logging.initialize_logging()


def start_prometheus():
    start_http_server(config.PROMETHEUS_PORT)


try:
    with open(config.BUCKET_MAP_FILE, "rb") as f:
        BUCKET_MAP = yaml.safe_load(f)
except Exception as e:
    logger.exception(e)
    BUCKET_MAP = {}

formatter = {}

running = True

producer = None


def handle_signal(signal, frame):
    global running
    running = False


signal.signal(signal.SIGTERM, handle_signal)


def main():

    logger.info("Starting Storage Broker")

    config.log_config()

    consumer = consume.init_consumer()
    global producer
    producer = produce.init_producer()

    while running:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            logger.error("Consumer error: %s", msg.error())
            continue

        try:
            data = json.loads(msg.value().decode("utf-8"))
            if msg.topic() == config.VALIDATION_TOPIC:
                # if it comes in on validation actually check it
                check_validation(data)
            elif msg.topic() == config.STORAGE_TOPIC:
                key, bucket = get_key(data)
                aws.copy(data["request_id"], config.STAGE_BUCKET, bucket, key)
            else:
                # otherwise it comes from egress and we should just reproduce it
                produce_available(data)
        except Exception:
            logger.exception("An error occurred during message processing")

        if not config.KAFKA_AUTO_COMMIT:
            consumer.commit()

        producer.flush()

    consumer.close()
    producer.flush()


def delivery_report(err, msg=None, request_id=None):
    """
    Callback function for produced messages
    """
    if err is not None:
        logger.error(
            "Message delivery for topic %s failed for request_id [%s]: %s",
            msg.topic(),
            err,
            request_id
        )
        logger.info("Message contents: %s", json.loads(msg.value().decode("utf-8")))
    else:
        logger.info(
            "Message delivered to %s [%s] for request_id [%s]",
            msg.topic(),
            msg.partition(),
            request_id,
        )
        logger.info("Message contents: %s", json.loads(msg.value().decode("utf-8")))


def get_key(msg):
    """
    Get the key that will be used when transferring file to the new bucket
    """
    key_map = KeyMap.from_json(msg)
    key_map.timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    if msg["service"] in BUCKET_MAP.keys():
        service = msg["service"]
        ident = key_map.identity()
        key_map.org_id = ident["identity"]["internal"].get("org_id")
        key_map.account = ident["identity"]["account_number"]
        if ident["identity"].get("system"):
            key_map.cluster_id = ident["identity"]["system"].get("cluster_id")
        formatter = BUCKET_MAP[service]["format"]
        key = formatter.format(**key_map.__dict__)
        bucket = BUCKET_MAP[service]["bucket"]
    else:
        key = key_map["request_id"]
        bucket = config.REJECT_BUCKET

    return key, bucket


# This is is a way to support legacy uploads that are expected to be on the
# platform.upload.available queue
def produce_available(msg):
    logger.debug("Incoming Egress Message Content: %s", msg)
    platform_metadata = msg.pop("platform_metadata")
    msg["id"] = msg["host"].get("id")
    if msg["host"].get("system_profile"):
        del msg["host"]["system_profile"]
    available_message = {**msg, **platform_metadata}
    tracker_msg = msgs.create_msg(
        available_message, "received", "received egress message"
    )
    send_message(config.TRACKER_TOPIC, tracker_msg)
    send_message(config.ANNOUNCER_TOPIC, available_message)
    tracker_msg = msgs.create_msg(
        available_message, "success", "sent message to platform.upload.available"
    )
    send_message(config.TRACKER_TOPIC, tracker_msg)


def check_validation(msg):
    if msg.get("validation") == "success":
        logger.info("Validation success for [%s]", msg.get("request_id"))
        send_message(config.ANNOUNCER_TOPIC, msg)
    elif msg.get("validation") == "failure":
        tracker_msg = msgs.create_msg(msg, "received", "received validation response")
        send_message(config.TRACKER_TOPIC, tracker_msg)
        try:
            aws.copy(msg.get("request_id"), config.STAGE_BUCKET, config.REJECT_BUCKET, msg.get("request_id"))
            tracker_msg = msgs.create_msg(
                msg, "success", "copied failed payload to reject bucket"
            )
            send_message(config.TRACKER_TOPIC, tracker_msg)
        except ClientError:
            logger.exception(
                "Unable to move %s to %s bucket",
                config.REJECT_BUCKET,
                msg.get("request_id"),
            )
    else:
        logger.error("Validation status not supported: [%s]", msg.get("validation"))


def send_message(topic, msg):
    try:
        producer.poll(0)
        _bytes = json.dumps(msg, ensure_ascii=False).encode("utf-8")
        producer.produce(topic, _bytes, callback=partial(delivery_report, request_id=msg.get("request_id")))
    except KafkaError:
        logger.exception(
            "Unable to topic [%s] for request id [%s]", topic, msg.get("request_id")
        )


if __name__ == "__main__":
    main()
