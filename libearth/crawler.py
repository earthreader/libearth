""":mod:`libearth.crawler` --- Crawler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides functions to crawl documents in given URL,
and autodiscovery feed url in document.

.. todo::

   - function to check If-Modified-Since tag.

"""
import re

from .compat import PY3
from .parser.heuristic import get_document_type

if PY3:
    import urllib.parse as urlparse
    from html.parser import HTMLParser
else:
    import urlparse
    from HTMLParser import HTMLParser


def auto_discovery(document, url):
    """If given url is feed url, it returns the url instantly.
    Or if given url is a url of web page, It find the site's RSS feed url
    and return it.
    If autodiscovery failed, It raised :class:`FeedUrlNotFoundError`.

    :param document: HTML, or XML strings.
    :type document: :class:`str`
    :param url: URL of the ``document``. If feed url is in HTML and represented
                in relative URL, this function joined it with the ``url`` and
                return the result.
    :type url: :class:`str`
    :returns: feed url
    :rtype: :class:`str`

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
    """Error raised when no feed url is found in html.

    """
    def __init__(self, msg):
        self.msg = msg
