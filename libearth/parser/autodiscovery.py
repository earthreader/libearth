""":mod:`libearth.parser.autodiscovery` --- Autodiscovery
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides functions to autodiscovery feed url in document.

"""
import re
from libearth.compat import PY3
from libearth.parser.heuristic import get_document_type

if PY3:
    import urllib.parse as urlparse
    from html.parser import HTMLParser
else:
    import urlparse
    from HTMLParser import HTMLParser

__all__ = 'autodiscovery',


#: (:class:`str`) The MIME type of RSS 2.0 format.
RSS_TYPE = 'application/rss+xml'

#: (:class:`str`) The MIME type of Atom format.
ATOM_TYPE = 'application/atom+xml'


def autodiscovery(document, url):
    """If the given url refers an actual feed, it returns the given url
    without any change.

    If the given url is a url of an ordinary web page
    (i.e. :mimetype:`text/html`), it finds the url of the corresponding feed.
    If autodiscovery failed, it raise :exc:`FeedUrlNotFoundError`.

    :param document: html, or xml strings
    :type document: :class:`str`
    :param url: the url used to retrieve the ``document``.
                if feed url is in html and represented in relative url,
                it will be rebuilt on top of the ``url``
    :type url: :class:`str`
    :returns: feed url
    :rtype: :class:`str`

    """
    document_type = get_document_type(document)
    if document_type is None:
        parser = AutoDiscovery()
        rss_url = parser.find_feed_url(document)
        if rss_url is None:
            raise FeedUrlNotFoundError('Cannot find feed url')
        if rss_url.startswith('/'):
            rss_url = urlparse.urljoin(url, rss_url)
        return rss_url
    else:
        return url


class AutoDiscovery(HTMLParser):
    """Parse the given HTML and try finding the actual feed url from it."""

    feed_url = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link' and 'rel' in attrs and attrs['rel'] == 'alternate' \
                and 'type' in attrs and attrs['type'] in RSS_TYPE+ATOM_TYPE:
            self.feed_url = attrs['href']

    def find_feed_url(self, document):
        chunks = re.findall('[^>]*(?:>|$)', document)
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
    """Exception raised when feed url cannot be found in html."""

    def __init__(self, msg):
        self.msg = msg
