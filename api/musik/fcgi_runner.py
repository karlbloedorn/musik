#!/var/www/html/musik/api/bin/python
from flup.server.fcgi import WSGIServer
from musik.application import app
app.use_x_sendfile = True


if __name__ == '__main__':
    WSGIServer(app).run()
