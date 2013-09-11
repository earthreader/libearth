import re
import select
import socket


class FeedSocket(object):

    URL_PATTERN = re.compile(r'''
    (?:http://)?
    (?P<host> [^/]+)
    (?P<path> .+)
    ''', re.VERBOSE)

    just_received = 'not None'
    received = ''

    def __init__(self, feed_url):
        try:
            self.url = feed_url
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            match = self.URL_PATTERN.match(feed_url)
            host = match.group('host')
            path = match.group('path')
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


class SelectCrawler(object):

    readers = []
    returns = []
    feedlist = []
    URL_PATTERN = re.compile(r'''
    (?:http://)?
    (?P<host> [^/]+)
    (?P<path> .+)
    ''', re.VERBOSE)

    def __init__(self):
        self.error_handler = self.default_error_handler

    def default_error_handler(self, e):
        print e.msg

    def add_error_handler(self, error_handler):
        self.error_handler = error_handler

    def add_feedlist(self, feedlist):
        self.feedlist.extend(feedlist)

    def crawl(self):
        for feed_url in self.feedlist:
            try:
                s = FeedSocket(feed_url)
            except ConnectError as e:
                self.error_handler(e)
            else:
                self.readers.append(s)
        while True:
            r_list, w, e = select.select(self.readers, [], [], 3)
            if not r_list:
                break
            else:
                for r in r_list:
                    if r.just_received:
                        r.recv(3000)
                    else:
                        self.readers.remove(r)
                        self.returns.append((r.url, r.received))
        for reader in self.readers:
            self.returns.append((reader.url, reader.received))
        return self.returns


class ConnectError(Exception):
    """Exception raised when socket connect failed."""

    def __init__(self, msg):
        self.msg = msg
