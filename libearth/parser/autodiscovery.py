""":mod:`libearth.parser.autodiscovery` --- Autodiscovery
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides functions to autodiscovery feed url in document.

"""
import re
from libearth.compat import PY3, text
from libearth.parser.heuristic import get_format

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
    (i.e. :mimetype:`text/html`), it finds the urls of the corresponding feed.
    It sorts feed urls in lexicographical order of feed types and return urls.

    If autodiscovery failed, it raise :exc:`FeedUrlNotFoundError`.

    :param document: html, or xml strings
    :type document: :class:`str`
    :param url: the url used to retrieve the ``document``.
                if feed url is in html and represented in relative url,
                it will be rebuilt on top of the ``url``
    :type url: :class:`str`
    :returns: list of (feed_type, feed url)
    :rtype: :class:`collections.MutableSequence`

    """
    document = text(document)
    document_type = get_format(document)
    if document_type is None:
        parser = AutoDiscovery()
        feed_urls = parser.find_feed_url(document)
        if not feed_urls:
            raise FeedUrlNotFoundError('Cannot find feed url')
        for rss_url in feed_urls:
            if rss_url[1].startswith('/'):
                rss_url[1] = urlparse.urljoin(url, rss_url)
        return feed_urls
    else:
        return url


class AutoDiscovery(HTMLParser):
    """Parse the given HTML and try finding the actual feed urls from it."""

    def __init__(self):
        self.feed_urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link' and 'rel' in attrs and attrs['rel'] == 'alternate' \
                and 'type' in attrs and attrs['type'] in RSS_TYPE+ATOM_TYPE:
            self.feed_urls.append((attrs['type'], attrs['href']))

    def find_feed_url(self, document):
        match = re.match('.+</head>', document)
        if match:
            head = match.group(0)
        else:
            head = document
        chunks = re.findall('[^>]*(?:>|$)', head)
        for chunk in chunks:
            try:
                self.feed(chunk)
            except:
                self.find_feed_url_with_regex(chunk)
        self.feed_urls = sorted(self.feed_urls, key=lambda feed: feed[0])
        return self.feed_urls

    def find_feed_url_with_regex(self, chunk):
        if (re.search('rel\s?=\s?(\'|")?alternate[\'"\s>]', chunk) and
                (RSS_TYPE in chunk) or (ATOM_TYPE in chunk)):
            feed_url = re.search('href\s?=\s?(?:\'|")?([^\'"\s>]+)',
                                 chunk).group(1)
            feed_type = re.search('type\s?=\s?(?:\'|\")?([^\'"\s>]+)',
                                  chunk).group(1)
            self.feed_urls.append((feed_type, feed_url))


class FeedUrlNotFoundError(Exception):
    """Exception raised when feed url cannot be found in html."""

    def __init__(self, msg):
        self.msg = msg
