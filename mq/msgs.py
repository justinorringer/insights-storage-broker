import datetime


def get_time():
    return datetime.datetime.now().isoformat()


def create_msg(data, status, status_msg):
    msg = {"service": "insights-storage-broker",
           "account": data["platform_metadata"].get("account"),
           "payload_id": data["platform_metadata"].get("request_id"),
           "inventory_id": data["host"].get("id"),
           "status": status,
           "status_msg": status_msg,
           "date": get_time()}

    return msg
