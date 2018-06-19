# -*- coding: utf-8 -*-
from gevent import monkey
monkey.patch_all()

import logging
from datetime import datetime
from httplib import IncompleteRead
from time import time, sleep

from gevent.greenlet import Greenlet
from gevent.queue import Empty
from zope.interface import implementer

from openprocurement.bridge.basic.interfaces import IFilter


logger = logging.getLogger(__name__)
INFINITY = True


@implementer(IFilter)
class BasicCouchDBFilter(Greenlet):

    def __init__(self, conf, input_queue, filtered_queue, db):
        logger.info('Init Basic CouchDB Filter')
        Greenlet.__init__(self)
        self.config = conf
        self.input_queue = input_queue
        self.filtered_queue = filtered_queue
        self.db = db
        self.resource = self.config['resource']
        self.view_path = '_design/{}/_view/by_dateModified'.format(self.resource)
        self.bulk_query_interval = self.config['storage_config']['bulk_query_interval']
        self.bulk_query_limit = self.config['storage_config']['bulk_query_limit']

    def _check_bulk(self, bulk, priority_cache):
        sleep_before_retry = 2
        for i in xrange(0, 3):
            try:
                logger.debug(
                    'Send check bulk: {}'.format(len(bulk)), extra={'CHECK_BULK_LEN': len(bulk)}
                )
                start = time()
                rows = self.db.db.view(self.view_path, keys=bulk.values())
                end = time() - start
                logger.debug('Duration bulk check: {} sec.'.format(end), extra={'CHECK_BULK_DURATION': end * 1000})
                resp_dict = {k.id: k.key for k in rows}
                break
            except (IncompleteRead, Exception) as e:
                logger.error('Error while send bulk {}'.format(e.message), extra={'MESSAGE_ID': 'exceptions'})
                if i == 2:
                    raise e
                sleep(sleep_before_retry)
                sleep_before_retry *= 2
        for item_id, date_modified in bulk.items():
            if item_id in resp_dict and date_modified == resp_dict[item_id]:
                logger.debug(
                    'Skipped {} {}: In db exist newest.'.format(self.resource[:-1], item_id),
                    extra={'MESSAGE_ID': 'skipped'}
                )
            elif ((1, item_id) not in self.filtered_queue.queue and
                    (1000, item_id) not in self.filtered_queue.queue):
                self.filtered_queue.put((priority_cache[item_id], item_id))
                logger.debug(
                    'Put to main queue {}: {}'.format(self.resource[:-1], item_id),
                    extra={'MESSAGE_ID': 'add_to_resource_items_queue'}
                )
            else:
                logger.debug(
                    'Skipped {} {}: In queue exist with same id'.format(self.resource[:-1], item_id),
                    extra={'MESSAGE_ID': 'skipped'}
                )

    def _run(self):
        start_time = datetime.now()
        input_dict = {}
        priority_cache = {}
        while INFINITY:
            # Get resource_item from temp queue
            if not self.input_queue.empty():
                priority, resource_item = self.input_queue.get()
            else:
                timeout = self.bulk_query_interval - (datetime.now() - start_time).total_seconds()
                if timeout > self.bulk_query_interval:
                    timeout = self.bulk_query_interval
                try:
                    priority, resource_item = self.input_queue.get(timeout=timeout)
                except Empty:
                    resource_item = None

            # Add resource_item to bulk
            if resource_item is not None:
                logger.debug('Add to input_dict {}'.format(resource_item['id']))
                input_dict[resource_item['id']] = resource_item['dateModified']
                priority_cache[resource_item['id']] = priority

            if (len(input_dict) >= self.bulk_query_limit or (datetime.now() - start_time).total_seconds() >=
                    self.bulk_query_interval):
                if len(input_dict) > 0:
                    self._check_bulk(input_dict, priority_cache)
                    input_dict = {}
                    priority_cache = {}
                start_time = datetime.now()


@implementer(IFilter)
class BasicElasticSearchFilter(BasicCouchDBFilter):

    def __init__(self, conf, input_queue, filtered_queue, db):
        self.config = conf
        self.input_queue = input_queue
        self.filtered_queue = filtered_queue
        self.db = db
        self.bulk_query_interval = self.config['storage_config']['bulk_query_interval']
        self.bulk_query_limit = self.config['storage_config']['bulk_query_limit']

    def _check_bulk(self, bulk, priority_cache):
        logger.debug('Send check bulk: {}'.format(len(bulk)), extra={'CHECK_BULK_LEN': len(bulk)})
        start = time()
        rows = self.db.mget(
            index=self.db.alias, doc_type=self.db.doc_type.title(),
            body={"ids": bulk.keys()}, _source_include="dateModified"
        )
        end = time() - start
        logger.debug('Duration bulk check: {} sec.'.format(end), extra={'CHECK_BULK_DURATION': end * 1000})
        for item in rows['docs']:
            doc_id = item['_id']
            date_modified = item['_source']['dateModified'] if '_source' in item else item['found']
            if date_modified != bulk[doc_id] and ((1, doc_id) not in self.filtered_queue.queue and
                                                  (1000, doc_id) not in self.filtered_queue.queue):
                self.filtered_queue.put((priority_cache[doc_id], doc_id))
            else:
                logger.debug(
                    'Ignored {}: SYNC - {}, ElasticSearch or Queue - {}'.format(doc_id, bulk[doc_id], date_modified),
                    extra={'MESSAGE_ID': 'skipped'}
                )
