# -*- coding: utf-8 -*-
class Db(object):
    """ Database proxy """

    def __init__(self, config):
        self.config = config

        self._backend = None
        self._db_name = None
        self._port = None
        self._host = None

        if 'cache_host' in self.config['storage_config']:
            import redis
            self._backend = "redis"
            self._host = self.config['storage_config'].get('cache_host')
            self._port = self.config['storage_config'].get('cache_port') or 6379
            self._db_name = self.config['storage_config'].get('cache_db_name') or 0
            self.db = redis.StrictRedis(host=self._host, port=self._port, db=self._db_name)
            self.set_value = self.db.set
            self.has_value = self.db.exists
        else:
            from lazydb import Db
            self._backend = "lazydb"
            self._db_name = self.config['storage_config'].get('cache_db_name') or 'databridge_cache_db'
            self.db = Db(self._db_name)
            self.set_value = self.db.put
            self.has_value = self.db.has

    def get(self, key):
        return self.db.get(key)

    def put(self, key, value):
        self.set_value(key, value)

    def has(self, key):
        return self.has_value(key)


def includeme(config):
    return Db(config)
