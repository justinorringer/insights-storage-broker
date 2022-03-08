import json

from logging import StringTemplateStyle
from storage_broker.mq.msgs import notification_msg
from storage_broker.normalizers import Validation


MSG = {
    "account": "000001",
    "org_id": "123456",
    "reporter": "puptoo",
    "request_id": "12345",
    "system_id": "abdc-1234",
    "hostname": "hostname",
    "validation": "failure",
    "service": "advisor",
    "reason": "error unpacking archive",
    "size": "12345",
}


def test_validation_normalizer():
    normalizer = Validation()
    data = normalizer.from_json(MSG)
    assert data.account == "000001"
    assert data.org_id == "123456"


def test_notification_msg():
    normalizer = Validation()
    data = normalizer.from_json(MSG)
    msg = notification_msg(data)
    assert type(msg["events"][0]["payload"]) == str
    assert msg["version"] == "v1.1.0"
    assert msg["bundle"] == "console"
    assert msg["application"] == "storage-broker"
    assert msg["event_type"] == "upload-rejection"
    assert msg["account"] == "000001"
    assert msg["events"][0]["metadata"] == {}

    payload = json.loads(msg["events"][0]["payload"])
    assert payload["request_id"] == "12345"
    assert payload["reason"] == "error unpacking archive"
    assert payload["system_id"] == "abdc-1234"
    assert payload["hostname"] == "hostname"
    assert payload["reporter"] == "puptoo"
