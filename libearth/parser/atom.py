""":mod:`libearth.parser.atom` --- Atom parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parsing Atom feed. Atom specification is :rfc:`4287`

.. todo::

   Parsing text construct which ``type`` is ``'xhtml'``.

"""
import copy
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from ..codecs import Rfc3339, Rfc822
from ..compat.etree import fromstring
from ..feed import (Category, Content, Entry, Feed, Generator, Link,
                    Person, Source, Text)
from ..schema import DecodeError
from .util import normalize_xml_encoding

__all__ = 'ATOM_XMLNS_SET', 'XML_XMLNS', 'parse_atom'


#: (:class:`frozenset`) The set of XML namespaces for Atom format.
ATOM_XMLNS_SET = frozenset([
    'http://www.w3.org/2005/Atom',
    'http://purl.org/atom/ns#'
])

#: (:class:`str`) The XML namespace for the predefined ``xml:`` prefix.
XML_XMLNS = 'http://www.w3.org/XML/1998/namespace'


def get_element_id(name_space, element_name):
    return '{' + name_space + '}' + element_name


def get_xml_base(data, default):
    if get_element_id(XML_XMLNS, 'base') in data.attrib:
        return data.attrib['{' + XML_XMLNS + '}base']
    else:
        return default


class AtomParser(object):

    def __init__(self, parser=None):
        if parser:
            self.parser = parser
        self.children_parser = {}

    def __call__(self, root_element, session):
        root, root_session = self.parser(root_element, session)
        for element_name, (parser, attr_name)\
                in self.children_parser.items():
            elements = root_element.findall(get_element_id(session.atom_xmlns,
                                                           element_name))
            for element in elements:
                session = copy.copy(root_session)
                session.xml_base = get_xml_base(element, session.xml_base)
                child = parser(element, session)
                if not child:
                    continue
                descriptor = getattr(type(root), attr_name)
                if descriptor.multiple:
                    getattr(root, attr_name).append(child)
                else:
                    setattr(root, attr_name, child)
        return root

    def path(self, element_name, attr_name=None):

        def decorator(func):
            if isinstance(func, AtomParser):
                func = func.parser
            parser = AtomParser(func)
            self.children_parser[element_name] = (parser,
                                                  attr_name or element_name)
            return parser

        return decorator


class AtomSession(object):

    atom_xmlns = None
    xml_base = None

    def __init__(self, atom_xmlns, xml_base):
        self.atom_xmlns = atom_xmlns
        self.xml_base = xml_base


atom_parser = AtomParser()


@atom_parser.path('feed')
def parse_feed(element, session):
    return Feed(), session


@atom_parser.path('entry')
def parse_entry(element, session):
    return Entry(), session


@parse_entry.path('source')
def parse_source(element, session):
    return Source(), session


@parse_feed.path('id')
@parse_feed.path('icon')
@parse_feed.path('logo')
@parse_entry.path('id')
@parse_source.path('id')
@parse_source.path('icon')
@parse_source.path('logo')
def parse_icon(element, session):
    return urlparse.urljoin(session.xml_base, element.text), session


@parse_feed.path('title')
@parse_feed.path('rights')
@parse_feed.path('subtitle')
@parse_entry.path('title')
@parse_entry.path('rights')
@parse_entry.path('summary')
@parse_source.path('title')
@parse_source.path('rights')
@parse_source.path('subtitle')
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


@parse_feed.path('author', 'authors')
@parse_feed.path('contributor', 'contributors')
@parse_entry.path('author', 'authors')
@parse_entry.path('contributor', 'contributors')
@parse_source.path('author', 'authors')
@parse_source.path('contributor', 'contributors')
def parse_person_construct(element, session):
    person = Person()
    for child in element:
        if child.tag == get_element_id(session.atom_xmlns, 'name'):
            person.name = child.text
        elif child.tag == get_element_id(session.atom_xmlns, 'uri'):
            person.uri = urlparse.urljoin(session.xml_base, child.text)
        elif child.tag == get_element_id(session.atom_xmlns, 'email'):
            person.email = child.text
    if not person.name:
        if person.email:
            person.name = person.email
        elif person.uri:
            person.name = person.uri
        else:
            person = None
    return person, session


@parse_feed.path('link', 'links')
@parse_entry.path('link', 'links')
@parse_source.path('link', 'links')
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


@parse_feed.path('updated', 'updated_at')
@parse_feed.path('modified', 'updated_at')
@parse_entry.path('updated', 'updated_at')
@parse_entry.path('published', 'published_at')
@parse_entry.path('modified', 'updated_at')
@parse_source.path('updated', 'updated_at')
def parse_datetime(element, session):
    try:
        return Rfc3339().decode(element.text), session
    except DecodeError:
        return Rfc822().decode(element.text), session


@parse_feed.path('category', 'categories')
@parse_entry.path('category', 'categories')
@parse_source.path('category', 'categories')
def parse_category(element, session):
    if not element.get('term'):
        return
    category = Category()
    category.term = element.get('term')
    category.scheme_uri = element.get('scheme')
    category.label = element.get('label')
    return category, session


@parse_feed.path('generator')
@parse_source.path('generator')
def parse_generator(element, session):
    generator = Generator()
    generator.value = element.text
    if 'uri' in element.attrib:
        generator.uri = urlparse.urljoin(session.xml_base,
                                         element.attrib['uri'])
    generator.version = element.get('version')
    return generator, session


@parse_entry.path('content')
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
