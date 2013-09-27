""":mod:`libearth.crawler` --- Crawler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Crawl feeds.

"""
import multiprocessing.pool
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

from .parser.heuristic import get_document_type

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


    return parser(feed_crawled, feed)
def get_feed(feed_url):
    f = urllib2.urlopen(feed_url)
    feed_xml = f.read()
    parser = get_document_type(feed_xml)
