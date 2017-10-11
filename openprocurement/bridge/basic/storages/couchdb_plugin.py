# -*- coding: utf-8 -*-
import logging
from couchdb import Server, Session
from couchdb.design import ViewDefinition
from gevent import sleep
from httplib import IncompleteRead
from socket import error


LOGGER = logging.getLogger(__name__)
VALIDATE_BULK_DOCS_ID = '_design/validate_date_modified'
VALIDATE_BULK_DOCS_UPDATE = """function(newDoc, oldDoc, userCtx) {
    if (oldDoc && (newDoc.dateModified <= oldDoc.dateModified)) {
        throw({forbidden: 'New doc with oldest dateModified.' });
    };
}"""


class CouchDBStorage(object):

    def __init__(self, conf, resource):
        self.config = conf
        user = self.config['storage'].get('user', '')
        password = self.config['storage'].get('password', '')
        if (user and password):
            self.couch_url = "http://{user}:{password}@{host}:{port}".format(
                **self.config['storage'])
        else:
            self.couch_url = "http://{host}:{port}".format(
                **self.config['storage'])
        self.db_name = self.config['storage'].get('db_name', 'bridge_db')
        self.resource = resource
        self._prepare_couchdb()
        self.view_path = '_design/{}/_view/by_dateModified'.format(
            self.resource)

    def _prepare_couchdb(self):
        server = Server(self.couch_url,
                        session=Session(retry_delays=range(10)))
        try:
            if self.db_name not in server:
                self.db = server.create(self.db_name)
            else:
                self.db = server[self.db_name]
        except error as e:
            LOGGER.error('Database error: {}'.format(e.message))
            raise Exception(e.strerror)

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
        }}''' % dict(resource=self.resource[:-1].title(),
                    doc_type=self.resource[:-1])
        )
        by_date_modified_view.sync(self.db)

        validate_doc = self.db.get(VALIDATE_BULK_DOCS_ID,
                                   {'_id': VALIDATE_BULK_DOCS_ID})
        if validate_doc.get('validate_doc_update') != VALIDATE_BULK_DOCS_UPDATE:
            validate_doc['validate_doc_update'] = VALIDATE_BULK_DOCS_UPDATE
            self.db.save(validate_doc)
            LOGGER.info('Validate document update view saved.')
        else:
            LOGGER.info('Validate document update view already exist.')

    def get_doc(self, doc_id):
        """
        Trying get doc with doc_id from storage and return doc dict if
        doc exist else None
        :param doc_id:
        :return: dict: or None
        """
        doc = self.db.get(doc_id)
        return doc


    def filter_bulk(self, bulk):
        """
        Receiving list of docs ids and checking existing in storage, return
        dict where key is doc_id and value - dateModified if doc exist
        :param keys: List of docs ids
        :return: dict: key: doc_id, value: dateModified
        """
        sleep_before_retry = 2
        for i in xrange(0, 3):
            try:
                rows = self.db.view(self.view_path, keys=bulk.values())
                resp_dict = {k.id: k.key for k in rows}
                return resp_dict
            except (IncompleteRead, Exception) as e:
                LOGGER.error('Error while send bulk {}'.format(e.message),
                             extra={'MESSAGE_ID': 'exceptions'})
                if i == 2:
                    raise e
                sleep(sleep_before_retry)
                sleep_before_retry *= 2

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
    resource = config.get('main', {}).get('resource')
    config['storage_obj'] = CouchDBStorage(config['main'], resource)