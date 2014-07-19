""":mod:`libearth.parser.rss2` --- RSS 2.0 parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parsing RSS 1.0 feed.

"""
from ..compat.etree import fromstring
from ..feed import Entry, Feed
from .base import ParserBase, get_element_id
from .rss2 import parse_content, parse_link, parse_subtitle, parse_text
from .util import normalize_xml_encoding


RSS1_XMLNS = 'http://purl.org/rss/1.0/'


rss1_parser = ParserBase()


@rss1_parser.path('channel', [RSS1_XMLNS])
def parse_channel(element, session):
    return Feed(), session


parse_text = parse_channel.path('title', [RSS1_XMLNS])(parse_text)
parse_link = parse_channel.path('link', [RSS1_XMLNS], 'links')(parse_link)
parse_subtitle = parse_channel.path(
    'description', [RSS1_XMLNS], 'subtitle')(parse_subtitle)


@rss1_parser.path('item', [RSS1_XMLNS])
def parse_item(element, session):
    return Entry(), session


parse_text = parse_item.path('title', [RSS1_XMLNS])(parse_text)
parse_link = parse_item.path('link', [RSS1_XMLNS], 'links')(parse_link)
parse_content = parse_item.path(
    'description', [RSS1_XMLNS], 'content')(parse_content)


def parse_rss1(xml, feed_url=None, parse_entry=True):
    root = fromstring(normalize_xml_encoding(xml))
    channel = root.find(get_element_id(RSS1_XMLNS, 'channel'))
    feed_data = parse_channel(channel, None)
    if parse_entry:
        entries = root.findall(get_element_id(RSS1_XMLNS, 'item'))
        entry_list = []
        for entry in entries:
            entry_list.append(parse_item(entry, None))
        feed_data.entries = entry_list
    return feed_data, None
