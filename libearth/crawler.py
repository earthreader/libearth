""":mod:`libearth.crawler` --- Crawler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import os
import re
import urllib2
import urlparse

try:
    from lxml import etree
except ImportError:
    try:
        from xml.etree import cElementTree as etree
    except ImportError:
        from xml.etree import ElementTree as etree

from HTMLParser import HTMLParser


def crawl(url):
    request = urllib2.Request(url)
    f = urllib2.urlopen(request)
    document = f.read()
    return document


def auto_discovery(document, url=None):
    """If given url is rss feed url, it returns the url instantly.
    If given url is a url of web page, It find the site's RSS feed url
    and return it
    """
    document_type = get_document_type(document)
    if document_type == 'not feed':
        parser = AutoDiscovery()
        rss_url = parser.find_feed_url(document)
        if rss_url.startswith('/'):
            rss_url = urlparse.urljoin(url, rss_url)
        return rss_url
    else:
        return url


def get_document_type(document):
    try:
        root = etree.fromstring(document)
    except etree.ParseError:
        return 'not feed'
    if re.search('feed', root.tag):
        return 'atom'
    elif root.tag == 'rss':
        return 'rss2.0'
    elif re.search('RDF', root.tag):
        return 'rss1.0'
    else:
        raise UnidentifiedDocumentError()


RSS_TYPE = ('application/rss+xml', 'application/atom+xml')


class AutoDiscovery(HTMLParser):

    feed_url = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link' and 'type' in attrs and \
           attrs['type'] in RSS_TYPE:
            self.feed_url = attrs['href']

    def find_feed_url(self, document):
        chunks = re.findall(r'[^>]*(?:>|$)', document)
        for chunk in chunks:
            if self.feed_url is None:
                self.feed(chunk)
            else:
                return self.feed_url


class UnidentifiedDocumentError(Exception):
    def __init__():
        self.msg = 'cannot define the document\'s type'


class FeedUrlNotFoundError(Exception):
    def __init__(self):
        self.msg = 'cannot find feed url'
>>>>>>> Disassemble class into functions.
