import attr
import json
import logging

from datetime import datetime

from storage_broker.utils import config

logger = logging.getLogger(config.APP_NAME)


@attr.s
class TrackerMessage(object):
    date = attr.ib(default=datetime.now().isoformat())
    service = attr.ib(default=None)
    account = attr.ib(default=None)
    inventory_id = attr.ib(default=None)
    status = attr.ib(default=None)
    status_msg = attr.ib(default=None)

    @classmethod
    def from_json(cls, doc):
        try:
            doc = json.loads(doc)
            doc = {a.name: doc.get(a.name, a.default) for a in attr.fields(TrackerMessage)}
            return cls(**doc)
        except Exception:
            logger.exception("failed to deserialize message: %s", doc)
            raise
