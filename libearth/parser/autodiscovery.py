""":mod:`libearth.parser.autodiscovery` --- Autodiscovery
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides functions to autodiscovery feed url in document.

"""
try:
    import HTMLParser
except ImportError:
    import html.parser as HTMLParser
import collections
import logging
import re
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from ..compat import text
from ..compat.etree import fromstring
from .atom import parse_atom
from .rss2 import parse_rss


__all__ = ('ATOM_TYPE', 'RSS_TYPE', 'TYPE_TABLE', 'AutoDiscovery', 'FeedLink',
           'FeedUrlNotFoundError', 'autodiscovery', 'get_format')


#: (:class:`str`) The MIME type of RSS 2.0 format.
RSS_TYPE = 'application/rss+xml'

#: (:class:`str`) The MIME type of Atom format.
ATOM_TYPE = 'application/atom+xml'

#: (:class:`collections.Mapping`) The mapping table of feed types
TYPE_TABLE = {parse_atom: ATOM_TYPE, parse_rss: RSS_TYPE}

#: Namedtuple which is a pair of ``type` and ``url``
FeedLink = collections.namedtuple('FeedLink', 'type url')


def autodiscovery(document, url):
    """If the given url refers an actual feed, it returns the given url
    without any change.

    If the given url is a url of an ordinary web page
    (i.e. :mimetype:`text/html`), it finds the urls of the corresponding feed.
    It returns feed urls in feed types' lexicographical order.

    If autodiscovery failed, it raise :exc:`FeedUrlNotFoundError`.

    :param document: html, or xml strings
    :type document: :class:`str`
    :param url: the url used to retrieve the ``document``.
                if feed url is in html and represented in relative url,
                it will be rebuilt on top of the ``url``
    :type url: :class:`str`
    :returns: list of :class:`FeedLink` objects
    :rtype: :class:`collections.MutableSequence`

    """
    document = text(document)
    document_type = get_format(document)
    if document_type is None:
        parser = AutoDiscovery()
        feed_links = parser.find_feed_url(document)
        if not feed_links:
            raise FeedUrlNotFoundError('Cannot find feed url')
        for link in feed_links:
            if link.url.startswith('/'):
                absolute_url = urlparse.urljoin(url, link.url)
                feed_links[feed_links.index(link)] = \
                    FeedLink(link.type, absolute_url)
        return feed_links
    else:
            return [FeedLink(TYPE_TABLE[document_type], url)]


class AutoDiscovery(HTMLParser.HTMLParser):
    """Parse the given HTML and try finding the actual feed urls from it."""

    FEED_PATTERN = r'''rel\s?=\s?('|")?alternate['"\s>]'''
    FEED_URL_PATTERN = r'''href\s?=\s?(?:'|")?([^'"\s>]+)'''
    FEED_TYPE_PATTERN = r'''type\s?=\s?(?:'|")?([^'"\s>]+)'''

    def __init__(self):
        self.feed_links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link' and 'rel' in attrs and attrs['rel'] == 'alternate' \
                and 'type' in attrs and attrs['type'] in RSS_TYPE+ATOM_TYPE:
            self.feed_links.append(FeedLink(attrs['type'], attrs['href']))

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
            except Exception:
                self.find_feed_url_with_regex(chunk)
        self.feed_links = sorted(self.feed_links, key=lambda link: link.type)
        return self.feed_links

    def find_feed_url_with_regex(self, chunk):
        if (re.search(self.FEED_PATTERN, chunk) and
           ((RSS_TYPE in chunk) or (ATOM_TYPE in chunk))):
            feed_url = re.search(self.FEED_URL_PATTERN, chunk).group(1)
            feed_type = re.search(self.FEED_TYPE_PATTERN, chunk).group(1)
            self.feed_links.append(FeedLink(feed_type, feed_url))


class FeedUrlNotFoundError(Exception):
    """Exception raised when feed url cannot be found in html."""

    def __init__(self, msg):
        self.msg = msg


def get_format(document):
    """Guess the syndication format of an arbitrary ``document``.

    :param document: document string to guess
    :type document: :class:`str`, :class:`bytes`
    :returns: the function possible to parse the given ``document``
    :rtype: :class:`collections.Callable`

    .. versionchanged:: 0.2.0
       The function was in :mod:`libearth.parser.heuristic` module (which is
       removed now) before 0.2.0, but now it's moved to
       :mod:`libearth.parser.autodiscovery`.

    """
    try:
        root = fromstring(document)
    except Exception as e:
        logger = logging.getLogger(__name__ + '.get_format')
        logger.warning(e, exc_info=True)
        return None
    if root.tag == '{http://www.w3.org/2005/Atom}feed':
        return parse_atom
    elif root.tag == 'rss':
        return parse_rss
    else:
        return None
