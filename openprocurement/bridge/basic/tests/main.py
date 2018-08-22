# -*- coding: utf-8 -*-

import unittest

from openprocurement.bridge.basic.tests import (
    databridge, workers, test_couchdb_storage, test_elasticsearch_storage, filters
)


def suite():
    tests = unittest.TestSuite()
    tests.addTest(workers.suite())
    tests.addTest(databridge.suite())
    tests.addTest(filters.suite())
    tests.addTest(test_couchdb_storage.suite())
    tests.addTest(test_elasticsearch_storage.suite())
    return tests


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
