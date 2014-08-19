""":mod:`libearth.parser.rss1` --- RSS 1.0 parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parsing RSS 1.0 feed.

"""
from ..compat.etree import fromstring
from ..feed import Category, Entry, Feed
from .base import ParserBase, get_element_id
from .rss_base import (CONTENT_XMLNS, RSSSession, content_parser,
                       datetime_parser, guess_default_tzinfo, link_parser,
                       make_legal_as_atom, person_parser, subtitle_parser,
                       text_parser)
from .util import normalize_xml_encoding


#: (:class:`str`) The XML namespace used in RSS1 feed.
RSS1_XMLNS = 'http://purl.org/rss/1.0/'
#: (:class:`str`) The XML namespace for the predefined ``dc:`` prefix.
DC_NAMESPACE = 'http://purl.org/dc/elements/1.1/'


rss1_parser = ParserBase()


@rss1_parser.path('channel', [RSS1_XMLNS])
def parse_channel(element, session):
    return Feed(), session


@rss1_parser.path('item', [RSS1_XMLNS])
def parse_item(element, session):
    return Entry(), session


@parse_channel.path('description', [RSS1_XMLNS, DC_NAMESPACE], 'subtitle')
def parse_subtitle(element, session):
    return subtitle_parser(element, session)


@parse_channel.path('creator', [DC_NAMESPACE], 'authors')
@parse_channel.path('contributor', [DC_NAMESPACE], 'contributors')
@parse_channel.path('publisher', [DC_NAMESPACE], 'contributors')
@parse_item.path('creator', [DC_NAMESPACE], 'authors')
@parse_item.path('contributor', [DC_NAMESPACE], 'contributors')
@parse_item.path('publisher', [DC_NAMESPACE], 'contributors')
def parse_person(element, session):
    return person_parser(element, session)


@parse_channel.path('date', [DC_NAMESPACE], 'updated_at')
@parse_item.path('date', [DC_NAMESPACE], 'updated_at')
def parse_datetime(element, session):
    return datetime_parser(element, session)


@parse_channel.path('title', [RSS1_XMLNS, DC_NAMESPACE])
@parse_channel.path('rights', [DC_NAMESPACE])
@parse_item.path('title', [RSS1_XMLNS, DC_NAMESPACE])
@parse_item.path('rights', [DC_NAMESPACE])
def parse_text(element, session):
    return text_parser(element, session)


@parse_channel.path('link', [RSS1_XMLNS], 'links')
@parse_item.path('link', [RSS1_XMLNS], 'links')
def parse_link(element, session):
    return link_parser(element, session)


@parse_item.path('encoded', [CONTENT_XMLNS], 'content')
@parse_item.path('description', [RSS1_XMLNS, DC_NAMESPACE], 'content')
def parse_content(element, session):
    return content_parser(element, session)


@parse_channel.path('identifier', [DC_NAMESPACE], 'id')
@parse_item.path('identifier', [DC_NAMESPACE])
def parse_id(element, session):
    return element.text, session


@parse_channel.path('type', [DC_NAMESPACE], 'categories')
@parse_channel.path('subject', [DC_NAMESPACE], 'categories')
@parse_item.path('type', [DC_NAMESPACE], 'categories')
@parse_item.path('subject', [DC_NAMESPACE], 'categories')
def parse_category(element, session):
    return Category(term=element.text), session


def parse_rss1(xml, feed_url=None, parse_entry=True):
    root = fromstring(normalize_xml_encoding(xml))
    channel = root.find(get_element_id(RSS1_XMLNS, 'channel'))
    default_tzinfo = guess_default_tzinfo(root, feed_url)
    session = RSSSession(feed_url, default_tzinfo)
    feed_data = parse_channel(channel, session)
    if parse_entry:
        entries = root.findall(get_element_id(RSS1_XMLNS, 'item'))
        entry_list = []
        for entry in entries:
            entry_list.append(parse_item(entry, session))
        feed_data.entries = entry_list
    make_legal_as_atom(feed_data, session)
    return feed_data, None
