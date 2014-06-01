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
from .util import normalize_xml_encoding


__all__ = ('ATOM_TYPE', 'RSS_TYPE', 'TYPE_TABLE', 'AutoDiscovery', 'FeedLink',
           'FeedUrlNotFoundError', 'autodiscovery', 'get_format')


#: (:class:`str`) The MIME type of RSS 2.0 format
#: (:mimetype:`application/rss+xml`).
RSS_TYPE = 'application/rss+xml'

#: (:class:`str`) The MIME type of Atom format
#: (:mimetype:`application/atom+xml`).
ATOM_TYPE = 'application/atom+xml'

#: (:class:`collections.Set`) The set of supported feed MIME types.
#:
#: .. versionadded:: 0.3.0
FEED_TYPES = frozenset([RSS_TYPE, ATOM_TYPE])

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
        feed_links, _ = parser.find(document)
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
    """Parse the given HTML and try finding the actual feed urls from it.

    .. versionchanged:: 0.3.0
       It became to find icon links as well, and :meth:`find_feed_url()`
       method (that returned only feed links) was gone, instead :meth:`find()`
       (that return a pair of feed links and icon links) was introduced.

    """

    LINK_PATTERN = re.compile(r'''rel\s?=\s?(?:'|")?([^'">]+)''')
    LINK_HREF_PATTERN = re.compile(r'''href\s?=\s?(?:'|")?([^'"\s>]+)''')
    LINK_TYPE_PATTERN = re.compile(r'''type\s?=\s?(?:'|")?([^'"\s>]+)''')

    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.feed_links = []
        self.icon_links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if not (tag == 'link' and 'rel' in attrs and 'href' in attrs):
            return
        if attrs['rel'] == 'alternate' and 'type' in attrs and \
           attrs['type'] in FEED_TYPES:
            self.feed_links.append(FeedLink(attrs['type'], attrs['href']))
        elif 'icon' in attrs['rel'].split():
            self.icon_links.append(attrs['href'])

    def find(self, document):
        document = text(document)
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
                self.find_link_with_regex(chunk)
        self.feed_links = sorted(self.feed_links, key=lambda link: link.type)
        return self.feed_links, self.icon_links

    def find_link_with_regex(self, chunk):
        match = self.LINK_PATTERN.search(chunk)
        if not match:
            return
        href_match = self.LINK_HREF_PATTERN.search(chunk)
        if not href_match:
            return
        rels = match.group(1).split()
        href = href_match.group(1)
        if 'alternate' in rels:
            type_match = self.LINK_TYPE_PATTERN.search(chunk)
            if type_match:
                type_ = type_match.group(1)
                if type_ in FEED_TYPES:
                    self.feed_links.append(FeedLink(type_, href))
        if 'icon' in rels:
            self.icon_links.append(href)


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
    document = normalize_xml_encoding(document)
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
