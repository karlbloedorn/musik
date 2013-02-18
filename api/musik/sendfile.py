from flask import Response, request
from re import findall
import os
from werkzeug.datastructures import Headers
import mimetypes
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime

def __http_date(dt = None, delta = None):
    if dt is None:
        dt = datetime.now()
        pass
    if delta is not None:
        dt = dt + delta
        pass
    stamp = mktime(dt.timetuple())
    return format_date_time(stamp)

def head_request(filename):
    status = 200
    size = os.stat(filename).st_size
    headers = Headers()
    mimetype = mimetypes.guess_type(filename)[0]
    headers.add('Content-Type', mimetype)
    headers.add('Accept-Ranges', 'bytes')
    headers.add('Content-Length', str(size))
    return Response(status=status, headers=headers)

def sendfile(filename, expire=None):
    headers = Headers()
    headers.add('Content-Disposition', 'attachment',filename=filename)
    headers.add('Content-Transfer-Encoding', 'binary')

    status = 200
    stat = os.stat(filename)
    size = stat.st_size
    begin = 0;
    end = size - 1;

    mimetype = mimetypes.guess_type(filename)[0]

    if request.headers.has_key("Range"):
        status = 206
        headers.add('Accept-Ranges','bytes')
        ranges=findall(r"\d+", request.headers["Range"])
        begin = int(ranges[0])
        if len(ranges)>1:
            end = int(ranges[1])
            headers.add('Content-Range','bytes %s-%s/%s' % 
                        (str(begin),str(end),str(size)))
            headers.add('Content-Length', str((end-begin)+1))
            with open(filename, 'rb') as fh:
                fh.seek(begin)
                data = fh.read((end-begin)+1)
                pass
            response = Response(data,  status=status, headers=headers, mimetype=mimetype, direct_passthrough=True)
            return response
        pass
    else:
        etag = '\"{0:d}\"'.format(int(os.stat('.').st_mtime))
        if request.headers.get('If-None-Match'):
            user_agent_etag = request.headers['If-None-Match']
            if user_agent_etag == etag:
                return Response('Not modified', status=304)
            pass
        fh = open(filename, 'rb')
        headers.add('Content-Length', str(size))
        headers.add('ETag', etag)
        headers.add('Expires', __http_date(delta=expire))
        response = Response(fh, status=status, headers=headers, mimetype=mimetype, direct_passthrough=True)
        return response
    pass
