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

from ..codecs import Rfc3339
from ..compat.etree import fromstring
from ..feed import (Category, Content, Entry, Feed, Generator, Link,
                    Person, Source, Text)
from .util import normalize_xml_encoding

__all__ = 'XMLNS_ATOM', 'XMLNS_XML', 'parse_atom'


#: (:class:`str`) The XML namespace for Atom format.
XMLNS_ATOM = 'http://www.w3.org/2005/Atom'

#: (:class:`str`) The XML namespace for the predefined ``xml:`` prefix.
XMLNS_XML = 'http://www.w3.org/XML/1998/namespace'


def parse_atom(xml, feed_url, parse_entry=True):
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
    entries = root.findall('{' + XMLNS_ATOM + '}' + 'entry')
    feed_data = atom_get_feed_data(root, feed_url)
    if parse_entry:
        entries_data = atom_get_entry_data(entries, feed_url)
        feed_data.entries = entries_data
    return feed_data, None


def atom_parse_text_construct(data):
    text = Text()
    text_type = data.get('type')
    if text_type is not None:
        text.type = text_type
    if text.type in ('text', 'html'):
        text.value = data.text
    elif text.value == 'xhtml':
        text.value = ''  # TODO
    return text


def atom_parse_person_construct(data, xml_base):
    person = Person()
    xml_base = atom_get_xml_base(data, xml_base)
    for child in data:
        if child.tag == '{' + XMLNS_ATOM + '}' + 'name':
            person.name = child.text
        elif child.tag == '{' + XMLNS_ATOM + '}' + 'uri':
            person.uri = urlparse.urljoin(xml_base, child.text)
        elif child.tag == '{' + XMLNS_ATOM + '}' + 'email':
            person.email = child.text
    return person


def atom_get_feed_data(root, feed_url):
    feed_data = Feed()
    xml_base = atom_get_xml_base(root, feed_url)
    alt_id = None
    for data in root:
        if data.tag == '{' + XMLNS_ATOM + '}' + 'id':
            feed_data.id = alt_id = atom_get_id_tag(data, xml_base)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'title':
            feed_data.title = atom_get_title_tag(data)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'updated':
            feed_data.updated_at = atom_get_updated_tag(data)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'author':
            feed_data.authors.append(atom_get_author_tag(data, xml_base))
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'category':
            category = atom_get_category_tag(data)
            if category:
                feed_data.categories.append(atom_get_category_tag(data))
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'contributor':
            feed_data.contributors.append(
                atom_get_contributor_tag(data, xml_base)
            )
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'link':
            link = atom_get_link_tag(data, xml_base)
            if link.relation == 'self':
                alt_id = alt_id or link.uri
            feed_data.links.append(link)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'generator':
            feed_data.generator = atom_get_generator_tag(data, xml_base)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'icon':
            feed_data.icon = atom_get_icon_tag(data, xml_base)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'logo':
            feed_data.logo = atom_get_logo_tag(data, xml_base)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'rights':
            feed_data.rights = atom_get_rights_tag(data)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'subtitle':
            feed_data.subtitle = atom_get_subtitle_tag(data)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'entry':
            break
    if feed_data.id is None:
        feed_data.id = alt_id or feed_url
    return feed_data


def atom_get_entry_data(entries, feed_url):
    entries_data = []
    for entry in entries:
        entry_data = Entry()
        xml_base = atom_get_xml_base(entry, feed_url)
        for data in entry:
            if data.tag == '{' + XMLNS_ATOM + '}' + 'id':
                entry_data.id = atom_get_id_tag(data, xml_base)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'title':
                entry_data.title = atom_get_title_tag(data)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'updated':
                entry_data.updated_at = atom_get_updated_tag(data)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'author':
                entry_data.authors.append(atom_get_author_tag(data, xml_base))
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'category':
                category = atom_get_category_tag(data)
                if category:
                    entry_data.categories.append(atom_get_category_tag(data))
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'contributor':
                entry_data.contributors.append(
                    atom_get_contributor_tag(data, xml_base)
                )
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'link':
                entry_data.links.append(atom_get_link_tag(data, xml_base))
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'content':
                entry_data.content = atom_get_content_tag(data, xml_base)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'published':
                entry_data.published_at = atom_get_published_tag(data)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'rights':
                entry_data.rigthts = atom_get_rights_tag(data)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'source':
                entry_data.source = atom_get_source_tag(data, xml_base)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'summary':
                entry_data.summary = atom_get_summary_tag(data)
        entries_data.append(entry_data)
    return entries_data


def atom_get_xml_base(data, default):
    if '{' + XMLNS_XML + '}' + 'base' in data.attrib:
        return data.attrib['{' + XMLNS_XML + '}' + 'base']
    else:
        return default


def atom_get_id_tag(data, xml_base):
    xml_base = atom_get_xml_base(data, xml_base)
    return urlparse.urljoin(xml_base, data.text)


def atom_get_title_tag(data):
    return atom_parse_text_construct(data)


def atom_get_updated_tag(data):
    return Rfc3339().decode(data.text)


def atom_get_author_tag(data, xml_base):
    return atom_parse_person_construct(data, xml_base)


def atom_get_category_tag(data):
    if not data.get('term'):
        return
    category = Category()
    category.term = data.get('term')
    category.scheme_uri = data.get('scheme')
    category.label = data.get('label')
    return category


def atom_get_contributor_tag(data, xml_base):
    return atom_parse_person_construct(data, xml_base)


def atom_get_link_tag(data, xml_base):
    link = Link()
    xml_base = atom_get_xml_base(data, xml_base)
    link.uri = urlparse.urljoin(xml_base, data.get('href'))
    link.relation = data.get('rel')
    link.mimetype = data.get('type')
    link.language = data.get('hreflang')
    link.title = data.get('title')
    link.byte_size = data.get('length')
    return link


def atom_get_generator_tag(data, xml_base):
    generator = Generator()
    xml_base = atom_get_xml_base(data, xml_base)
    generator.value = data.text
    if 'uri' in data.attrib:
        generator.uri = urlparse.urljoin(xml_base, data.attrib['uri'])
    generator.version = data.get('version')
    return generator


def atom_get_icon_tag(data, xml_base):
    xml_base = atom_get_xml_base(data, xml_base)
    return urlparse.urljoin(xml_base, data.text)


def atom_get_logo_tag(data, xml_base):
    xml_base = atom_get_xml_base(data, xml_base)
    return urlparse.urljoin(xml_base, data.text)


def atom_get_rights_tag(data):
    return atom_parse_text_construct(data)


def atom_get_subtitle_tag(data):
    return atom_parse_text_construct(data)


def atom_get_content_tag(data, xml_base):
    content = Content()
    content.value = data.text
    content_type = data.get('type')
    if content_type is not None:
        content.type = content_type
    if 'src' in data.attrib:
        content.source_uri = urlparse.urljoin(xml_base, data.attrib['src'])
    return content


def atom_get_published_tag(data):
    return Rfc3339().decode(data.text)


def atom_get_source_tag(data_dump, xml_base):
    source = Source()
    xml_base = atom_get_xml_base(data_dump[0], xml_base)
    authors = []
    categories = []
    contributors = []
    links = []
    for data in data_dump:
        xml_base = atom_get_xml_base(data, xml_base)
        if data.tag == '{' + XMLNS_ATOM + '}' + 'author':
            authors.append(atom_get_author_tag(data, xml_base))
            source.authors = authors
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'category':
            categories.append(atom_get_category_tag(data))
            source.categories = categories
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'contributor':
            contributors.append(atom_get_contributor_tag(data, xml_base))
            source.contributors = contributors
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'link':
            links.append(atom_get_link_tag(data, xml_base))
            source.links = links
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'id':
            source.id = atom_get_id_tag(data, xml_base)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'title':
            source.title = atom_get_title_tag(data)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'updated':
            source.updated_at = atom_get_updated_tag(data)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'generator':
            source.generator = atom_get_generator_tag(data, xml_base)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'icon':
            source.icon = atom_get_icon_tag(data, xml_base)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'logo':
            source.logo = atom_get_logo_tag(data, xml_base)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'rights':
            source.rights = atom_get_rights_tag(data)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'subtitle':
            source.subtitle = atom_get_subtitle_tag(data)
    return source


def atom_get_summary_tag(data):
    summary_tag = atom_parse_text_construct(data)
    return summary_tag
