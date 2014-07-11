""":mod:`libearth.parser.atom` --- Atom parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parsing Atom feed. Atom specification is :rfc:`4287`

.. todo::

   Parsing text construct which ``type`` is ``'xhtml'``.

"""
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from ..codecs import Rfc3339, Rfc822
from ..compat.etree import fromstring
from ..feed import (Category, Content, Entry, Feed, Generator, Link,
                    Person, Source, Text)
from ..schema import DecodeError
from .base import ParserBase, SessionBase, get_element_id, get_xml_base
from .util import normalize_xml_encoding

__all__ = 'ATOM_XMLNS_SET', 'parse_atom'


#: (:class:`frozenset`) The set of XML namespaces for Atom format.
ATOM_XMLNS_SET = frozenset([
    'http://www.w3.org/2005/Atom',
    'http://purl.org/atom/ns#'
])


AtomSession = SessionBase


atom_parser = ParserBase()


@atom_parser.path('feed', ATOM_XMLNS_SET)
def parse_feed(element, session):
    return Feed(), session


@atom_parser.path('entry', ATOM_XMLNS_SET)
def parse_entry(element, session):
    return Entry(), session


@parse_entry.path('source', ATOM_XMLNS_SET)
def parse_source(element, session):
    return Source(), session


@parse_feed.path('id', ATOM_XMLNS_SET)
@parse_feed.path('icon', ATOM_XMLNS_SET)
@parse_feed.path('logo', ATOM_XMLNS_SET)
@parse_entry.path('id', ATOM_XMLNS_SET)
@parse_source.path('id', ATOM_XMLNS_SET)
@parse_source.path('icon', ATOM_XMLNS_SET)
@parse_source.path('logo', ATOM_XMLNS_SET)
def parse_icon(element, session):
    return urlparse.urljoin(session.xml_base, element.text), session


@parse_feed.path('title', ATOM_XMLNS_SET)
@parse_feed.path('rights', ATOM_XMLNS_SET)
@parse_feed.path('subtitle', ATOM_XMLNS_SET)
@parse_entry.path('title', ATOM_XMLNS_SET)
@parse_entry.path('rights', ATOM_XMLNS_SET)
@parse_entry.path('summary', ATOM_XMLNS_SET)
@parse_source.path('title', ATOM_XMLNS_SET)
@parse_source.path('rights', ATOM_XMLNS_SET)
@parse_source.path('subtitle', ATOM_XMLNS_SET)
def parse_text_construct(element, session):
    text = Text()
    text_type = element.get('type')
    if text_type is not None:
        if text_type == 'text/plain':
            text_type = 'text'
        elif text_type == 'text/html':
            text_type = 'html'
        text.type = text_type
    if text.type in ('text', 'html'):
        text.value = element.text
    elif text.value == 'xhtml':
        text.value = ''  # TODO
    return text, session


@parse_feed.path('author', ATOM_XMLNS_SET, 'authors')
@parse_feed.path('contributor', ATOM_XMLNS_SET, 'contributors')
@parse_entry.path('author', ATOM_XMLNS_SET, 'authors')
@parse_entry.path('contributor', ATOM_XMLNS_SET, 'contributors')
@parse_source.path('author', ATOM_XMLNS_SET, 'authors')
@parse_source.path('contributor', ATOM_XMLNS_SET, 'contributors')
def parse_person_construct(element, session):
    person = Person()
    for child in element:
        if child.tag == get_element_id(session.element_ns, 'name'):
            person.name = child.text
        elif child.tag == get_element_id(session.element_ns, 'uri'):
            person.uri = urlparse.urljoin(session.xml_base, child.text)
        elif child.tag == get_element_id(session.element_ns, 'email'):
            person.email = child.text
    if not person.name:
        if person.email:
            person.name = person.email
        elif person.uri:
            person.name = person.uri
        else:
            person = None
    return person, session


@parse_feed.path('link', ATOM_XMLNS_SET, 'links')
@parse_entry.path('link', ATOM_XMLNS_SET, 'links')
@parse_source.path('link', ATOM_XMLNS_SET, 'links')
def parse_link(element, session):
    link = Link(
        uri=urlparse.urljoin(session.xml_base, element.get('href')),
        mimetype=element.get('type'),
        language=element.get('hreflang'),
        title=element.get('title'),
        byte_size=element.get('length')
    )
    rel = element.get('rel')
    if rel:
        link.relation = rel
    return link, session


@parse_feed.path('updated', ATOM_XMLNS_SET, 'updated_at')
@parse_feed.path('modified', ATOM_XMLNS_SET, 'updated_at')
@parse_entry.path('updated', ATOM_XMLNS_SET, 'updated_at')
@parse_entry.path('published', ATOM_XMLNS_SET, 'published_at')
@parse_entry.path('modified', ATOM_XMLNS_SET, 'updated_at')
@parse_source.path('updated', ATOM_XMLNS_SET, 'updated_at')
def parse_datetime(element, session):
    try:
        return Rfc3339().decode(element.text), session
    except DecodeError:
        return Rfc822().decode(element.text), session


@parse_feed.path('category', ATOM_XMLNS_SET, 'categories')
@parse_entry.path('category', ATOM_XMLNS_SET, 'categories')
@parse_source.path('category', ATOM_XMLNS_SET, 'categories')
def parse_category(element, session):
    if not element.get('term'):
        return
    category = Category()
    category.term = element.get('term')
    category.scheme_uri = element.get('scheme')
    category.label = element.get('label')
    return category, session


@parse_feed.path('generator', ATOM_XMLNS_SET)
@parse_source.path('generator', ATOM_XMLNS_SET)
def parse_generator(element, session):
    generator = Generator()
    generator.value = element.text
    if 'uri' in element.attrib:
        generator.uri = urlparse.urljoin(session.xml_base,
                                         element.attrib['uri'])
    generator.version = element.get('version')
    return generator, session


@parse_entry.path('content', ATOM_XMLNS_SET)
def parse_content(element, session):
    content = Content()
    content.value = element.text
    content_type = element.get('type')
    if content_type is not None:
        content.type = content_type
    if 'src' in element.attrib:
        content.source_uri = urlparse.urljoin(session.xml_base,
                                              element.attrib['src'])
    return content, session


def parse_atom(xml, feed_url, need_entries=True):
    """Atom parser.  It parses the Atom XML and returns the feed data
    as internal representation.

    :param xml: target atom xml to parse
    :type xml: :class:`str`
    :param feed_url: the url used to retrieve the atom feed.
                     it will be the base url when there are any relative
                     urls without ``xml:base`` attribute
    :type feed_url: :class:`str`
    :param parse_entry: whether to parse inner items as well.
                        it's useful to ignore items when retrieve
                        ``<source>`` in rss 2.0.  :const:`True` by default.
    :type parse_item: :class:`bool`
    :returns: a pair of (:class:`~libearth.feed.Feed`, crawler hint)
    :rtype: :class:`tuple`

    """
    root = fromstring(normalize_xml_encoding(xml))
    for atom_xmlns in ATOM_XMLNS_SET:
        if root.tag.startswith('{' + atom_xmlns + '}'):
            break
    xml_base = get_xml_base(root, feed_url)
    session = AtomSession(atom_xmlns, xml_base)
    feed_data = parse_feed(root, session)
    if not feed_data.id:
        feed_data.id = feed_url
    if need_entries:
        entries = root.findall(get_element_id(atom_xmlns, 'entry'))
        entry_list = []
        for entry in entries:
            entry_list.append(parse_entry(entry, session))
        feed_data.entries = entry_list
    return feed_data, None
