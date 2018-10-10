import unittest

from copy import deepcopy
from datetime import datetime
from mock import patch, MagicMock, call

from openprocurement_client.exceptions import (
    RequestFailed,
    ResourceNotFound,
    ResourceGone
)

from openprocurement.bridge.basic.tests.base import AdaptiveCache
from openprocurement.bridge.basic.handlers import HandlerTemplate, logger
from openprocurement.bridge.basic.utils import DataBridgeConfigError


class CustomObjectMaker(HandlerTemplate):

    def __init__(self, config, cache_db):
        logger.info("Init Close Framework Agreement UA Handler.")
        self.handler_name = 'handler_cfaua'
        super(CustomObjectMaker, self).__init__(config, cache_db)
        self.basket = {}
        self.keys_from_tender = ('procuringEntity',)


class TestCustomObjectMaker(unittest.TestCase):
    config = {'worker_config': {'handler_cfaua': {
        'input_resources_api_token': 'resources_api_token',
        'output_resources_api_token': 'resources_api_token',
        'resources_api_version': 'resources_api_version',
        'input_resources_api_server': 'resources_api_server',
        'input_public_resources_api_server': 'public_resources_api_server',
        'input_resource': 'resource',
        'output_resources_api_server': 'resources_api_server',
        'output_public_resources_api_server': 'public_resources_api_server',
        'output_resource': 'output_resource'
    }}}

    @patch('openprocurement.bridge.basic.handlers.APIClient')
    @patch('openprocurement.bridge.basic.tests.handlers.logger')
    def test_init(self, mocked_logger, mocked_client):
        handler = CustomObjectMaker(self.config, 'cache_db')

        self.assertEquals(handler.cache_db, 'cache_db')
        self.assertEquals(handler.handler_config, self.config['worker_config']['handler_cfaua'])
        self.assertEquals(handler.main_config, self.config)
        self.assertEquals(handler.config_keys,
                          ('input_resources_api_token', 'output_resources_api_token', 'resources_api_version',
                           'input_resources_api_server',
                           'input_public_resources_api_server', 'input_resource', 'output_resources_api_server',
                           'output_public_resources_api_server', 'output_resource')
                          )
        self.assertEquals(handler.keys_from_tender, ('procuringEntity',))
        mocked_logger.info.assert_called_once_with('Init Close Framework Agreement UA Handler.')

    @patch('openprocurement.bridge.basic.handlers.APIClient')
    @patch('openprocurement.bridge.basic.handlers.logger')
    def test_validate_and_fix_handler_config(self, mocked_logger, mocked_client):
        temp_comfig = deepcopy(self.config)
        temp_comfig['resource'] = temp_comfig['worker_config']['handler_cfaua']['input_resource']
        del temp_comfig['worker_config']['handler_cfaua']['input_resource']

        handler = CustomObjectMaker(temp_comfig, 'cache_db')

        self.assertEquals(handler.handler_config['input_resource'], 'resource')

        temp_comfig = deepcopy(self.config)
        del temp_comfig['worker_config']['handler_cfaua']['output_resource']

        with self.assertRaises(DataBridgeConfigError) as e:
            handler = CustomObjectMaker(temp_comfig, 'cache_db')
            self.assertEquals(e.message, "Missing 'output_resource' in handler configuration.")

    @patch('openprocurement.bridge.basic.handlers.APIClient')
    @patch('openprocurement.bridge.basic.handlers.logger')
    def test_initialize_clients(self, mocked_logger, mocked_client):
        handler = CustomObjectMaker(self.config, 'cache_db')
        self.assertEquals(isinstance(handler.output_client, MagicMock), True)
        self.assertEquals(isinstance(handler.public_output_client, MagicMock), True)
        self.assertEquals(isinstance(handler.input_client, MagicMock), True)

    @patch('openprocurement.bridge.basic.handlers.sleep')
    @patch('openprocurement.bridge.basic.handlers.APIClient')
    @patch('openprocurement.bridge.basic.handlers.logger')
    def test_create_api_client(self, mocked_logger, mocked_client, mocked_sleep):
        handler = CustomObjectMaker(self.config, 'cache_db')

        # emulate RequestFailed
        mocked_client.side_effect = (RequestFailed(),)
        mocked_sleep.side_effect = (KeyboardInterrupt(),)

        with self.assertRaises(KeyboardInterrupt) as e:
            handler.create_api_client()
        self.assertEquals(
            mocked_logger.error.call_args_list,
            [
                call(
                    'Failed start api_client with status code {}'.format(None),
                    extra={'MESSAGE_ID': 'exceptions'}
                )
            ]
        )
        self.assertEquals(
            mocked_logger.info.call_args_list, [call('create_api_client will be sleep {} sec.'.format(0.2))]
        )

        # emulate Exception
        mocked_client.side_effect = (Exception(),)
        mocked_sleep.side_effect = (KeyboardInterrupt(),)

        with self.assertRaises(KeyboardInterrupt) as e:
            handler.create_api_client()
        self.assertEquals(
            mocked_logger.error.call_args_list[1:],
            [
                call(
                    'Failed start api client with error: {}'.format(''),
                    extra={'MESSAGE_ID': 'exceptions'}
                )
            ]
        )
        self.assertEquals(
            mocked_logger.info.call_args_list[1:], [call('create_api_client will be sleep {} sec.'.format(0.2))]
        )

    @patch('openprocurement.bridge.basic.handlers.APIClient')
    @patch('openprocurement.bridge.basic.handlers.logger')
    def test_get_resource_credentials(self, mocked_logger, mocked_client):
        handler = CustomObjectMaker(self.config, 'cache_db')

        resource_id = 'resource_id'
        result_data = {'owner': 'owner', 'tender_token': 'tender_token'}

        input_mock = MagicMock()
        input_mock.extract_credentials.return_value = result_data
        handler.input_client = input_mock

        result = handler.get_resource_credentials(resource_id)
        self.assertEquals(result_data, result)
        self.assertEquals(
            mocked_logger.info.call_args_list,
            [call('Getting credentials for tender {}'.format(resource_id),
                  extra={'MESSAGE_ID': 'databridge_get_credentials', 'JOURNAL_TENDER_ID': resource_id}),
             call('Got tender {} credentials'.format(resource_id),
                  extra={'MESSAGE_ID': 'databridge_got_credentials', 'JOURNAL_TENDER_ID': resource_id})]
        )

    @patch('openprocurement.bridge.basic.handlers.APIClient')
    def test__put_resource_in_cache(self, mocked_client):
        cache_db = AdaptiveCache({'0' * 32: datetime.now()})
        handler = CustomObjectMaker(self.config, cache_db)

        new_date = datetime.now()
        resource = {'id': '0' * 32, 'dateModified': new_date}

        handler._put_resource_in_cache(resource)

        self.assertEquals(cache_db.get(resource['id']), new_date)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCustomObjectMaker))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
