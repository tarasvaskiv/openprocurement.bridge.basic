# -*- coding: utf-8 -*-
import unittest
from copy import deepcopy
from datetime import datetime
from uuid import uuid4

from couchdb.http import Unauthorized
from mock import MagicMock, call, patch

from openprocurement.bridge.basic.storages.couchdb_plugin import CouchDBStorage
from openprocurement.bridge.basic.tests.base import TEST_CONFIG


class TestCouchDBStorage(unittest.TestCase):

    config = deepcopy(TEST_CONFIG['main'])
    config['storage_config']['user'] = 'taras'
    config['storage_config']['password'] = 'shevchenko'

    @patch('openprocurement.bridge.basic.storages.couchdb_plugin.Server')
    def test_init(self, mocked_server):
        db = CouchDBStorage(self.config)
        self.assertEqual(
            db.couch_url, 'http://{user}:{password}@{host}:{port}'.format(**self.config['storage_config'])
        )

    @patch('openprocurement.bridge.basic.storages.couchdb_plugin.LOGGER')
    def test_prepare_couchdb(self, mocked_logger):
        # mocked_create.side_effect = error('Can\'t create db')
        with self.assertRaises(Unauthorized):
            CouchDBStorage(self.config)
        mocked_logger.error.assert_called_once_with('Database error: {}'.format(repr(Unauthorized(''))))
        config = deepcopy(self.config)
        del config['storage_config']['user']
        del config['storage_config']['password']
        cb = CouchDBStorage(config)
        cb._prepare_couchdb()
        mocked_logger.info.assert_has_calls([call('Validate document update view already exist.')])

    @patch('openprocurement.bridge.basic.storages.couchdb_plugin.Server')
    def test_get_doc(self, mocked_server):
        db = CouchDBStorage(self.config)
        db.db = MagicMock()
        mocked_doc = {
            'id': '1',
            '_id': '1',
            'doc_type': 'Tender',
            '_rev': '1-{}'.format(uuid4().hex)
        }
        db.db.get.return_value = mocked_doc
        doc = db.get_doc('1')
        self.assertEqual(mocked_doc, doc)

    @patch('openprocurement.bridge.basic.storages.couchdb_plugin.Server')
    def test_save_bulk(self, mocked_server):
        storage = CouchDBStorage(self.config)
        doc_id_1 = uuid4().hex
        doc_id_2 = uuid4().hex
        doc_id_3 = uuid4().hex
        doc_id_4 = uuid4().hex

        date_modified = datetime.now().isoformat()
        bulk = {
            doc_id_1: {'id': doc_id_1, 'dateModified': date_modified},
            doc_id_2: {'id': doc_id_2, 'dateModified': date_modified},
            doc_id_3: {'id': doc_id_3, 'dateModified': date_modified},
            doc_id_4: {'id': doc_id_4, 'dateModified': date_modified}
        }
        update_return_value = [
            (True, doc_id_1, '1-' + uuid4().hex),
            (True, doc_id_2, '2-' + uuid4().hex),
            (False, doc_id_3, Exception(u'New doc with oldest dateModified.')),
            (False, doc_id_4, Exception(u'Document update conflict.'))
        ]
        storage.db.update.return_value = update_return_value

        results = storage.save_bulk(bulk)
        successed = 0
        failed = 0

        for r in results:
            if r[0]:
                successed += 1
            else:
                failed += 1

        self.assertEqual(successed, 3)
        self.assertEqual(failed, 1)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCouchDBStorage))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
