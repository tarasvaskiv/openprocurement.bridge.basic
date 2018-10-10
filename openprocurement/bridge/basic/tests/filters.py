# -*- coding: utf-8 -*-
import unittest
from copy import deepcopy
from datetime import datetime
from uuid import uuid4

import jmespath
from gevent.queue import PriorityQueue
from mock import MagicMock, patch, call
from munch import munchify

from openprocurement.bridge.basic.filters import (
    BasicCouchDBFilter,
    BasicElasticSearchFilter,
    JMESPathFilter,
)
from openprocurement.bridge.basic.tests.base import TEST_CONFIG


CONFIG = {
    'filter_config': {
        'statuses': [],
        'procurementMethodTypes': [],
        'lot_status': None,
        'timeout': 0,
        'filters': [],
    },
    'resource': 'tenders'
}


class TestBasicCouchDBFilter(unittest.TestCase):

    config = deepcopy(TEST_CONFIG['main'])
    config['storage_config']['bulk_query_limit'] = 1

    def setUp(self):
        self.old_date_modified = datetime.now().isoformat()
        self.id_1 = uuid4().hex
        self.date_modified_1 = datetime.now().isoformat()
        self.id_2 = uuid4().hex
        self.date_modified_2 = datetime.now().isoformat()
        self.id_3 = uuid4().hex
        self.date_modified_3 = datetime.now().isoformat()
        self.queue = PriorityQueue()
        self.input_queue = PriorityQueue()
        self.db = MagicMock()
        self.bulk = {
            self.id_1: self.date_modified_1,
            self.id_2: self.date_modified_2,
            self.id_3: self.date_modified_3
        }
        self.priority_cache = {self.id_1: 1, self.id_2: 1, self.id_3: 1}
        self.return_value = [
            munchify({'id': self.id_1, 'key': self.date_modified_1}),
            munchify({'id': self.id_2, 'key': self.old_date_modified}),
            munchify({'id': self.id_3, 'key': self.old_date_modified})
        ]
        self.db.db.view.return_value = self.return_value

    def test__check_bulk(self):
        self.queue.put((1000, self.id_3))
        couchdb_filter = BasicCouchDBFilter(self.config, self.input_queue, self.queue, self.db)
        self.assertEqual(self.queue.qsize(), 1)

        couchdb_filter._check_bulk(self.bulk, self.priority_cache)
        self.assertEqual(self.queue.qsize(), 2)

        self.db.db.view.side_effect = [Exception(), Exception(), Exception('test')]
        self.bulk = {}
        with self.assertRaises(Exception) as e:
            couchdb_filter._check_bulk(self.bulk, self.priority_cache)
        self.assertEqual(e.exception.message, 'test')

    @patch('openprocurement.bridge.basic.filters.INFINITY')
    def test__run(self, mocked_infinity):
        couchdb_filter = BasicCouchDBFilter(self.config, self.input_queue, self.queue, self.db)
        self.input_queue.put((1, {'id': self.id_1, 'dateModified': self.date_modified_1}))
        self.input_queue.put((1, {'id': self.id_2, 'dateModified': self.date_modified_2}))
        self.input_queue.put((1, {'id': self.id_3, 'dateModified': self.date_modified_3}))
        mocked_infinity.__nonzero__.side_effect = [True] * 5 + [False, False]
        self.assertEqual(self.queue.qsize(), 0)
        self.assertEqual(self.input_queue.qsize(), 3)

        couchdb_filter._run()
        self.assertEqual(self.queue.qsize(), 2)
        self.assertEqual(self.input_queue.qsize(), 0)


class TestBasicElasticSearchFilter(unittest.TestCase):

    config = deepcopy(TEST_CONFIG['main'])

    def test__check_bulk(self):
        input_queue = PriorityQueue()
        queue = PriorityQueue()
        old_date_modified = datetime.now().isoformat()
        id_1 = uuid4().hex
        date_modified_1 = datetime.now().isoformat()
        id_2 = uuid4().hex
        date_modified_2 = datetime.now().isoformat()
        id_3 = uuid4().hex
        date_modified_3 = datetime.now().isoformat()
        db = MagicMock()
        bulk = {
            id_1: date_modified_1,
            id_2: date_modified_2,
            id_3: date_modified_3
        }
        priority_cache = {id_1: 1, id_2: 1, id_3: 1}
        return_value = {
            u'docs': [
                {
                    u'_type': u'Tender',
                    u'_source': {
                        u'dateModified': date_modified_1
                    },
                    u'_index': u'bridge_tenders',
                    u'_version': 1,
                    u'found': True,
                    u'_id': id_1
                },
                {
                    u'_type': u'Tender',
                    u'_source': {
                        u'dateModified': old_date_modified
                    },
                    u'_index': u'bridge_tenders',
                    u'_version': 1,
                    u'found': True,
                    u'_id': id_2
                },
                {
                    u'found': False,
                    u'_type': u'Tender',
                    u'_id': id_3,
                    u'_index': u'bridge_tenders'
                }
            ]
        }
        db.mget.return_value = return_value
        elastic_filter = BasicElasticSearchFilter(self.config, input_queue, queue, db)
        self.assertEqual(queue.qsize(), 0)

        elastic_filter._check_bulk(bulk, priority_cache)
        self.assertEqual(queue.qsize(), 2)


class TestResourceFilters(unittest.TestCase):
    db = {}
    conf = CONFIG

    @patch('openprocurement.bridge.basic.filters.INFINITY')
    @patch('openprocurement.bridge.basic.filters.logger')
    def test_JMESPathFilter(self, logger, infinity):
        self.input_queue = PriorityQueue()
        self.filtered_queue = PriorityQueue()

        resource = self.conf['resource'][:-1]
        jmes_filter = JMESPathFilter(self.conf, self.input_queue, self.filtered_queue, self.db)
        mock_calls = [call.info('Init Close Framework Agreement JMESPath Filter.')]
        self.assertEqual(logger.mock_calls, mock_calls)
        extra = {'MESSAGE_ID': 'SKIPPED', 'JOURNAL_{}_ID'.format(resource.upper()): 'test_id'}

        infinity.__nonzero__.side_effect = [True, False]
        jmes_filter._run()

        doc = {
            'id': 'test_id',
            'dateModified': '1970-01-01',
            'status': 'draft.pending'
        }

        self.input_queue.put((None, doc))
        self.db['test_id'] = '1970-01-01'
        infinity.__nonzero__.side_effect = [True, False]
        jmes_filter._run()
        mock_calls.append(
            call.info('{} test_id not modified from last check. Skipping'.format(resource.title()),
                      extra=extra)
        )
        self.assertEqual(logger.mock_calls, mock_calls)

        # no filters
        doc['dateModified'] = '1970-01-02'
        self.input_queue.put((None, doc))
        infinity.__nonzero__.side_effect = [True, False]
        jmes_filter._run()
        mock_calls.append(
            call.debug('Put to filtered queue {} test_id {}'.format(resource, doc['status']))
        )
        self.assertEqual(logger.mock_calls, mock_calls)
        priority, filtered_doc = self.filtered_queue.get()
        self.assertIsNone(priority)
        self.assertEqual(filtered_doc, doc)

        # not found
        jmes_filter.filters = [jmespath.compile("contains([`test_status`], status)")]
        doc['status'] = 'spam_status'
        self.input_queue.put((None, doc))
        infinity.__nonzero__.side_effect = [True, False]
        jmes_filter._run()
        mock_calls.append(
            call.info('Skip {} test_id'.format(resource),
                      extra=extra)
        )

        # has found
        doc['status'] = 'test_status'
        self.input_queue.put((None, doc))
        infinity.__nonzero__.side_effect = [True, False]
        jmes_filter._run()
        mock_calls.append(
            call.debug('Put to filtered queue {} test_id {}'.format(resource, doc['status']))
        )
        self.assertEqual(logger.mock_calls, mock_calls)
        priority, filtered_doc = self.filtered_queue.get()
        self.assertIsNone(priority)
        self.assertEqual(filtered_doc, doc)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBasicCouchDBFilter))
    suite.addTest(unittest.makeSuite(TestBasicElasticSearchFilter))
    suite.addTest(unittest.makeSuite(TestResourceFilters))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
