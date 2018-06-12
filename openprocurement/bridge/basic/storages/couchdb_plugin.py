# -*- coding: utf-8 -*-
import logging
from requests import Session
from couchdb import Server, Session
from couchdb.design import ViewDefinition
from zope.interface import implementer

from openprocurement.bridge.basic.interfaces import IStorage

LOGGER = logging.getLogger(__name__)
VALIDATE_BULK_DOCS_ID = '_design/validate_date_modified'
VALIDATE_BULK_DOCS_UPDATE = """function(newDoc, oldDoc, userCtx) {
    if (oldDoc && (newDoc.dateModified <= oldDoc.dateModified)) {
        throw({forbidden: 'New doc with oldest dateModified.' });
    };
}"""


@implementer(IStorage)
class CouchDBStorage(object):

    def __init__(self, conf):
        self.config = conf
        user = self.config['storage_config'].get('user', '')
        password = self.config['storage_config'].get('password', '')
        self.bulk_query_limit = self.config['storage_config'].get('bulk_query_limit', 10)
        self.bulk_query_interval = self.config['storage_config'].get('bulk_query_interval', 2)
        if (user and password):
            self.couch_url = "http://{user}:{password}@{host}:{port}".format(
                **self.config['storage_config'])
        else:
            self.couch_url = "http://{host}:{port}".format(**self.config['storage_config'])
        self.db_name = self.config['storage_config'].get('db_name', 'bridge_db')
        self.resource = self.config['resource']
        self._prepare_couchdb()
        self.view_path = '_design/{}/_view/by_dateModified'.format(self.resource)

    def _prepare_couchdb(self):
        server = Server(self.couch_url, session=Session(retry_delays=range(10)))
        try:
            if self.db_name not in server:
                self.db = server.create(self.db_name)
            else:
                self.db = server[self.db_name]
        except Exception as e:
            LOGGER.error('Database error: {}'.format(repr(e)))
            raise

        by_date_modified_view = ViewDefinition(
            self.resource, 'by_dateModified', '''function(doc) {
        if (doc.doc_type == '%(resource)s') {
            var fields=['%(doc_type)sID'], data={};
            for (var i in fields) {
                if (doc[fields[i]]) {
                    data[fields[i]] = doc[fields[i]]
                }
            }
            emit(doc.dateModified, data);
        }}''' % dict(resource=self.resource[:-1].title(), doc_type=self.resource[:-1])
        )
        by_date_modified_view.sync(self.db)

        validate_doc = self.db.get(VALIDATE_BULK_DOCS_ID, {'_id': VALIDATE_BULK_DOCS_ID})
        if validate_doc.get('validate_doc_update') != VALIDATE_BULK_DOCS_UPDATE:
            validate_doc['validate_doc_update'] = VALIDATE_BULK_DOCS_UPDATE
            self.db.save(validate_doc)
            LOGGER.info('Validate document update view saved.')
        else:
            LOGGER.info('Validate document update view already exist.')

    def get_doc(self, doc_id, default=None):
        """
        Trying get doc with doc_id from storage and return doc dict if doc exist else default
        :param doc_id:
        :return: dict: or default
        """
        return self.db.get(doc_id, default)

    def save_doc(self, doc):
        return self.db.save(doc)

    def save_bulk(self, bulk):
        """
        Save to storage bulk data

        :param bulk: Dict where key: doc_id, value: document
        :return: list: List of tuples with id, success: boolean, reason:
        if success is str: state else exception object
        """
        res = self.db.update(bulk.values())
        results = []
        for success, doc_id, reason in res:
            if success:
                if not reason.startswith('1-'):
                    reason = 'updated'
                else:
                    reason = 'created'
            else:
                if reason.message == u'New doc with oldest dateModified.':
                    success = True
                    reason = 'skipped'
            results.append((success, doc_id, reason))
        return results


def includme(config):
    return CouchDBStorage(config)
