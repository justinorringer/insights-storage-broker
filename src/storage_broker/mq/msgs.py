import datetime


def get_time():
    return datetime.datetime.now().isoformat()


def create_msg(data, status, status_msg):
    msg = {
        "service": "insights-storage-broker",
        "account": data.get("account"),
        "request_id": data.get("request_id"),
        "inventory_id": data.get("id"),
        "status": status,
        "status_msg": status_msg,
        "date": get_time(),
    }

    return msg


def notification_msg(data):
    msg = {
        "version": "v1.1.0",
        "bundle": "rhel",
        "application": "validation",
        "event_type": "upload_rejection",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "account": data.account,
        "events": [
            {
                "metadata": {},
                "payload": """{\n
                    \"request_id\": \"{0}\",\n
                    \"reason\": \"{1}\",\n
                    \"system_id\": \"{2}\",\n
                    \"hostname\": \"{3}\",\n
                    \"reporter\": \"{4}\"\n
            }""".format(data.request_id, data.reason,
                        data.system_id, data.hostname,
                        data.reporter),
            }
        ],
        "context": "{}",
        "recipients": []
    }

    return msg
