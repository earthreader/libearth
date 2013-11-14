""":mod:`libearth.crawler` --- Crawler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Crawl feeds.

"""
import multiprocessing.pool
import sys
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

from .parser.heuristic import get_format

__all__ = 'crawl',


class crawl(object):
    """Crawl feeds in feed list using thread.

    .. note::

       It will not crawl feeds unless iterate the generator.

    :param feeds: feeds
    :type feeds: :class: `collections.Sequence`
    :returns: set of pairs (`~libearth.feed.Feed`, crawler hint)
    :rtype: :class:`collections.Iterable`

    """

    __slots__ = 'pool', 'async_results'

    def __init__(self, feeds, pool_size):
        self.pool = multiprocessing.pool.ThreadPool(pool_size)
        self.async_results = self.pool.imap_unordered(get_feed, feeds)

    def __iter__(self):
        for result in self.async_results:
            yield result
        self.pool.close()
        self.pool.join()


def get_feed(feed_url):
    try:
        f = urllib2.urlopen(feed_url)
        feed_xml = f.read()
        parser = get_format(feed_xml)
        return feed_url, parser(feed_xml, feed_url)
    except Exception:
        raise CrawlError(
            'Crawling, {0} failed: {1}'.format(feed_url, sys.exc_info()[0]))


class CrawlError(IOError):
    '''Error which rises when crawling given url failed.'''
