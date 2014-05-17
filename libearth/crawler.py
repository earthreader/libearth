""":mod:`libearth.crawler` --- Crawler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Crawl feeds.

"""
import collections
import logging


try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

from .compat.parallel import parallel_map
from .feed import Link
from .parser.autodiscovery import get_format


__all__ = 'CrawlError', 'CrawlResult', 'crawl', 'get_feed'


def crawl(feeds, pool_size):
    """Crawl feeds in feed list using thread.

    :param feeds: feeds
    :type feeds: :class: `collections.Sequence`
    :returns: a set of :class:`CrawlResult` objects
    :rtype: :class:`collections.Iterable`

    .. versionchanged:: 0.3.0

       It became to return a set of :class:`CrawlResult`\ s instead of
       :class:`tuple`\ s.

    """
    return parallel_map(pool_size, get_feed, feeds)


def get_feed(feed_url):
    # TODO: should be documented
    try:
        f = urllib2.urlopen(feed_url)
        feed_xml = f.read()
        f.close()
        parser = get_format(feed_xml)
        feed, crawler_hints = parser(feed_xml, feed_url)
        self_uri = None
        for link in feed.links:
            if link.relation == 'self':
                self_uri = link.uri
        if not self_uri:
            feed.links.append(Link(relation='self', uri=feed_url,
                                   mimetype=f.info()['content-type']))
        feed.entries = sorted(feed.entries, key=lambda entry: entry.updated_at,
                              reverse=True)
        favicon = feed.links.favicon
        if favicon is None:
            # FIXME: try 1) finding link[rel=icon] in the permalink html
            #            2) requesting HEAD /favicon.ico
            pass
        else:
            favicon = favicon.uri
        return CrawlResult(feed_url, feed, crawler_hints, favicon)
    except Exception as e:
        logging.getLogger(__name__ + '.get_feed').exception(e)
        raise CrawlError('{0} failed: {1}'.format(feed_url, e))


class CrawlResult(collections.Sequence):
    """The result of each crawl of a feed.

    It mimics triple of (:attr:`url`, :attr:`feed`, :attr:`hints`) for
    backward compatibility to below 0.3.0, so you can still take these
    values using tuple unpacking, though it's not recommended way to
    get these values anymore.

    .. versionadded:: 0.3.0

    """

    #: (:class:`str`) The crawled :attr:`feed` url.
    url = None

    #: (:class:`~libearth.feed.Feed`) The crawled feed.
    feed = None

    #: (:class:`collections.Mapping`) The extra hints for the crawler
    #: e.g. ``skipHours``, ``skipMinutes``, ``skipDays``.
    #: It might be :const:`None`.
    hints = None

    #: (:clas:`str`) The favicon url of the :attr:`feed` if exists.
    #: It might be :const:`None`.
    icon_url = None

    def __init__(self, url, feed, hints, icon_url=None):
        self.url = url
        self.feed = feed
        self.hints = hints
        self.icon_url = icon_url

    def __len__(self):
        return 3

    def __getitem__(self, index):
        if index == 0 or index == -3:
            return self.url
        elif index == 1 or index == -2:
            return self.feed
        elif index == 2 or index == -1:
            return self.hints
        raise IndexError('index out of range')


class CrawlError(IOError):
    """Error which rises when crawling given url failed."""
