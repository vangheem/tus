tus python integration
======================

This package aims to be a robust implementation of the tus resumable upload
standard, `http://tus.io/`<tus.io>.

Integrations include an api to handle WebOb requests and Zope2 requests.
Additionally, you can run this server as a wsgi filter.


Options
-------

tmp_file_dir
    directory to store temporary files
send_file
    by default, it'll only send the filename in the request body,
    not an actual file upload
upload_valid_duration
    how long before you cleanup old uploads in minutes


Basics
------

1. POST to url, response 201 with location of temp file upload url.

2. PATCH to temp file upload url responded to in previous POST. These can be
   chunks of the entire file.

Resume
~~~~~~

- HEAD to issued temp file upload url to give current size of uploaded
