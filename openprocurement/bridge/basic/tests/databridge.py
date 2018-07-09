# -*- coding: utf-8 -*-
from gevent import monkey
monkey.patch_all()

import unittest
import datetime
import logging
import uuid
from copy import deepcopy
from gevent import sleep
from gevent.queue import Queue
from couchdb import Server
from mock import MagicMock, patch
from munch import munchify
from openprocurement_client.exceptions import RequestFailed

from openprocurement.bridge.basic.databridge import BasicDataBridge
from openprocurement.bridge.basic.storages.couchdb_plugin import CouchDBStorage
from openprocurement.bridge.basic.utils import DataBridgeConfigError
from openprocurement.bridge.basic.tests.base import MockedResponse, AlmostAlwaysTrue, TEST_CONFIG


logger = logging.getLogger()
logger.level = logging.DEBUG


class TestBasicDataBridge(unittest.TestCase):

    config = deepcopy(TEST_CONFIG)

    def setUp(self):
        user = self.config['main']['storage_config'].get('user', '')
        password = self.config['main']['storage_config'].get('password', '')
        if (user and password):
            self.couch_url = "http://{user}:{password}@{host}:{port}".format(
                **self.config['main']['storage_config'])
        else:
            self.couch_url = "http://{host}:{port}".format(
                **self.config['main']['storage_config'])
        server = Server(self.couch_url)
        if self.config['main']['storage_config']['db_name'] in server:
            self.db = server[self.config['main']['storage_config']['db_name']]
        else:
            self.db = server.create(self.config['main']['storage_config']['db_name'])

    def tearDown(self):
        user = self.config['main']['storage_config'].get('user', '')
        password = self.config['main']['storage_config'].get('password', '')
        if (user and password):
            couch_url = "http://{user}:{password}@{host}:{port}".format(
                **self.config['main']['storage_config'])
        else:
            couch_url = "http://{host}:{port}".format(
                **self.config['main']['storage_config'])
        try:
            server = Server(couch_url)
            del server[self.config['main']['storage_config']['db_name']]
        except Exception:
            logger.debug('Error while tearDown')

    def test_init(self):
        bridge = BasicDataBridge(self.config)
        self.assertIsInstance(bridge.db, CouchDBStorage)
        for k in self.config['main'].keys():
            self.assertEqual(getattr(bridge, k), self.config['main'][k])

        del bridge
        config = deepcopy(self.config)
        config['main']['resources_api_server'] = ''
        with self.assertRaises(DataBridgeConfigError) as e:
            BasicDataBridge(config)
        self.assertEqual(
            e.exception.message,
            "In config dictionary empty or missing 'resources_api_server'"
        )

        config['main']['resources_api_server'] = 'invalid_server'
        with self.assertRaises(DataBridgeConfigError) as e:
            BasicDataBridge(config)
        self.assertEqual(e.exception.message, "Invalid 'resources_api_server' url.")

        config = deepcopy(self.config)
        config['main']['retrievers_params']['up_wait_sleep'] = 29.9
        with self.assertRaises(DataBridgeConfigError) as e:
            BasicDataBridge(config)
        self.assertEqual(
            e.exception.message,
            "Invalid 'up_wait_sleep' in 'retrievers_params'. Value must be grater than 30."
        )

    @patch('openprocurement.bridge.basic.databridge.APIClient')
    def test_fill_api_clients_queue(self, mock_APIClient):
        bridge = BasicDataBridge(self.config)
        self.assertEqual(bridge.api_clients_queue.qsize(), 0)
        bridge.fill_api_clients_queue()
        self.assertEqual(bridge.api_clients_queue.qsize(),
                         bridge.workers_min)

    def test_fill_input_queue(self):
        bridge = BasicDataBridge(self.config)
        return_value = [(
            1, {'id': uuid.uuid4().hex,
                'dateModified': datetime.datetime.utcnow().isoformat()}
        )]
        bridge.feeder.get_resource_items = MagicMock(return_value=return_value)
        self.assertEqual(bridge.input_queue.qsize(), 0)
        bridge.fill_input_queue()
        self.assertEqual(bridge.input_queue.qsize(), 1)
        self.assertEqual(bridge.input_queue.get(), return_value[0])

    @patch('openprocurement.bridge.basic.databridge.spawn')
    @patch('openprocurement.bridge.basic.workers.BasicResourceItemWorker.spawn')
    @patch('openprocurement.bridge.basic.databridge.APIClient')
    def test_gevent_watcher(self, mock_APIClient, mock_riw_spawn, mock_spawn):
        bridge = BasicDataBridge(self.config)
        bridge.queue_filter = MagicMock()
        bridge.queue_filter.exception = Exception('test_filler')
        bridge.input_queue_filler = MagicMock()
        bridge.input_queue_filler.exception = Exception('test_temp_filler')
        self.assertEqual(bridge.workers_pool.free_count(),
                         bridge.workers_max)
        self.assertEqual(bridge.retry_workers_pool.free_count(),
                         bridge.retry_workers_max)
        bridge.gevent_watcher()
        self.assertEqual(bridge.workers_pool.free_count(),
                         bridge.workers_max - bridge.workers_min)
        self.assertEqual(bridge.retry_workers_pool.free_count(),
                         bridge.retry_workers_max - bridge.retry_workers_min)
        del bridge

    @patch('openprocurement.bridge.basic.databridge.APIClient')
    @patch('openprocurement.bridge.basic.workers.BasicResourceItemWorker.spawn')
    def test_queues_controller(self, mock_riw_spawn, mock_APIClient):
        bridge = BasicDataBridge(self.config)
        bridge.resource_items_queue_size = 10
        bridge.resource_items_queue = Queue(10)
        for i in xrange(0, 10):
            bridge.resource_items_queue.put('a')
        self.assertEqual(len(bridge.workers_pool), 0)
        self.assertEqual(bridge.resource_items_queue.qsize(), 10)
        with patch('__builtin__.True', AlmostAlwaysTrue()):
            bridge.queues_controller()
        self.assertEqual(len(bridge.workers_pool), 1)
        bridge.workers_pool.add(mock_riw_spawn)
        self.assertEqual(len(bridge.workers_pool), 2)

        for i in xrange(0, 10):
            bridge.resource_items_queue.get()
        with patch('__builtin__.True', AlmostAlwaysTrue()):
            bridge.queues_controller()
        self.assertEqual(len(bridge.workers_pool), 1)
        self.assertEqual(bridge.resource_items_queue.qsize(), 0)

    @patch('openprocurement.bridge.basic.databridge.APIClient')
    def test_create_api_client(self, mock_APIClient):
        mock_APIClient.side_effect = [
            RequestFailed(), Exception('Test create client exception'),
            munchify({
                'session': {'headers': {'User-Agent': 'test.agent'}}
            })
        ]
        bridge = BasicDataBridge(self.config)
        self.assertEqual(bridge.api_clients_queue.qsize(), 0)
        bridge.create_api_client()
        self.assertEqual(bridge.api_clients_queue.qsize(), 1)

        del bridge

    @patch('openprocurement_client.api_base_client.Session')
    def test__get_average_request_duration(self, mocked_session):
        mocked_session.request.return_value = MockedResponse(200)
        bridge = BasicDataBridge(self.config)
        bridge.create_api_client()
        bridge.create_api_client()
        bridge.create_api_client()
        res, _ = bridge._get_average_requests_duration()
        self.assertEqual(res, 0)
        request_duration = 1
        for k in bridge.api_clients_info:
            for i in xrange(0, 3):
                bridge.api_clients_info[k]['request_durations'][
                    datetime.datetime.now()] = request_duration
            request_duration += 1
        res, res_list = bridge._get_average_requests_duration()
        self.assertEqual(res, 2)
        self.assertEqual(len(res_list), 3)

        delta = datetime.timedelta(seconds=301)
        grown_date = datetime.datetime.now() - delta
        bridge.api_clients_info[uuid.uuid4().hex] = {
            'request_durations': {grown_date: 1},
            'destroy': False,
            'request_interval': 0,
            'avg_duration': 0
        }
        self.assertEqual(len(bridge.api_clients_info), 4)

        res, res_list = bridge._get_average_requests_duration()
        grown = 0
        for k in bridge.api_clients_info:
            if bridge.api_clients_info[k].get('grown', False):
                grown += 1
        self.assertEqual(res, 1.75)
        self.assertEqual(len(res_list), 4)
        self.assertEqual(grown, 1)

    def test__calculate_st_dev(self):
        bridge = BasicDataBridge(self.config)
        values = [1.1, 1.11, 1.12, 1.13, 1.14]
        stdev = bridge._calculate_st_dev(values)
        self.assertEqual(stdev, 0.014)
        stdev = bridge._calculate_st_dev([])
        self.assertEqual(stdev, 0)

    @patch('openprocurement_client.api_base_client.Session')
    def test__mark_bad_clients(self, mocked_session):
        mocked_session.request.return_value = MockedResponse(200)
        bridge = BasicDataBridge(self.config)
        self.assertEqual(bridge.api_clients_queue.qsize(), 0)
        self.assertEqual(len(bridge.api_clients_info), 0)

        bridge.create_api_client()
        bridge.create_api_client()
        bridge.create_api_client()
        self.assertEqual(len(bridge.api_clients_info), 3)
        avg_duration = 1
        req_intervals = [0, 2, 0, 0]
        for cid in bridge.api_clients_info:
            self.assertEqual(bridge.api_clients_info[cid]['drop_cookies'],
                             False)
            bridge.api_clients_info[cid]['avg_duration'] = avg_duration
            bridge.api_clients_info[cid]['grown'] = True
            bridge.api_clients_info[cid]['request_interval'] = \
                req_intervals[avg_duration]
            avg_duration += 1
        avg = 1.5
        bridge._mark_bad_clients(avg)
        self.assertEqual(len(bridge.api_clients_info), 3)
        self.assertEqual(bridge.api_clients_queue.qsize(), 3)
        to_destroy = 0
        for cid in bridge.api_clients_info:
            if bridge.api_clients_info[cid]['drop_cookies']:
                to_destroy += 1
        self.assertEqual(to_destroy, 3)

    @patch('openprocurement_client.api_base_client.Session')
    def test_perfomance_watcher(self, mocked_session):
        mocked_session.request.return_value = MockedResponse(200)
        bridge = BasicDataBridge(self.config)
        for i in xrange(0, 3):
            bridge.create_api_client()
        req_duration = 1
        for _, info in bridge.api_clients_info.items():
            info['request_durations'][datetime.datetime.now()] = req_duration
            req_duration += 1
            self.assertEqual(info.get('grown', False), False)
            self.assertEqual(len(info['request_durations']), 1)
        self.assertEqual(len(bridge.api_clients_info), 3)
        self.assertEqual(bridge.api_clients_queue.qsize(), 3)
        sleep(1)

        bridge.perfomance_watcher()
        grown = 0
        with_new_cookies = 0
        for cid, info in bridge.api_clients_info.items():
            if info.get('grown', False):
                grown += 1
            if info['drop_cookies']:
                with_new_cookies += 1
            self.assertEqual(len(info['request_durations']), 0)
        self.assertEqual(len(bridge.api_clients_info), 3)
        self.assertEqual(bridge.api_clients_queue.qsize(), 3)
        self.assertEqual(grown, 3)
        self.assertEqual(with_new_cookies, 1)

    @patch('openprocurement.bridge.basic.databridge.BasicDataBridge.fill_input_queue')
    @patch('openprocurement.bridge.basic.databridge.BasicDataBridge.queues_controller')
    @patch('openprocurement.bridge.basic.databridge.BasicDataBridge.perfomance_watcher')
    @patch('openprocurement.bridge.basic.databridge.BasicDataBridge.gevent_watcher')
    def test_run(self, mock_gevent, mock_perfomance, mock_controller, mock_fill_input_queue):
        bridge = BasicDataBridge(self.config)
        self.assertEqual(len(bridge.filter_workers_pool), 0)
        with patch('__builtin__.True', AlmostAlwaysTrue(4)):
            bridge.run()
        self.assertEqual(mock_controller.call_count, 1)
        self.assertEqual(mock_gevent.call_count, 1)
        self.assertEqual(mock_fill_input_queue.call_count, 1)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBasicDataBridge))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
