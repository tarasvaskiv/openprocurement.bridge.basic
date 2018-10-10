# -*- coding: utf-8 -*-
import logging

from gevent import sleep
from retrying import retry
from uuid import uuid4

from openprocurement_client.clients import APIResourceClient as APIClient
from openprocurement_client.exceptions import (
    RequestFailed,
    ResourceNotFound,
    ResourceGone
)

from openprocurement.bridge.basic.utils import DataBridgeConfigError, journal_context, generate_req_id

CONFIG_MAPPING = {
    'input_resources_api_token': 'resources_api_token',
    'output_resources_api_token': 'resources_api_token',
    'resources_api_version': 'resources_api_version',
    'input_resources_api_server': 'resources_api_server',
    'input_public_resources_api_server': 'public_resources_api_server',
    'input_resource': 'resource',
    'output_resources_api_server': 'resources_api_server',
    'output_public_resources_api_server': 'public_resources_api_server'
}

logger = logging.getLogger(__name__)


class HandlerTemplate(object):

    def __init__(self, config, cache_db):
        self.cache_db = cache_db
        self.handler_config = config['worker_config'].get(self.handler_name, {})
        self.main_config = config
        self.config_keys = ('input_resources_api_token', 'output_resources_api_token', 'resources_api_version',
                            'input_resources_api_server',
                            'input_public_resources_api_server', 'input_resource', 'output_resources_api_server',
                            'output_public_resources_api_server', 'output_resource')
        self.validate_and_fix_handler_config()
        self.initialize_clients()

    def validate_and_fix_handler_config(self):
        for key in self.config_keys:
            if key not in self.handler_config:
                self.handler_config[key] = self.main_config['worker_config'].get(key, '')
        for key in CONFIG_MAPPING.keys():
            if not self.handler_config[key]:
                self.handler_config[key] = self.main_config[CONFIG_MAPPING[key]]

        if not self.handler_config['output_resource']:
            raise DataBridgeConfigError("Missing 'output_resource' in handler configuration.")

    def initialize_clients(self):
        self.output_client = self.create_api_client()
        self.public_output_client = self.create_api_client(read_only=True)
        self.input_client = self.create_api_client(input_resource=True)

    def create_api_client(self, input_resource=False, read_only=False):
        client_user_agent = 'contracting_worker' + '/' + uuid4().hex
        timeout = 0.1
        while 1:
            try:
                if input_resource:
                    api_client = APIClient(host_url=self.handler_config['input_resources_api_server'],
                                           user_agent=client_user_agent,
                                           api_version=self.handler_config['resources_api_version'],
                                           key=self.handler_config['input_resources_api_token'],
                                           resource=self.handler_config['input_resource'])
                else:
                    if read_only:
                        api_client = APIClient(host_url=self.handler_config['output_public_resources_api_server'],
                                               user_agent=client_user_agent,
                                               api_version=self.handler_config['resources_api_version'],
                                               key='',
                                               resource=self.handler_config['output_resource'])
                    else:
                        api_client = APIClient(host_url=self.handler_config['output_resources_api_server'],
                                               user_agent=client_user_agent,
                                               api_version=self.handler_config['resources_api_version'],
                                               key=self.handler_config['output_resources_api_token'],
                                               resource=self.handler_config['output_resource'])
                return api_client
            except RequestFailed as e:
                logger.error('Failed start api_client with status code {}'.format(e.status_code),
                             extra={'MESSAGE_ID': 'exceptions'})
                timeout = timeout * 2
                logger.info('create_api_client will be sleep {} sec.'.format(timeout))
                sleep(timeout)
            except Exception as e:
                logger.error('Failed start api client with error: {}'.format(e.message),
                             extra={'MESSAGE_ID': 'exceptions'})
                timeout = timeout * 2
                logger.info('create_api_client will be sleep {} sec.'.format(timeout))
                sleep(timeout)

    def _put_resource_in_cache(self, resource):
        date_modified = self.cache_db.get(resource['id'])
        if not date_modified or date_modified < resource['dateModified']:
            self.cache_db.put(resource['id'], resource['dateModified'])

    @retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000)
    def get_resource_credentials(self, resource_id):
        self.input_client.headers.update({'X-Client-Request-ID': generate_req_id()})
        logger.info(
            "Getting credentials for tender {}".format(resource_id),
            extra=journal_context({"MESSAGE_ID": "databridge_get_credentials"}, {"TENDER_ID": resource_id})
        )
        data = self.input_client.extract_credentials(resource_id)
        logger.info(
            "Got tender {} credentials".format(resource_id),
            extra=journal_context({"MESSAGE_ID": "databridge_got_credentials"}, {"TENDER_ID": resource_id})
        )
        return data
