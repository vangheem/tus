# -*- coding: utf-8 -*-
import unittest2 as unittest
from tempfile import mkdtemp
from shutil import rmtree
from tus.tests import test_file
import os


def test_app(environ, start_response):
    start_response('200 OK', [('Content-type', 'text/html')])
    return ['appfoobar:%s' % environ['wsgi.input'].read()]


class TusFilterTests(unittest.TestCase):

    def setUp(self):
        self.options = {
            'tmp_file_dir': mkdtemp(),
            'upload_path': '/'
        }

    def tearDown(self):
        rmtree(self.options['tmp_file_dir'])

    def get_app(self):
        from webtest import TestApp
        from tus import Filter
        return TestApp(Filter(test_app, {}, **self.options))

    def patch_request(self, app, url, body, length, extra_environ={},
                      headers={}):
        environ = app._make_environ(extra_environ)
        environ['REQUEST_METHOD'] = 'PATCH'
        url = str(url)
        url = app._remove_fragment(url)
        req = app.RequestClass.blank(url, environ)
        req.environ['wsgi.input'] = body
        req.content_length = length
        if headers:
            req.headers.update(headers)
        return app.do_request(req, None, False)

    def test_tus_create(self):
        app = self.get_app()
        resp = app.post('/', headers={
            'ENTITY_LENGTH': str(os.path.getsize(test_file))
        })
        assert resp.status_int == 201

    def test_tus_filter_upload(self):
        app = self.get_app()
        fi = open(test_file)
        length = os.path.getsize(test_file)
        resp = app.post('/', headers={
            'ENTITY_LENGTH': str(length)
        })
        resp = self.patch_request(
            app, resp.headers.get('Location'), fi, length, headers={
                'ENTITY_LENGTH': str(os.path.getsize(test_file)),
                'OFFSET': '0'
            })
        assert resp.status_int == 200
        assert 'appfoobar:' in resp.body
        assert '/tmp' in resp.body

    def test_tus_multi_part_upload(self):
        app = self.get_app()
        fi = open(test_file)
        length = os.path.getsize(test_file)
        resp = app.post('/', headers={
            'ENTITY_LENGTH': str(length * 2)
        })
        location = resp.headers.get('Location')
        resp = self.patch_request(
            app, location, fi, length, headers={
                'ENTITY_LENGTH': str(length),
                'OFFSET': '0'
            })
        assert resp.status_int == 200
        assert 'appfoobar:' not in resp.body
        fi.close()
        fi = open(test_file)
        resp = self.patch_request(
            app, location, fi, length, headers={
                'ENTITY_LENGTH': str(length),
                'OFFSET': str(length)
            })
        assert resp.status_int == 200
        assert 'appfoobar:' in resp.body
        assert '/tmp' in resp.body
