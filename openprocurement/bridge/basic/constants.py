# -*- coding: utf-8 -*-
DEFAULTS = {
    'worker_config': {
        'worker_type': 'basic_couchdb',
        'client_inc_step_timeout': 0.1,
        'client_dec_step_timeout': 0.02,
        'drop_threshold_client_cookies': 2,
        'worker_sleep': 5,
        'retry_default_timeout': 3,
        'retries_count': 10,
        'queue_timeout': 3,
        'bulk_save_limit': 100,
        'bulk_save_interval': 3
    },
    'storage_config': {
        # required for databridge
        "storage_type": "couchdb",  # possible values ['couchdb', 'elasticsearch']
        # arguments for storage configuration
        "host": "localhost",
        "port": 5984,
        "user": "",
        "password": "",
        "db_name": "basic_bridge_db",
        "bulk_query_interval": 3,
        "bulk_query_limit": 100,
    },
    'filter_type': 'basic_couchdb',
    'retrievers_params': {
        'down_requests_sleep': 5,
        'up_requests_sleep': 1,
        'up_wait_sleep': 30,
        'queue_size': 1001
    },
    'extra_params': {
        "mode": "_all_",
        "limit": 1000
    },
    'resources_api_server': 'http://localhost:1234',
    'resources_api_version': "0",
    'public_resources_api_server': 'http://localhost:1234',
    'resource': 'tenders',
    'workers_inc_threshold': 75,
    'workers_dec_threshold': 35,
    'workers_min': 1,
    'workers_max': 3,
    'filter_workers_count': 1,
    'retry_workers_min': 1,
    'retry_workers_max': 2,
    'retry_resource_items_queue_size': -1,
    'watch_interval': 10,
    'user_agent': 'bridge.basic',
    'resource_items_queue_size': 10000,
    'input_queue_size': 10000,
    'resource_items_limit': 1000,
    'queues_controller_timeout': 60,
    'perfomance_window': 300
}
