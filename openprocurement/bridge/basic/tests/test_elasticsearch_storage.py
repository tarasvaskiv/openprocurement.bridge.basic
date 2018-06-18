# -*- coding: utf-8 -*-
import unittest
from copy import deepcopy

from mock import patch

from openprocurement.bridge.basic.storages.elasticsearch_plugin import (ElasticsearchStorage,
                                                                        includme)
from openprocurement.bridge.basic.tests.base import TEST_CONFIG


class TestElasticsearchStorage(unittest.TestCase):

    config = deepcopy(TEST_CONFIG['main'])
    id_1 = '2bf7359509c2436d96f903c745d09ab5'
    id_2 = 'ffb2de965f02491bb44a9209cdc5c320'

    @patch('openprocurement.bridge.basic.storages.elasticsearch_plugin.Elasticsearch')
    def test_save_bulk(self, mocked_elastic):
        id_3 = '4dbb346095554f788b568c5c29e9ef23'
        id_4 = 'ae50ea25bb1349898600ab380ee74e57'
        response = {
            u'items': [
                {
                    u'index': {
                        u'status': 201,
                        u'_type': u'Tender',
                        u'_shards': {
                            u'successful': 1,
                            u'failed': 0,
                            u'total': 3
                        },
                        u'_index': u'bridge_tenders',
                        u'_version': 1,
                        u'created': True,
                        u'result': u'created',
                        u'_id': u'2bf7359509c2436d96f903c745d09ab5'
                    }
                },
                {
                    u'index': {
                        u'status': 200,
                        u'_type': u'Tender',
                        u'_shards': {
                            u'successful': 1,
                            u'failed': 0,
                            u'total': 3
                        },
                        u'_index': u'bridge_tenders',
                        u'_version': 2,
                        u'created': False,
                        u'result': u'updated',
                        u'_id': u'ffb2de965f02491bb44a9209cdc5c320'
                    }
                },
                {
                    u'index': {
                        u'status': 400,
                        u'error': {
                            u'reason': u'Mapping reason message'
                        },
                        u'_id': u'ae50ea25bb1349898600ab380ee74e57'
                    }
                },
                {
                    u'index': {
                        u'status': 403,
                        u'error': {
                            u'reason': u'Forbidden'
                        },
                        u'_id': u'4dbb346095554f788b568c5c29e9ef23'
                    }
                }
            ],
            u'errors': False,
            u'took': 367
        }
        mocked_elastic().indices.get_settings.return_value = {}
        db = ElasticsearchStorage(self.config)
        db.db.bulk.return_value = response
        bulk = {
            self.id_1: {
                'id': self.id_1,
                '_id': self.id_1,
                '_ver': 1,
                'doc_type': 'Tender'
            },
            self.id_2: {
                '_id': self.id_2,
                'id': self.id_2,
                'doc_type': 'Tender'
            },
            id_3: {
                '_id': id_3,
                'id': id_3,
                'doc_type': 'Tender'
            },
            id_4: {
                '_id': id_4,
                'id': id_4,
                'doc_type': 'Tender'
            }
        }
        results = db.save_bulk(bulk)
        created = 0
        updated = 0
        skipped = 0
        add_to_retry = 0
        for success, doc_id, result in results:
            if success and result == 'updated':
                updated += 1
            if success and result == 'created':
                created += 1
            if success and result == 'skipped':
                skipped += 1
            if not success and result == 'Mapping reason message':
                add_to_retry += 1
        self.assertEqual([1, 1, 1, 1], [created, updated, skipped, add_to_retry])

    @patch('openprocurement.bridge.basic.storages.elasticsearch_plugin.Elasticsearch')
    def test_get_doc(self, mocked_elastic):
        mocked_elastic().indices.get_settings.return_value = {}
        db = ElasticsearchStorage(self.config)
        db.db.get.return_value = {}
        doc = db.get_doc(self.id_1)
        self.assertIs(doc, None)
        db.db.get.return_value = {'_source': {'id': self.id_2}, '_version': 1}
        doc = db.get_doc(self.id_2)
        self.assertEqual(doc, {'id': self.id_2, '_ver': 1})
        self.assertEqual(db.doc_type, self.config['resource'])

    @patch('openprocurement.bridge.basic.storages.elasticsearch_plugin.Elasticsearch')
    def test_includme(self, mocked_elastic):
        config = {'resource': 'lots'}
        self.assertIs(config.get('storage_obj'), None)
        class_instance = includme(config)
        self.assertIsInstance(class_instance, ElasticsearchStorage)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestElasticsearchStorage))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
