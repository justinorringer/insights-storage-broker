import signal
import json
import yaml
import attr

from storage_broker.mq import consume, produce, msgs
from storage_broker.storage import aws
from storage_broker.utils import broker_logging, config, metrics
from storage_broker import TrackerMessage, normalizers

from datetime import datetime
from confluent_kafka import KafkaError
from prometheus_client import start_http_server
from functools import partial

logger = broker_logging.initialize_logging()

running = True
producer = None
bucket_map = {}


def start_prometheus():
    start_http_server(config.PROMETHEUS_PORT)


def load_bucket_map(_file):
    try:
        with open(_file, "rb") as f:
            bucket_map = yaml.safe_load(f)
    except Exception as e:
        logger.exception(e)
        bucket_map = {}

    return bucket_map


def handle_signal(signal, frame):
    global running
    running = False


signal.signal(signal.SIGTERM, handle_signal)


def main():

    logger.info("Starting Storage Broker")

    config.log_config()

    if config.PROMETHEUS == "True":
        start_prometheus()
    global bucket_map
    bucket_map = load_bucket_map(config.BUCKET_MAP_FILE)

    consumer = consume.init_consumer()
    global producer
    producer = produce.init_producer()

    while running:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            metrics.message_consume_error_count.inc()
            logger.error("Consumer error: %s", msg.error())
            continue

        metrics.message_consume_count.inc()
        if msg.topic() == config.EGRESS_TOPIC:
            announce(msg.value())
            continue
        try:
            tracker_msg = TrackerMessage.from_json(msg.value().decode("utf-8"))
            data = normalize(bucket_map, msg)
            tracker_msg.status, tracker_msg.status_msg, tracker_msg.date = ("received",
                                                                            "received message",
                                                                            datetime.now().isoformat())
            send_message(config.TRACKER_TOPIC, attr.asdict(tracker_msg))
            if data.topic == config.VALIDATION_TOPIC:
                handle_validation(msg, data, tracker_msg)
            else:
                try:
                    handle_bucket(msg.topic(), data, tracker_msg)
                except Exception:
                    logger.error(f"No map provided for {data.service}")
                    continue
        except Exception:
            metrics.message_json_unpack_error.labels(topic=msg.topic()).inc()
            logger.exception("An error occurred during message processing")

        consumer.commit()
        producer.flush()

    consumer.commit()
    producer.flush()


def handle_bucket(topic, data, tracker_msg):
    try:
        for d in bucket_map[topic]:
            if d["service"] == data.service:
                _map = d
        formatter = _map["format"]
        key = formatter.format(**data.__dict__)
        bucket = _map["bucket"]
    except Exception as e:
        logger.exception("something went wrong: %s", e)
        raise

    aws.copy(data.request_id, config.STAGE_BUCKET, bucket, key)
    metrics.payload_size.labels(service=data.service).observe(data.size)


def handle_validation(msg, data, tracker_msg):
    tracker_msg.status, tracker_msg.status_msg, tracker_msg.date = ("received",
                                                                    "received validation response",
                                                                    datetime.now().isoformat())
    send_message(config.TRACKER_TOPIC, attr.asdict(tracker_msg))
    if data.validation == "success":
        send_message(config.ANNOUNCER_TOPIC, json.loads(msg.value()).decode("utf-8"))
        tracker_msg.status, tracker_msg.status_msg, tracker_msg.date = ("success",
                                                                        f"announced to {config.ANNOUNCER_TOPIC}",
                                                                        datetime.now().isoformat())
        send_message(config.TRACKER_TOPIC, attr.asdict(tracker_msg))
    if data.validation == "failure":
        aws.copy(data.request_id, config.STAGE_BUCKET, config.REJECT_BUCKET, data.request_id)
        tracker_msg.status, tracker_msg.status_msg, tracker_msg.date = ("success",
                                                                        "copied failed payload to rejected bucket",
                                                                        datetime.now().isoformat())
        send_message(config.TRACKER_TOPIC, attr.asdict(tracker_msg))
    else:
        logger.error(f"Invalid validation response: {data.validation}")
        metrics.invalid_validation_status.labels(service=data.service).inc()
        tracker_msg.status, tracker_msg.status_msg, tracker_msg.date = ("error",
                                                                        f"invalid validation response: {data.validation}",
                                                                        datetime.now().isoformat())
        send_message(config.TRACKER_TOPIC, attr.asdict(tracker_msg))


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
        metrics.message_publish_error.inc()
    else:
        logger.info(
            "Message delivered to %s [%s] for request_id [%s]",
            msg.topic(),
            msg.partition(),
            request_id,
        )
        logger.info("Message contents: %s", json.loads(msg.value().decode("utf-8")))
        metrics.message_publish_count.inc()


# This is is a way to support legacy uploads that are expected to be on the
# platform.upload.available queue
def announce(msg):
    msg = json.loads(msg.decode("utf-8"))
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
        available_message, "success", f"sent message to {config.ANNOUNCER_TOPIC}"
    )
    send_message(config.TRACKER_TOPIC, tracker_msg)


def normalize(bucket_map, msg):
    topic = msg.topic()
    data = json.loads(msg.value().decode("utf-8"))
    for d in bucket_map[topic]:
        if d["service"] == data["service"]:
            normalizer = getattr(normalizers, d["normalizer"])()
    normalized_data = normalizer.from_json(data, msg.topic())
    return normalized_data


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
