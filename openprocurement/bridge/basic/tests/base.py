# -*- coding: utf-8 -*-
import os

from yaml import safe_load

CONFIG_FILE = "{}/test.yml".format(os.path.dirname(__file__))
with open(CONFIG_FILE, 'r') as f:
    TEST_CONFIG = safe_load(f.read())


class MockedResponse(object):

    def __init__(self, status_code, text=None, headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers


class AlmostAlwaysTrue(object):

    def __init__(self, total_iterations=1):
        self.total_iterations = total_iterations
        self.current_iteration = 0

    def __nonzero__(self):
        if self.current_iteration < self.total_iterations:
            self.current_iteration += 1
            return bool(1)
        return bool(0)


class AdaptiveCache(object):

    def __init__(self, data):
        self.data = data

    def get(self, key):
        return self.data.get(key, '')

    def put(self, key, value):
        self.data[key] = value

    def has(self, key):
        return key in self.data

    def __getitem__(self, item):
        return self.data[item]

    def __contains__(self, item):
        return item in self.data
