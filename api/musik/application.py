import logging
import hashlib
import os.path
from datetime import timedelta
from functools import update_wrapper

from flask import request, Flask, Response, make_response, current_app, json, send_file, render_template
import flask

from werkzeug import secure_filename

from musik.db import *
from musik.utils import logging_setup
import musik.sendfile
import musik.tagging
import musik.auth
from flaskext.auth import Auth, AuthUser, login_required, login

def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            h['Access-Control-Expose-Headers'] = headers
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator

def request_wants_json():
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']


app = Flask(__name__)
auth = Auth(app)
logger, syshan = logging_setup(__name__)
lib = Library()
syshan.setLevel(logging.DEBUG)
app.logger.addHandler(syshan)
app.secret_key = 'N4BUdSXUzHxNoO8g'

@app.route('/login', methods = ['POST', 'OPTIONS'])
@crossdomain(origin='*')
def logon():
    username = request.form['username']
    password = request.form['password']
    if musik.auth.check_auth(username, password):
        user = AuthUser(username)
        login(user)
        return '', 200
        pass
    else:
        return 'Not authorized', 401
    pass


@app.route('/songs', methods = ['POST', 'GET', 'OPTIONS'])
@login_required()
@crossdomain(origin='*')
def library_list_all():
    if request.method == 'GET':
        if request_wants_json():
            md5 = hashlib.md5()
            md5.update('s36XLKU7095hu7asN' + str(lib.version))
            etag = 'W/"{0}"'.format(md5.hexdigest())
            if request.headers.get('If-None-Match'):
                user_agent_etag = request.headers['If-None-Match']
                if user_agent_etag == etag:
                    return 'Lastest version', 304
                pass
            return json.dumps(lib, cls=JSONEncoder), 200, {'Content-Type': 'application/json', 'ETag': etag}
        pass
    else:
        metadata = request.form['metadata']
        decoded_metadata = json.loads(metadata)
        song_file = request.files['song_file']
        try:
            song, album, artist = lib.add(decoded_metadata['artist'], decoded_metadata['album'], decoded_metadata['song'])
        except SongExists_Exception as e:
            return 'Song existed', 409
            pass
        else:
            disk_path = lib.files.create(song.name, 
                             prefix='songs', 
                             filename=secure_filename(song_file.filename)
                             )
            song_file.save(disk_path)
            song['path'] = 'local'
            if 'art' in artist and 'art' in album:
                pass
            else:
                art, tag = musik.tagging.tag(disk_path)
                if art is not None:
                    art_data, art_ext = art
                    art_path = lib.files.create(album.name + ':art',
                                                prefix='art',
                                                filename=album.key + art_ext
                                                )
                    album['art'] = 'local'
                    with open(art_path, 'w+b') as fh:
                        fh.write(art_data)
                        pass
                    pass
                pass
            pass
        return json.dumps(song, cls=JSONEncoder), 201, {'Content-Type': 'application/json', 'Location': '/song/{0}'.format(song.key)}
        pass
    pass


@app.route('/song/<key>', methods = ['GET', 'HEAD', 'OPTIONS'])
@crossdomain(origin='*', headers = [ 'Content-Length', 'Range'])
@login_required()
def song_data(key):
    if request.method == 'HEAD':
        song = lib.songs[key]
        return musik.sendfile.head_request(song.file)
    requested_mimetype = request.accept_mimetypes.best_match(['application/json', 'text/html', 'application/octet-stream'])
    if requested_mimetype  == 'text/html' and False:
        return "HTML For song"
    elif requested_mimetype  == 'application/json' and False:
        return "JSON For song"
    elif requested_mimetype  == 'application/octet-stream' or True:
        song = lib.songs[key]
        if song.file and os.path.exists(song.file):
            return musik.sendfile.sendfile(song.file)
        else:
            return "File missing", 500, {'Content-Type': 'text/plain'}
    else:
        return "Format mismatch", 406


@app.route('/album/<key>/art')
@login_required()
def album_art(key):
    album = lib.albums[key]
    if album.art and os.path.exists(album.art):
        return musik.sendfile.sendfile(album.art)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7681,  debug=False)
