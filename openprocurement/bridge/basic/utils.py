# -*- coding: utf-8 -*-
import os
from pytz import timezone
from uuid import uuid4

TZ = timezone(os.environ['TZ'] if 'TZ' in os.environ else 'Europe/Kiev')


class DataBridgeConfigError(Exception):
    pass


def journal_context(record={}, params={}):
    for k, v in params.items():
        record["JOURNAL_" + k] = v
    return record


def generate_req_id():
    return b'contracting-data-bridge-req-' + str(uuid4()).encode('ascii')
