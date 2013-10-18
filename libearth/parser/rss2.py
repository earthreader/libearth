""":mod:`libearth.parser.rss2` --- RSS 2.0 parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parsing RSS 2.0 feed.

"""
try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

try:
    from lxml import etree
except ImportError:
    try:
        from xml.etree import cElementTree as etree
    except ImportError:
        from xml.etree import ElementTree as etree

from ..codecs import Rfc822
from ..feed import (Category, Content, Entry, Feed, Generator, Link,
                    Person, Text)
from ..tz import now


def parse_rss(xml, feed_url=None, parse_entry=True):
    """Parse RSS 2.0 XML and translate it into Atom.

    To make the feed data valid in Atom format, ``id`` and ``link[rel=self]``
    fields would become the url of the feed.

    If ``pubDate`` is not present, ``updated`` field will be from
    the latest entry's ``updated`` time, or the time it's crawled instead.

    :param xml: rss 2.0 xml string to parse
    :type xml: :class:`str`
    :param parse_item: whether to parse items (entries) as well.
                       it's useful when to ignore items when retrieve
                       ``<source>``.  :const:`True` by default
    :type parse_item: :class:`bool`
    :returns: a pair of (:class:`~libearth.feed.Feed`, crawler hint)
    :rtype: :class:`tuple`

    """
    root = etree.fromstring(xml)
    channel = root.find('channel')
    items = channel.findall('item')
    feed_data, crawler_hints = rss_get_channel_data(channel, feed_url)
    if parse_entry:
        feed_data.entries = rss_get_item_data(items)
    check_valid_as_atom(feed_data)
    return feed_data, crawler_hints


def check_valid_as_atom(feed_data):
    if feed_data.updated_at is None:
        if feed_data.entries:
            try:
                feed_data.updated_at = max(entry.updated_at
                                           for entry in feed_data.entries
                                           if entry.updated_at)
            except ValueError:
                feed_data.updated_at = now()
        else:
            feed_data.updated_at = now()


def rss_get_channel_data(root, feed_url):
    feed_data = Feed(id=feed_url)
    feed_data.links.append(Link(relation='self', uri=feed_url))
    crawler_hints = {}
    contributors = []
    for data in root:
        if data.tag == 'title':
            feed_data.title = Text()
            feed_data.title.value = data.text or ''
        elif data.tag == 'link':
            link = Link()
            link.uri = data.text
            link.relation = 'alternate'
            link.mimetype = 'text/html'
            feed_data.links.append(link)
        elif data.tag == 'description':
            subtitle = Text()
            subtitle.type = 'text'
            subtitle.value = data.text
            feed_data.subtitle = subtitle
        elif data.tag == 'copyright':
            rights = Text()
            rights.value = data.text
            feed_data.rights = rights
        elif data.tag == 'managingEditor':
            contributor = Person()
            contributor.name = data.text
            contributor.email = data.text
            contributors.append(contributor)
            feed_data.contributors = contributors
        elif data.tag == 'webMaster':
            contributor = Person()
            contributor.name = data.text
            contributor.email = data.text
            contributors.append(contributor)
            feed_data.contributors = contributors
        elif data.tag == 'pubDate':
            feed_data.updated_at = Rfc822().decode(data.text)
        elif data.tag == 'category':
            category = Category()
            category.term = data.text
            feed_data.categories = [category]
        elif data.tag == 'generator':
            generator = Generator()
            generator.value = data.text
            feed_data.generator = generator
        elif data.tag == 'lastBuildDate':
            crawler_hints['lastBuildDate'] = Rfc822().decode(data.text)
        elif data.tag == 'ttl':
            crawler_hints['ttl'] = data.text
        elif data.tag == 'skipHours':
            crawler_hints['skipHours'] = data.text
        elif data.tag == 'skipMinutes':
            crawler_hints['skipMinutes'] = data.text
        elif data.tag == 'skipDays':
            crawler_hints['skipDays'] = data.text
    return feed_data, crawler_hints


def rss_get_item_data(entries):
    entries_data = []
    for entry in entries:
        entry_data = Entry()
        links = []
        for data in entry:
            if data.tag == 'title':
                title = Text()
                title.value = data.text
                entry_data.title = title
            elif data.tag == 'link':
                link = Link()
                link.uri = data.text
                link.relation = 'alternate'
                link.mimetype = 'text/html'
                links.append(link)
                entry_data.links = links
            elif data.tag == 'description':
                entry_data.content = Content(type='html', value=data.text)
            elif data.tag == 'author':
                author = Person()
                author.name = data.text
                author.email = data.text
                entry_data.authors = [author]
            elif data.tag == 'category':
                category = Category()
                category.term = data.text
                entry_data.categories = [category]
            elif data.tag == 'comments':
                #entry_data['comments'] = data.text
                pass  # FIXME
            elif data.tag == 'enclosure':
                link = Link()
                link.mimetype = data.get('type')
                link.uri = data.get('url')
                links.append(link)
                entry_data.links = links
            elif data.tag == 'guid':
                entry_data.id = data.text
            elif data.tag == 'pubDate':
                entry_data.published_at = Rfc822().decode(data.text)
                # TODO 'pubDate' is optional in RSS 2, but 'updated' in Atom
                #       is required element, so we have to fill some value to
                #       entry.updated_at.
            elif data.tag == 'source':
                from .heuristic import get_format
                url = data.get('url')
                request = urllib2.Request(url)
                f = urllib2.urlopen(request)
                xml = f.read()
                parser = get_format(xml)
                source, _ = parser(xml, url, parse_entry=False)
                entry_data.source = source
        if entry_data.updated_at is None:
            entry_data.updated_at = entry_data.published_at
        entries_data.append(entry_data)
    return entries_data
