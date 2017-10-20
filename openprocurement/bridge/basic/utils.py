# -*- coding: utf-8 -*-
import os
from pytz import timezone

TZ = timezone(os.environ['TZ'] if 'TZ' in os.environ else 'Europe/Kiev')


class DataBridgeConfigError(Exception):
    pass

