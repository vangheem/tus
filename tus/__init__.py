import uuid
import os
import time
from StringIO import StringIO


class TusException(Exception):
    pass


class Zope2RequestAdapter(object):

    def __init__(self, req):
        self.req = req

    @property
    def url(self):
        return self.req.URL

    @property
    def method(self):
        return self.req.REQUEST_METHOD

    def get_header(self, name):
        return self.req.getHeader(name)

    def set_response_code(self, code, status=None):
        self.req.response.setStatus(code, status)
        if status:
            self.req.response.body = status
        else:
            # Zope2 requires some kind of body or it'll rewrite the status
            self.req.respond.body = 'foobar'

    def set_header(self, name, value):
        self.req.response.setHeader(name, value)

    @property
    def body(self):
        return self.req._file

    def set_request_body(self, value):
        if hasattr(value, 'read'):
            self.req._file = value
        else:
            self.req._file = StringIO(value)


class WebobAdapter(object):

    def __init__(self, req):
        self.req = req
        self._resp = None

    @property
    def resp(self):
        if self._resp is None:
            from webob import Response
            self._resp = Response()
        return self._resp

    @property
    def url(self):
        return self.req.url

    @property
    def method(self):
        return self.req.method

    def get_header(self, name):
        return self.req.headers.get(name)

    def set_response_code(self, code, status=None):
        self.resp.status_code = code
        if status:
            self.resp.status = '%i %s' % (code, status)

    def set_header(self, name, value):
        self.resp.headers[name] = value

    @property
    def body(self):
        return self.req.body

    def set_request_body(self, value):
        if not hasattr(value, 'read'):
            self.req.body = value
        else:
            self.req.body_file = value


class Tus(object):
    upload_finished = False

    def __init__(self, req, tmp_file_dir=None, send_file=False,
                 upload_valid_duration=60*60, **kwargs):
        # detect request types
        self.req = req
        self.tmp_file_dir = tmp_file_dir
        self.send_file = send_file
        self.upload_valid_duration = upload_valid_duration

    @property
    def valid(self):
        if self.req.method == 'POST':
            if self.req.get_header('Entity-Length') or \
                    self.req.get_header('Final-Length'):
                return True
        elif self.req.method == 'HEAD':
            return True
        elif self.req.method == 'PATCH':
            if self.req.get_header('Offset') and \
                    self.req.get_header('Content-Type') == \
                    'application/offset+octet-stream':
                return True
        return False

    def handle(self):
        if self.req.method == 'POST':
            self.post()
        elif self.req.method == 'HEAD':
            self.head()
        elif self.req.method == 'PATCH':
            self.patch()

    def post(self):
        length = self.req.get_header('Entity-Length') or \
            self.req.get_header('Final-Length')
        try:
            length = int(length)
        except:
            raise TusException("Invalid length")
        uid = self.create_file(length)
        self.req.set_response_code(201, 'Created')
        self.req.set_header('Location', self.req.url + '/' + uid)

    def get_uid(self):
        return self.req.url.split('/')[-1]

    def head(self):
        uid = self.get_uid()
        length = self.get_current_offset(uid)
        if length == -1:
            self.req.set_response_code(404, 'Not Found')
            return
        elif length == self.get_end_length(uid):
            # huh, already done
            self.finished(uid)
        self.req.set_header('Offset', str(length))
        self.req.set_response_code(200, 'OK')

    def finished(self, uid):
        self.upload_finished = True
        if self.send_file:
            self.req.set_request_body(open(self.get_filepath()))
        else:
            self.req.set_request_body(self.get_filepath())

    def patch(self):
        uid = self.get_uid()
        # length = int(self.getHeader('Content-Length'))
        offset = int(self.req.get_header('Offset'))
        fi = self.req.body
        if not fi:
            raise TusException("no content body")

        if self.write_data(uid, offset, fi):
            self.finished(uid)
        self.req.set_response_code(200, 'OK')

    def get_current_offset(self, uid):
        path = self.get_filepath(uid)
        if not os.path.exists(path):
            return -1
        return os.path.getsize(path)

    def get_filepath(self, uid=None):
        if uid is None:
            uid = self.get_uid()
        return os.path.join(self.tmp_file_dir, uid)

    def create_file(self, length):
        """
        require defined length for result
        """
        self.cleanup()
        uid = uuid.uuid4().hex
        path = self.get_filepath(uid)
        while os.path.exists(path):
            uid = uuid.uuid5().hex
            path = self.get_filepath(uid)
        # write out info file
        lengthpath = path + '.length'
        fi = open(lengthpath, 'w')
        fi.write(str(length))
        fi.close()
        return uid

    def get_end_length(self, uid=None):
        if uid is None:
            uid = self.get_uid()
        path = os.path.join(self.tmp_file_dir, uid)
        infopath = path + '.length'
        if not os.path.exists(infopath):
            # XXX handle
            raise TusException('no length file written')
        fi = open(infopath)
        end_length = int(fi.read())
        fi.close()
        return end_length

    def write_data(self, uid, offset, data):
        path = os.path.join(self.tmp_file_dir, uid)
        if offset and not os.path.exists(path):
            # XXX hmmm, assuming file exists, error?
            raise Exception()
        mode = 'wb'
        if os.path.exists(path):
            mode = 'ab+'
        fi = open(path, mode)
        fi.seek(offset)
        if hasattr(data, 'read'):
            if hasattr(data, 'seek'):
                # if no seek, let's just hope it's at the beginning of the file
                data.seek(0)
            # file object
            while True:
                chunk = data.read(2 << 16)
                if not chunk:
                    break
                fi.write(chunk)
        else:
            fi.write(data)
        length = fi.tell()
        fi.close()

        end_length = self.get_end_length(uid)

        # touch length file so it doesn't get "cleaned" up
        infopath = path + '.length'
        with file(infopath, 'a'):
            os.utime(infopath, None)

        return length >= end_length

    def cleanup_file(self, uid=None):
        if uid is None:
            uid = self.get_uid()
        filepath = os.path.join(self.tmp_file_dir, uid)
        if os.path.exists(filepath):
            os.remove(filepath)
        length_filepath = os.path.join(self.tmp_file_dir, uid + '.length')
        if os.path.exists(length_filepath):
            os.remove(length_filepath)

    def cleanup(self):
        """
        look through upload directory and remove old uploads
        """
        duration = self.upload_valid_duration * 60
        for filename in os.listdir(self.tmp_file_dir):
            filepath = os.path.join(self.tmp_file_dir, filename)
            if os.path.isdir(filepath):
                continue
            if (time.time() - os.stat(filepath).st_mtime) > duration:
                os.remove(filepath)


class Filter(object):

    def __init__(self, app, global_conf, **options):
        self.global_conf = global_conf
        self.options = options
        self.app = app
        from webob import Request
        self.request_klass = Request

    def __call__(self, environ, start_response):
        req = self.request_klass(environ)
        if req.path.startswith(self.options['upload_path']):
            adapter = WebobAdapter(req)
            tus = Tus(adapter, **self.options)
            tus.handle()
            if tus.upload_finished:
                res = self.app(environ, start_response)
                tus.cleanup_file()
                return res
            else:
                return adapter.resp(environ, start_response)
        else:
            return self.app(environ, start_response)
