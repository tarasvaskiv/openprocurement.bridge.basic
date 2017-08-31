from setuptools import setup, find_packages
import os

version = '0.1'

here = os.path.abspath(os.path.dirname(__file__))

requires = [
    'cornice',
    'gevent',
    'pyramid_exclog',
    'setuptools',
    'couchdb',
    'couchapp',
    'pycrypto',
    'openprocurement_client',
    'munch',
    'tzlocal',
    'pyyaml',
    'psutil',
    'iso8601'
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
        'databridge = openprocurement.edge.databridge.databridge:main'
    ]
}


setup(name='openprocurement.edge.databridge',
      version=version,
      description="openprocurement.edge.databridge",
      long_description=open("README.txt").read() + "\n",
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
