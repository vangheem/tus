import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
]

setup(name='tus',
      version='1.0a1',
      description='tus',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
          "Programming Language :: Python",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
      ],
      author='Nathan Van Gheem',
      author_email='nathan@vangheem.us',
      url='',
      keywords='web pyramid pylons',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      extras_require={
          'test': [
              'WebOb',
              'WebTest'
          ],
          'dev': [
              'pyramid'
          ]
      },
      tests_require=requires,
      test_suite="tus",
      entry_points="""\
      [paste.filter_factory]
      main = tus:Filter
      """,
      )
