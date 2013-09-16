import socket
from  libearth.compat import PY3
if PY3:
    import urllib.parse as urlparse
else:
    import urlparse

class FeedSocket(object):

    just_received = 'not None'
    received = ''

    def __init__(self, feed_url):
        try:
            self.url = feed_url
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(1)
            url_parsed = urlparse.urlparse(feed_url)
            host = url_parsed.netloc
            path = url_parsed.path
            self.connect((host, 80))
            send_buffer = ('GET %s HTTP/1.1\r\n' % path +
                           'Host: %s\r\n\r\n' % host)
            sent_len = 0
            while(sent_len < len(send_buffer)):
                sent_len = self.sock.send(send_buffer)
        except:
            raise ConnectError('Connect to %s failed' % host)

    def __getattr__(self, name):
        return getattr(self.sock, name)

    def recv(self, length):
        self.just_received = self.sock.recv(length)
        self.received = self.received + self.just_received
        return self.just_received


class Crawler(object):

    readers = []

    def __init__(self):
        self.error_handler = self.default_error_handler

    def default_error_handler(self, e):
        print e.msg

    def add_error_handler(self, error_handler):
        self.error_handler = error_handler

    def add_reader(self, reader):
        self.readers.append(reader)

    def add_readers(self, readers):
        self.readers.extend(readers)

    def crawl(self, reader):
        while reader:
            reader = yield reader.recv(2048)


class ConnectError(Exception):
    """Exception raised when socket connect failed."""

    def __init__(self, msg):
        self.msg = msg

class RecvFinished(Exception):
    """Exception raised when socket has no data to receive"""

    def __init__(self, msg):
        self.msg = msg
