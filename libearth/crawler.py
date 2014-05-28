""":mod:`libearth.crawler` --- Crawler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Crawl feeds.

"""
import collections
import logging
import sys

try:
    import urllib.request as urllib2
except ImportError:
    import urllib2
try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

from .compat.parallel import parallel_map
from .feed import Link
from .parser.autodiscovery import AutoDiscovery, get_format
from .subscribe import SubscriptionSet
from .version import VERSION


__all__ = 'CrawlError', 'CrawlResult', 'crawl', 'get_feed'


def open_url(url):
    if isinstance(url, Request):
        request = url
    else:
        request = urllib2.Request(url)
    request.add_header('User-agent', '{0}/{1}'.format(__package__, VERSION))
    return urllib2.urlopen(request)


def crawl(feed_urls, pool_size):
    """Crawl feeds in feed list using thread.

    :param feed_urls: feed urls to crawl
    :type feed_urls: :class: `collections.Sequence`
    :param pool_size: the number of concurrent workers
    :type pool_size: :class:`numbers.Integral`
    :returns: a set of :class:`CrawlResult` objects
    :rtype: :class:`collections.Iterable`

    .. versionchanged:: 0.3.0

       It became to return a set of :class:`CrawlResult`\ s instead of
       :class:`tuple`\ s.

    .. versionchanged:: 0.3.0

       The parameter ``feeds`` was renamed to ``feed_urls``.

    """
    return parallel_map(pool_size, get_feed, feed_urls)


def get_feed(feed_url):
    # TODO: should be documented
    logger = logging.getLogger(__name__ + '.get_feed')
    try:
        f = open_url(feed_url)
        feed_xml = f.read()
        f.close()
        parser = get_format(feed_xml)
        if parser is None:
            logger.warn('failed to detect the format of %s', feed_url)
            logger.debug('the response body of %s:\n%s', feed_url, feed_xml)
            raise CrawlError('failed to detect the format of ' + feed_url)
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
            permalink = feed.links.permalink
            if permalink:
                try:
                    f = open_url(permalink.uri)
                except IOError:
                    pass
                else:
                    html = f.read()
                    f.close()
                    _, icon_urls = AutoDiscovery().find(html)
                    if icon_urls:
                        favicon = urlparse.urljoin(permalink.uri,
                                                   icon_urls[0])
                if favicon is None:
                    favicon = urlparse.urljoin(permalink.uri, '/favicon.ico')
                    req = Request(favicon, method='HEAD')
                    f = open_url(req)
                    if f.getcode() != 200:
                        favicon = None
                    f.close()
        else:
            favicon = favicon.uri
        return CrawlResult(feed_url, feed, crawler_hints, favicon)
    except Exception as e:
        logger.exception(
            '%s: %s', feed_url, e
        )
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

    #: (:class:`str`) The favicon url of the :attr:`feed` if exists.
    #: It might be :const:`None`.
    icon_url = None

    def __init__(self, url, feed, hints, icon_url=None):
        self.url = url
        self.feed = feed
        self.hints = hints
        self.icon_url = icon_url

    def add_as_subscription(self, subscription_set):
        """Add it as a subscription to the given ``subscription_set``.

        :param subscription_set: a subscription list or category to add
                                 a new subscription
        :type subscription_set: :class:`~libearth.subscribe.SubscriptionSet`
        :returns: the created subscription object
        :rtype: :class:`~libearth.subscribe.Subscription`

        """
        if not isinstance(subscription_set, SubscriptionSet):
            raise TypeError(
                'expected an instance of {0.__module__}.{0.__name__}, '
                'not {1!r}'.format(SubscriptionSet, subscription_set)
            )
        return subscription_set.subscribe(self.feed, icon_uri=self.icon_url)

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


if sys.version_info >= (3, 3):
    # Since Python 3.3 urllib.request.Request can take a method argument
    Request = urllib2.Request
else:
    class Request(urllib2.Request):
        """Request which can take a ``method`` argument."""

        def __init__(self, *args, **kwargs):
            method = kwargs.pop('method', None)
            urllib2.Request.__init__(self, *args, **kwargs)
            self._method = method

        def get_method(self):
            return self._method or urllib2.Request.get_method(self)
