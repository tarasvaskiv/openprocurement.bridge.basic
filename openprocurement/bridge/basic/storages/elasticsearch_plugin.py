# -*- coding: utf-8 -*-
import logging
from functools import partial

from elasticsearch import Elasticsearch
from zope.interface import implementer

from openprocurement.bridge.basic.interfaces import IStorage

LOGGER = logging.getLogger(__name__)
STORAGE_DEFAULTS = {
    'host': '127.0.0.1',
    'port': '9200',
    'db_name': 'bridge_db',
    'alias': 'bridge'
}


@implementer(IStorage)
class ElasticsearchStorage(object):

    def __init__(self, conf):
        STORAGE_DEFAULTS.update(conf.get('storage_config', {}))
        for name, value in STORAGE_DEFAULTS.items():
            setattr(self, name, value)
        self.doc_type = conf['resource']
        self.db = Elasticsearch('{}:{}'.format(self.host, self.port))
        self.db.indices.create(index=self.db_name, ignore=400)
        self.db.indices.put_alias(index=self.db_name, name=self.alias)
        settings = self.db.indices.get_settings(index=self.db_name, name='index.mapping.total_fields.limit')
        if settings.get(self.db_name, {}).get(u'settings', {}).get(u'index', {}).get(u'mapping', {}) \
                   .get(u'total_fields', {}).get(u'limit', u'1000') != u'4000':
            self.db.indices.put_settings(body={'index.mapping.total_fields.limit': 4000}, index=self.db_name)
        self.db.index_get = partial(self.db.get, index=self.alias)
        self.db.index_bulk = partial(self.db.bulk, index=self.alias)

    def save_bulk(self, bulk):
        """
        Save to storage bulk data
        :param bulk: Dict where key: doc_id, value: document
        :return: list: List of tuples with id, success: boolean, message: str
        """
        body = []
        for k, v in bulk.items():
            doc = v.copy()
            del doc['_id']
            if '_ver' in doc:
                body.append({
                    "index": {"_id": k, "_type": self.doc_type.title(),
                              "_index": self.alias, '_version': doc['_ver']}
                })
                del doc['_ver']
            else:
                body.append({
                    "index": {"_id": k, "_type": self.doc_type.title(),
                              "_index": self.alias}
                })
            body.append(doc)
        res = self.db.index_bulk(body=body, doc_type=self.doc_type.title())
        results = []
        for item in res['items']:
            success = item['index']['status'] in [200, 201]
            doc_id = item['index']['_id']
            result = item['index']['result'] if 'result' in item['index'] else item['index']['error']['reason']
            if not success and result != u'Mapping reason message':
                # TODO: Catch real mapping message and replace ^
                result = 'skipped'
                success = True
            results.append((success, doc_id, result))
        return results

    def get_doc(self, doc_id):
        """
        Trying get doc with doc_id from storage and return doc dict if
        doc exist else None
        :param doc_id:
        :return: dict: or None
        """
        doc = self.db.index_get(doc_type=self.doc_type.title(), id=doc_id, ignore=[404])
        if doc and '_source' in doc:
            source = doc['_source']
            ver = doc['_version']
            doc = source
            doc['_ver'] = ver
        else:
            doc = None
        return doc

    def save_doc(doc):
        pass


def includme(config):
    return ElasticsearchStorage(config)
