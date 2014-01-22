tus python integration
======================

This package aims to be a robust implementation of the tus resumable upload
standard, `tus.io <http://tus.io>`_.

Integrations include an api to handle WebOb requests and Zope2 requests.
Additionally, you can run this server as a wsgi filter.

The package aims to be everything you need to integrate the TUS protocol
into your python web applications.


Options
-------

tmp_file_dir
    directory to store temporary files
send_file
    by default, it'll only send the filename in the request body,
    not an actual file upload
upload_valid_duration
    how long before you cleanup old uploads in seconds
upload_path
    only used for WSGI filter


Basics
------

1. POST to url, response 201 with location of temp file upload url. The
   upload url is a combination of the base url + the unique id of the in
   progress file upload. Example: /upload/432jjdsfjsd78387

2. PATCH to temp file upload url responded to in previous POST. These can be
   chunks of the entire file.

Resume
~~~~~~

- HEAD to issued temp file upload url to give current size of uploaded


Integration
===========


WebOb compatible applications
-----------------------------

A simple Webob request adapter is provided to work with the API. This code
assume it will be handling all upload related requests--meaning::

    from tus import Tus, WebobAdapter
    adapter = WebobAdapter(req)
    options = {
        'tmp_file_dir': '/tmp'
    }
    tus = Tus(adapter, **options)
    if tus.valid:
        tus.handle()
        if tus.upload_finished:
            fipath = tus.get_filepath()
            # do something here
            tus.cleanup_file()
        else:
            return adapter.resp


Zope2 or Plone
--------------

This example is taken out of
`plone.app.widgets <https://github.com/plone/plone.app.widgets/blob/master/plone/app/widgets/browser/file.py#L91>`_::


    adapter = Zope2RequestAdapter(req)
    tus = Tus(adapter, **tus_settings)
    if tus.valid:
        tus.handle()
        if not tus.upload_finished:
            return
        else:
            filename = req.getHeader('FILENAME')
            if tus.send_file:
                filedata = req._file
            else:
                filepath = req._file.read()
                filedata = open(filepath)
            tus.cleanup_file()


WSGI Filter
-----------

Example in python::

    from tus import Filter as TusFilter
    filtered = TusFilter(app, tmp_file_dir='/tmp', upload_path='/upload')


WSGI Paste Configuration Example
--------------------------------

Basic paste deploy config::

    [app:main]
    use = egg:MyEgg
    filter-with = tus

    [filter:tus]
    use = egg:tus#main
    upload_path = /upload
    tmp_file_dir = /tmp


or::


    [filter:tus]
    use = egg:tus#main
    upload_path = /upload
    tmp_file_dir = /tmp

    [app:main]
    pipeline =
        tus
        egg:MyEgg


