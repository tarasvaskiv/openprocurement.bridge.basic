# -*- coding: utf-8 -*-
import unittest

from mock import MagicMock, patch
from openprocurement.bridge.basic.storages.redis_plugin import redis_includeme, lazy_includeme


class TestDbs(unittest.TestCase):

    def setUp(self):
        self.config = {
            'storage_config': {
                'cache_host': '127.0.0.1',
                'cache_port': '6379',
                'cache_db_name': '0'
            }
        }
        with patch('openprocurement.bridge.basic.storages.redis_plugin.redis') as mocked_redis:
            StrictRedis_mock = MagicMock()
            StrictRedis_mock.configure_mock(**{'set': None, 'exists': None})
            mocked_redis.StrictRedis.return_value = StrictRedis_mock

            self.db = redis_includeme(self.config)
        self.db.db = dict()

        def set_value(key, value):
            self.db.db[key] = value

        self.db.set_value = set_value
        self.db.has_value = lambda x: x in self.db.db

    @patch('openprocurement.bridge.basic.storages.redis_plugin.redis')
    def test_redis_includeme(self, mocked_redis):
        config = {
            'storage_config': {
                'cache_host': '127.0.0.1',
                'cache_port': '6379',
                'cache_db_name': '0'
            }
        }
        StrictRedis_mock = MagicMock()
        StrictRedis_mock.configure_mock(**{'set': None, 'exists': None})
        mocked_redis.StrictRedis.return_value = StrictRedis_mock

        db = redis_includeme(config)

        self.assertEqual(db._backend, 'redis')
        self.assertEqual(db._db_name, config['storage_config']['cache_db_name'])
        self.assertEqual(db._port, config['storage_config']['cache_port'])
        self.assertEqual(db._host, config['storage_config']['cache_host'])
        self.assertEqual(db._host, config['storage_config']['cache_host'])
        self.assertEqual(db.set_value, None)
        self.assertEqual(db.has_value, None)

    @patch('openprocurement.bridge.basic.storages.redis_plugin.Db')
    def test_cache_host_in_config(self, mocked_db):
        db = lazy_includeme(self.config)

        self.assertEqual(db._backend, 'lazydb')
        self.assertEqual(db._db_name, self.config['storage_config']['cache_db_name'])

    def test_get(self):
        self.assertEquals(self.db.get('test'), None)
        self.db.set_value('test', 'test')
        self.assertEquals(self.db.get('test'), 'test')

    def test_put(self):
        self.db.put('test_put', 'test_put')
        self.assertEquals(self.db.get('test_put'), 'test_put')

    def test_has(self):
        self.assertEquals(self.db.has('test_has'), False)
        self.db.set_value('test_has', 'test_has')
        self.assertEquals(self.db.has('test_has'), True)