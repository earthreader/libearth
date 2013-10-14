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


def crawl(feeds, pool_size):
    """Crawl feeds in feed list using thread.

    .. note::

       It will not crawl feeds unless iterate the generator.

    :param feeds: feeds
    :type feeds: :class: `collections.Sequence`
    :returns: set of pairs (`~libearth.feed.Feed`, crawler hint)
    :rtype: :class:`collections.Iterable`

    """
    pool = multiprocessing.pool.ThreadPool(pool_size)
    for result in pool.imap_unordered(get_feed, feeds):
        yield result
    pool.close()


def get_feed(feed_url):
    try:
        f = urllib2.urlopen(feed_url)
        feed_xml = f.read()
        parser = get_format(feed_xml)
        return feed_url, parser(feed_xml, feed_url)
    except:
        raise CrawlError(
            'Crawling, {0} failed: {1}'.format(feed_url, sys.exc_info()[0]))


class CrawlError(IOError):
    '''Error which rises when crawling given url failed.'''
