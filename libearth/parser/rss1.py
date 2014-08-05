""":mod:`libearth.parser.rss1` --- RSS 1.0 parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parsing RSS 1.0 feed.

"""
from ..compat.etree import fromstring
from ..feed import Entry, Feed
from .base import ParserBase, get_element_id
from .rss2 import parse_category, parse_content, parse_link, parse_person, parse_subtitle, parse_text, parse_datetime
from .util import normalize_xml_encoding


RSS1_XMLNS = 'http://purl.org/rss/1.0/'
DC_NAMESPACE = 'http://purl.org/dc/elements/1.1/'


rss1_parser = ParserBase()


@rss1_parser.path('channel', [RSS1_XMLNS])
def parse_channel(element, session):
    return Feed(), session


parse_text = parse_channel.path('title', [RSS1_XMLNS, DC_NAMESPACE])(parse_text)
parse_text = parse_channel.path('rights', [DC_NAMESPACE])(parse_text)
parse_link = parse_channel.path('link', [RSS1_XMLNS], 'links')(parse_link)
parse_subtitle = parse_channel.path(
    'description', [RSS1_XMLNS, DC_NAMESPACE], 'subtitle')(parse_subtitle)
parse_person = parse_channel.path(
    'creator', [DC_NAMESPACE], 'authors')(parse_person)
parse_person = parse_channel.path(
    'publisher', [DC_NAMESPACE], 'contributors')(parse_person)
parse_person = parse_channel.path(
    'contributor', [DC_NAMESPACE], 'contributors')(parse_person)
parse_datetime = parse_channel.path(
    'date', [DC_NAMESPACE], 'updated_at')(parse_datetime)
parse_category = parse_channel.path(
    'type', [DC_NAMESPACE], 'categories')(parse_category)
parse_category = parse_channel.path(
    'subject', [DC_NAMESPACE], 'categories')(parse_category)



@rss1_parser.path('item', [RSS1_XMLNS])
def parse_item(element, session):
    return Entry(), session


parse_text = parse_item.path('title', [RSS1_XMLNS, DC_NAMESPACE])(parse_text)
parse_text = parse_item.path('rights', [DC_NAMESPACE])(parse_text)
parse_link = parse_item.path('link', [RSS1_XMLNS], 'links')(parse_link)
parse_content = parse_item.path(
    'description', [RSS1_XMLNS, DC_NAMESPACE], 'content')(parse_content)
parse_person = parse_item.path(
    'creator', [DC_NAMESPACE], 'authors')(parse_person)
parse_person = parse_item.path(
    'contributor', [DC_NAMESPACE], 'contributors')(parse_person)
parse_datetime = parse_item.path(
    'date', [DC_NAMESPACE], 'updated_at')(parse_datetime)
parse_category = parse_item.path(
    'type', [DC_NAMESPACE], 'categories')(parse_category)
parse_category = parse_item.path(
    'subject', [DC_NAMESPACE], 'categories')(parse_category)


@parse_channel.path('identifier', [DC_NAMESPACE], 'id')
@parse_item.path('identifier', [DC_NAMESPACE])
def parse_id(element, session):
    return element.text, session


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
