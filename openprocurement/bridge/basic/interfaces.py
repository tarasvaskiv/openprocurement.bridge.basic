# -*- coding: utf-8 -*-
from zope.interface import Interface


class IStorage(Interface):
    """ Storage Interface """

    def __init__(config):
        """
        Initialize storage object

        :param config: Dictionary with databridge config
        """

    def get_doc(doc_id, default=None):
        """
        Trying retrieve document from storage by doc_id

        :param string doc_id: Document id
        :param obj default: Default value which will be returned if document don't exist in storage with entered id
        :return: Document object or default value
        :rtype: dict
        """

    def save_doc(doc):
        """
        Save document to storage

        :param dict doc: Document
        """

    def save_bulk(doc):
        """
        Save to storage bulk documents

        :param dict bulk: Dictionary where key is doc_id, value - document data
        :return: List of tuples with doc_id, success: boolean, reason: if success is state as string
        else exception object
        :rtype: list
        """


class IFilter(Interface):
    """ Databridge Filter Interface based on `gevent.greenlet.Greenlet` """

    def __init__(conf, input_queue, filtered_queue, db):
        """
        Filter initialization

        :param dict conf: Dictionary with databridge configuration.
        :param queue input_queue: Input queue with all items received from CDB.
        :param queue filtered_queue: Queue where will be stored filtered items.
        :param object db: Database object where store documents
        """

    def _run():
        """ Method which start filtering """


class IWorker(Interface):
    """ Databridge Worker Interface based on `gevent.greenlet.Greenlet` """
