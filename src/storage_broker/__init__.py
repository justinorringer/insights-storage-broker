import attr
import json
import logging

from base64 import b64decode

from storage_broker.utils import config

logger = logging.getLogger(config.APP_NAME)


@attr.s
class KeyMap(object):
    org_id = attr.ib(default=None)
    request_id = attr.ib(default="-1")
    category = attr.ib(default=None)
    account = attr.ib(default=None)
    timestamp = attr.ib(default=None)
    cluster_id = attr.ib(default=None)
    metadata = attr.ib(default=dict)
    principal = attr.ib(default=None)
    size = attr.ib(default=None)
    url = attr.ib(default=None)
    service = attr.ib(default="default")
    b64_identity = attr.ib(default=None)

    @classmethod
    def from_json(cls, doc):
        try:
            return cls(**doc)
        except Exception:
            logger.exception("failed to deserialize message: %s", doc)
            raise

    def identity(self):
        return json.loads(b64decode(self.b64_identity))
