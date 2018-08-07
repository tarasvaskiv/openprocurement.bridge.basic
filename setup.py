from setuptools import setup, find_packages
import os

version = '0.1.1'

here = os.path.abspath(os.path.dirname(__file__))

requires = [
    'cornice',
    'gevent',
    'pyramid_exclog',
    'setuptools',
    'pycrypto',
    'openprocurement_client',
    'munch',
    'tzlocal',
    'pyyaml',
    'iso8601',
    'couchdb',
    'elasticsearch',
    'redis'
]
test_requires = requires + [
    'requests',
    'webtest',
    'python-coveralls',
    'nose',
    'mock'
]

entry_points = {
    'console_scripts': [
        'databridge = openprocurement.bridge.basic.databridge:main'
    ],
    'openprocurement.bridge.basic.storage_plugins': [
        'couchdb = openprocurement.bridge.basic.storages.couchdb_plugin:includeme',
        'elasticsearch = openprocurement.bridge.basic.storages.elasticsearch_plugin:includeme',
        'redis = openprocurement.bridge.basic.storages.redis_plugin:includeme'
    ],
    'openprocurement.bridge.basic.filter_plugins': [
        'basic_couchdb = openprocurement.bridge.basic.filters:BasicCouchDBFilter',
        'basic_elasticsearch = openprocurement.bridge.basic.filters:BasicElasticSearchFilter'
    ],
    'openprocurement.bridge.basic.worker_plugins': [
        'basic_couchdb = openprocurement.bridge.basic.workers:BasicResourceItemWorker'
    ],
    'openprocurement.tests': [
        'bridge.basic = openprocurement.bridge.basic.tests.main:suite'
    ]
}


setup(name='openprocurement.bridge.basic',
      version=version,
      description="openprocurement.bridge.basic",
      long_description=open("README.md").read() + "\n",
      classifiers=[
          "Framework :: Pylons",
          "License :: OSI Approved :: Apache Software License",
          "Programming Language :: Python",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application"
      ],
      keywords='web services',
      author='Quintagroup, Ltd.',
      author_email='info@quintagroup.com',
      url="https://github.com/openprocurement/",
      license='Apache License 2.0',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['openprocurement'],
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=test_requires,
      extras_require={'test': test_requires},
      entry_points=entry_points,
      )
