import datetime
import json


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
        "bundle": "console",
        "application": "storage-broker",
        "event_type": "upload_rejection",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "account": data.account,
        "events": [
            {
                "metadata": {},
                "payload": json.dumps({
                    "request_id": data.request_id,
                    "reason": data.reason,
                    "system_id": data.system_id,
                    "hostname": data.hostname,
                    "reporter": data.reporter,
                })
            }
        ],
        "context": "{}",
        "recipients": []
    }

    return msg
