# -*- coding: utf-8 -*-
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import IntegrationTesting
import unittest2 as unittest
from tempfile import mkdtemp
from shutil import rmtree
import os
from tus.tests import test_file


class TusLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        pass

    def setUpPloneSite(self, portal):
        pass

    def tearDownPloneSite(self, portal):
        pass


TUS_FIXTURE = TusLayer()
TUS_INTEGRATION_TESTING = IntegrationTesting(
    bases=(TUS_FIXTURE,),
    name="Tus:Integration"
)


class TusIntegrationTests(unittest.TestCase):

    layer = TUS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        self.options = {
            'tmp_file_dir': mkdtemp()
        }

    def tearDown(self):
        rmtree(self.options['tmp_file_dir'])

    def test_tus_create(self):
        from tus import Tus, Zope2RequestAdapter
        req = self.request
        req.REQUEST_METHOD = 'POST'
        req.environ['ENTITY_LENGTH'] = '12345'
        tus = Tus(Zope2RequestAdapter(req), **self.options)
        assert tus.valid
        tus.handle()
        assert req.response.code == 201

    def test_tus_upload(self):
        from tus import Tus, Zope2RequestAdapter
        req = self.request
        fi = open(test_file)
        req.REQUEST_METHOD = 'POST'
        req.environ['ENTITY_LENGTH'] = str(os.path.getsize(test_file))
        tus = Tus(Zope2RequestAdapter(req), **self.options)
        tus.handle()
        req.REQUEST_METHOD = 'PATCH'
        req._file = fi
        req.URL = req.response.getHeader('Location')
        req.environ['CONTENT_LENGTH'] = req.environ['ENTITY_LENGTH']
        req.environ['OFFSET'] = '0'
        tus.handle()
        assert tus.upload_finished
        fipath = tus.get_filepath()
        fi.seek(0)
        otherfi = open(fipath)
        self.assertEquals(fi.read(), otherfi.read())
        fi.close()
        otherfi.close()

    def test_tus_multi_part_upload(self):
        from tus import Tus, Zope2RequestAdapter
        req = self.request
        fi = open(test_file)
        req.REQUEST_METHOD = 'POST'
        length = os.path.getsize(test_file)
        req.environ['ENTITY_LENGTH'] = str(length * 2)
        tus = Tus(Zope2RequestAdapter(req), **self.options)
        tus.handle()
        req.REQUEST_METHOD = 'PATCH'
        req._file = fi
        req.URL = req.response.getHeader('Location')
        req.environ['CONTENT_LENGTH'] = str(length)
        req.environ['OFFSET'] = '0'
        tus.handle()
        assert not tus.upload_finished
        # twice
        req.environ['OFFSET'] = str(length)
        tus.handle()
        assert tus.upload_finished

        fipath = tus.get_filepath()
        otherfi = open(fipath)
        fi.seek(0)
        self.assertEquals(len(fi.read()) * 2, len(otherfi.read()))
        fi.close()
        otherfi.close()
