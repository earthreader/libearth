""":mod:`libearth.parser.rss2` --- RSS 2.0 parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parsing RSS 2.0 feed.

"""
from libearth.compat import PY3
from libearth.codecs import Rfc822
from .common import get_tag_attribute

if PY3:
    import urllib.request as urllib2
else:
    import urllib2

try:
    from lxml import etree
except ImportError:
    try:
        from xml.etree import cElementTree as etree
    except ImportError:
        from xml.etree import ElementTree as etree


def parse_rss(xml, parse_item=True):
    """Parse RSS 2.0 XML.

    :param xml: target rss 2.0 xml to parse
    :type xml: :class:`str`
    :param parse_item: whether to parse inner items as well.
                       it's useful to ignore items when retrieve
                       ``<source>``.  :const:`True` by default.
    :type parse_item: :class:`bool`
    :returns: feed data parsed from xml.

    """
    root = etree.fromstring(xml)
    channel = root.find('channel')
    items = channel.findall('item')
    feed_data, data_for_crawl = rss_get_channel_data(channel)
    if parse_item:
        feed_data['entry'] = rss_get_item_data(items)
    return feed_data, data_for_crawl


def rss_get_channel_data(root):
    feed_data = {}
    data_for_crawl = {}
    multiple = ['category', 'contributor', 'link']
    for tag in multiple:
        feed_data[tag] = []
    for data in root:
        if data.tag == 'title':
            feed_data['title'] = data.text
        elif data.tag == 'link':
            link = {}
            link['href'] = data.text
            link['rel'] = 'alternate'
            link['type'] = 'text/html'
            feed_data['link'].append(link)
        elif data.tag == 'description':
            subtitle = {}
            subtitle['type'] = 'text'
            subtitle['text'] = data.text
            feed_data['subtitle'] = subtitle
        elif data.tag == 'copyright':
            rights = {}
            rights['text'] = data.text
            feed_data['rights'] = rights
        elif data.tag == 'managingEditor':
            contributor = {}
            contributor['name'] = data.text
            contributor['email'] = data.text
            feed_data['contributor'].append(contributor)
        elif data.tag == 'webMaster':
            contributor = {}
            contributor['name'] = data.text
            contributor['email'] = data.text
            feed_data['contributor'].append(contributor)
        elif data.tag == 'pubDate':
            feed_data['updated'] = Rfc822().decode(data.text)
        elif data.tag == 'category':
            category = {}
            category['term'] = data.text
            feed_data['category'].append(category)
        elif data.tag == 'generator':
            feed_data['generator'] = {}
            feed_data['generator']['text'] = data.text
        elif data.tag == 'lastBuildDate':
            data_for_crawl['lastBuildDate'] = Rfc822().decode(data.text)

        elif data.tag == 'ttl':
            data_for_crawl['ttl'] = data.text
        elif data.tag == 'skipHours':
            data_for_crawl['skipHours'] = data.text
        elif data.tag == 'skipMinutes':
            data_for_crawl['skipMinutes'] = data.text
        elif data.tag == 'skipDays':
            data_for_crawl['skipDays'] = data.text
    return feed_data, data_for_crawl


def rss_get_item_data(entries):
    entries_data = []
    multiple = ['category', 'link']
    for entry in entries:
        entry_data = {}
        for tag in multiple:
            entry_data[tag] = []
        for data in entry:
            if data.tag == 'title':
                title = {}
                title['text'] = data.text
                title['type'] = 'text'
                entry_data['title'] = title
            elif data.tag == 'link':
                link = {}
                link['href'] = data.text
                link['rel'] = 'alternate'
                link['type'] = 'text/html'
                entry_data['link'].append(link)
            elif data.tag == 'description':
                content = {}
                content['type'] = 'text'
                content['text'] = data.text
                entry_data['content'] = content
            elif data.tag == 'author':
                author = {}
                author['name'] = data.text
                author['email'] = data.text
                entry_data['author'] = author
            elif data.tag == 'category':
                category = {}
                category['term'] = data.text
                entry_data['category'].append(category)
            elif data.tag == 'comments':
                entry_data['comments'] = data.text
            elif data.tag == 'enclosure':
                link = {}
                link['type'] = get_tag_attribute(data, 'type')
                link['href'] = get_tag_attribute(data, 'url')
                entry_data['link'].append(link)
            elif data.tag == 'guid':
                id = {}
                id['uri'] = data.text
                entry_data['id'] = id
            elif data.tag == 'pubDate':
                entry_data['published'] = Rfc822().decode(data.text)
            elif data.tag == 'source':
                from .heuristic import get_document_type, get_parser
                source = {}
                url = get_tag_attribute(data, 'url')
                request = urllib2.Request(url)
                f = urllib2.urlopen(request)
                xml = f.read()
                document_type = get_document_type(xml)
                parser = get_parser(document_type)
                source, _ = parser(xml, False)
                entry_data['source'] = source
        entries_data.append(entry_data)
    return entries_data
