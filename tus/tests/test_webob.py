# -*- coding: utf-8 -*-
import unittest2 as unittest
from tempfile import mkdtemp
from shutil import rmtree
import os
from webob import Request
from tus.tests import test_file


def test_app(environ, start_response):
    start_response('200 OK', [('Content-type', 'text/html')])
    return ['foobar']


class TusWebobTests(unittest.TestCase):

    def setUp(self):
        self.options = {
            'tmp_file_dir': mkdtemp()
        }

    def tearDown(self):
        rmtree(self.options['tmp_file_dir'])

    def test_tus_create(self):
        from tus import Tus, WebobAdapter
        req = Request.blank('/', method='POST')
        adapter = WebobAdapter(req)
        req.headers['ENTITY_LENGTH'] = '12345'
        tus = Tus(adapter, **self.options)
        assert tus.valid
        tus.handle()
        assert adapter.resp.status_code == 201

    def test_tus_upload(self):
        from tus import Tus, WebobAdapter
        req = Request.blank('/', method='POST')
        adapter = WebobAdapter(req)
        fi = open(test_file)
        req.headers['ENTITY_LENGTH'] = str(os.path.getsize(test_file))
        tus = Tus(adapter, **self.options)
        tus.handle()
        req = Request.blank('/' + adapter.resp.headers.get('Location'),
                            method='PATCH')
        req.body_file = fi
        req.headers['ENTITY_LENGTH'] = str(os.path.getsize(test_file))
        req.headers['CONTENT_LENGTH'] = req.headers['ENTITY_LENGTH']
        req.headers['OFFSET'] = '0'
        adapter = WebobAdapter(req)
        tus = Tus(adapter, **self.options)
        tus.handle()
        assert tus.upload_finished
        fipath = tus.get_filepath()
        fi.seek(0)
        otherfi = open(fipath)
        self.assertEquals(fi.read(), otherfi.read())
        fi.close()
        otherfi.close()

    def test_tus_multi_part_upload(self):
        from tus import Tus, WebobAdapter
        req = Request.blank('/', method='POST')
        adapter = WebobAdapter(req)
        fi = open(test_file)
        length = os.path.getsize(test_file)
        req.headers['ENTITY_LENGTH'] = str(length * 2)
        tus = Tus(adapter, **self.options)
        tus.handle()
        req = Request.blank('/' + adapter.resp.headers.get('Location'),
                            method='PATCH')
        req.body_file = fi
        req.headers['CONTENT_LENGTH'] = str(length)
        req.headers['OFFSET'] = '0'
        adapter = WebobAdapter(req)
        tus = Tus(adapter, **self.options)
        tus.handle()
        assert not tus.upload_finished
        # twice
        req.headers['OFFSET'] = str(length)
        tus.handle()
        assert tus.upload_finished
        fipath = tus.get_filepath()
        otherfi = open(fipath)
        fi.seek(0)
        self.assertEquals(len(fi.read()) * 2, len(otherfi.read()))
        fi.close()
        otherfi.close()
