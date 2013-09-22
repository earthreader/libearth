""":mod:`libearth.crawler` --- Crawler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Crawl feeds.

"""
import multiprocessing.pool
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

from .parser.heuristic import get_document_type, get_parser

__all__ = 'crawl',


def crawl(feeds, num_of_thread):
    """Crawl feeds in feed list using thread.

    .. note::

       It will not crawl feeds unless iterate the generator.

    :param feeds: feeds
    :type feeds: :class: `collections.Sequence`
    :returns: set of pairs (`~libearth.feed.Feed`, crawler hint)
    :rtype: :class:`collections.Iterable`

    """
    pool = multiprocessing.pool.ThreadPool(num_of_thread)
    for result in pool.imap_unordered(get_feed, feeds):
        yield result
    pool.close()


def get_feed(feed):
    f = urllib2.urlopen(feed)
    feed_crawled = f.read()
    parser = get_parser(get_document_type(feed_crawled))
    return parser(feed_crawled, feed)
