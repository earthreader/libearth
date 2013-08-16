""":mod:`libearth.crawler` --- Crawler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import re

from .compat import PY3

if PY3:
    import urllib.request as urllib2
    import urllib.parse as urlparse
    from html.parser import HTMLParser
else:
    import urllib2
    import urlparse
    from HTMLParser import HTMLParser

try:
    from lxml import etree
except ImportError:
    try:
        from xml.etree import cElementTree as etree
    except ImportError:
        from xml.etree import ElementTree as etree


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
        if rss_url is None:
            raise FeedUrlNotFoundError('Cannot find feed url')
        if rss_url.startswith('/'):
            rss_url = urlparse.urljoin(url, rss_url)
        return rss_url
    else:
        return url


def get_document_type(document):
    try:
        root = etree.fromstring(document)
    except:
        return 'not feed'
    if re.search('feed', root.tag):
        return 'atom'
    elif root.tag == 'rss':
        return 'rss2.0'
    elif re.search('RDF', root.tag):
        return 'rss1.0'
    else:
        return 'not feed'


RSS_TYPE = 'application/rss+xml'
ATOM_TYPE = 'application/atom+xml'


class AutoDiscovery(HTMLParser):

    feed_url = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link' and 'rel' in attrs and attrs['rel'] == 'alternate' \
                and 'type' in attrs and attrs['type'] in RSS_TYPE+ATOM_TYPE:
            self.feed_url = attrs['href']

    def find_feed_url(self, document):
        chunks = re.findall(b'[^>]*(?:>|$)', document)
        for chunk in chunks:
            if self.feed_url is None:
                try:
                    self.feed(chunk)
                except:
                    self.find_feed_url_with_regex(document)
            else:
                return self.feed_url

    def find_feed_url_with_regex(self, document):
        document = str(document)
        head_pattern = re.compile('<head.+/head>', re.DOTALL)
        head = re.search(head_pattern, document).group(0)
        link_tags = re.findall('<link[^>]+>', head)
        for link_tag in link_tags:
            if (re.search('rel\s?=\s?(\'|")?alternate[\'"\s>]', link_tag) and
                    (RSS_TYPE in link_tag) or (ATOM_TYPE in link_tag)):
                feed_url = re.search('href\s?=\s?(\'|")?([^\'"\s>]+)',
                                     link_tag).group(2)
                self.feed_url = str(feed_url)
                return


class FeedUrlNotFoundError(Exception):
    def __init__(self, msg):
        self.msg = msg
