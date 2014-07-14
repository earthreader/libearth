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
from .util import normalize_xml_encoding

__all__ = 'ATOM_XMLNS_SET', 'XML_XMLNS', 'parse_atom'


#: (:class:`frozenset`) The set of XML namespaces for Atom format.
ATOM_XMLNS_SET = frozenset([
    'http://www.w3.org/2005/Atom',
    'http://purl.org/atom/ns#'
])

#: (:class:`str`) The XML namespace for the predefined ``xml:`` prefix.
XML_XMLNS = 'http://www.w3.org/XML/1998/namespace'


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
    :type parse_entry: :class:`bool`
    :returns: a pair of (:class:`~libearth.feed.Feed`, crawler hint)
    :rtype: :class:`tuple`

    """
    root = fromstring(normalize_xml_encoding(xml))
    for atom_xmlns in ATOM_XMLNS_SET:
        if root.tag.startswith('{' + atom_xmlns + '}'):
            break
    feed_data = atom_get_feed_data(root, feed_url, atom_xmlns)
    entries = root.findall('{' + atom_xmlns + '}entry')
    if parse_entry:
        entries_data = atom_get_entry_data(entries, feed_url, atom_xmlns)
        feed_data.entries = entries_data
    return feed_data, None


def atom_parse_text_construct(data):
    text = Text()
    text_type = data.get('type')
    if text_type is not None:
        if text_type == 'text/plain':
            text_type = 'text'
        elif text_type == 'text/html':
            text_type = 'html'
        text.type = text_type
    if text.type in ('text', 'html'):
        text.value = data.text
    elif text.value == 'xhtml':
        text.value = ''  # TODO
    return text


def atom_parse_person_construct(data, xml_base, atom_xmlns, as_list=False):
    person = Person()
    xml_base = atom_get_xml_base(data, xml_base)
    for child in data:
        if child.tag == '{' + atom_xmlns + '}name':
            person.name = child.text
        elif child.tag == '{' + atom_xmlns + '}uri':
            person.uri = urlparse.urljoin(xml_base, child.text)
        elif child.tag == '{' + atom_xmlns + '}email':
            person.email = child.text
    if not person.name:
        if person.email:
            person.name = person.email
        elif person.uri:
            person.name = person.uri
        else:
            person = None
    if as_list:
        return [person] if person else []
    return person


def atom_get_feed_data(root, feed_url, atom_xmlns):
    feed_data = Feed()
    xml_base = atom_get_xml_base(root, feed_url)
    alt_id = None
    for data in root:
        if data.tag == '{' + atom_xmlns + '}id':
            feed_data.id = alt_id = atom_get_id_tag(data, xml_base)
        elif data.tag == '{' + atom_xmlns + '}title':
            feed_data.title = atom_get_title_tag(data)
        elif data.tag == '{' + atom_xmlns + '}updated':
            feed_data.updated_at = atom_parse_datetime(data)
        elif data.tag == '{' + atom_xmlns + '}modified':
            # Non-standard: some feeds use <modified> instead of <updated>
            # which is standard e.g. Naver Blog.
            if not feed_data.updated_at:
                feed_data.updated_at = atom_parse_datetime(data)
        elif data.tag == '{' + atom_xmlns + '}author':
            feed_data.authors.extend(
                atom_parse_person_construct(data, xml_base, atom_xmlns, True)
            )
        elif data.tag == '{' + atom_xmlns + '}category':
            category = atom_get_category_tag(data)
            if category:
                feed_data.categories.append(atom_get_category_tag(data))
        elif data.tag == '{' + atom_xmlns + '}contributor':
            feed_data.contributors.extend(
                atom_parse_person_construct(data, xml_base, atom_xmlns, True)
            )
        elif data.tag == '{' + atom_xmlns + '}link':
            link = atom_get_link_tag(data, xml_base)
            if link.relation == 'self':
                alt_id = alt_id or link.uri
            feed_data.links.append(link)
        elif data.tag == '{' + atom_xmlns + '}generator':
            feed_data.generator = atom_get_generator_tag(data, xml_base)
        elif data.tag == '{' + atom_xmlns + '}icon':
            feed_data.icon = atom_get_icon_tag(data, xml_base)
        elif data.tag == '{' + atom_xmlns + '}logo':
            feed_data.logo = atom_get_logo_tag(data, xml_base)
        elif data.tag == '{' + atom_xmlns + '}rights':
            feed_data.rights = atom_get_rights_tag(data)
        elif data.tag == '{' + atom_xmlns + '}subtitle':
            feed_data.subtitle = atom_get_subtitle_tag(data)
        elif data.tag == '{' + atom_xmlns + '}entry':
            break
    if feed_data.id is None:
        feed_data.id = alt_id or feed_url
    return feed_data


def atom_get_entry_data(entries, feed_url, atom_xmlns):
    entries_data = []
    for entry in entries:
        entry_data = Entry()
        xml_base = atom_get_xml_base(entry, feed_url)
        for data in entry:
            if data.tag == '{' + atom_xmlns + '}id':
                entry_data.id = atom_get_id_tag(data, xml_base)
            elif data.tag == '{' + atom_xmlns + '}title':
                entry_data.title = atom_get_title_tag(data)
            elif data.tag == '{' + atom_xmlns + '}updated':
                entry_data.updated_at = atom_parse_datetime(data)
            elif data.tag == '{' + atom_xmlns + '}modified':
                # Non-standard: some feeds use <modified> instead of <updated>
                # which is standard e.g. Naver Blog.
                if not entry_data.updated_at:
                    entry_data.updated_at = atom_parse_datetime(data)
            elif data.tag == '{' + atom_xmlns + '}author':
                entry_data.authors.extend(
                    atom_parse_person_construct(
                        data, xml_base, atom_xmlns,
                        as_list=True
                    )
                )
            elif data.tag == '{' + atom_xmlns + '}category':
                category = atom_get_category_tag(data)
                if category:
                    entry_data.categories.append(atom_get_category_tag(data))
            elif data.tag == '{' + atom_xmlns + '}contributor':
                entry_data.contributors.extend(
                    atom_parse_person_construct(
                        data, xml_base, atom_xmlns,
                        as_list=True
                    )
                )
            elif data.tag == '{' + atom_xmlns + '}link':
                entry_data.links.append(atom_get_link_tag(data, xml_base))
            elif data.tag == '{' + atom_xmlns + '}content':
                entry_data.content = atom_get_content_tag(data, xml_base)
            elif data.tag == '{' + atom_xmlns + '}published':
                entry_data.published_at = atom_parse_datetime(data)
            elif data.tag == '{' + atom_xmlns + '}rights':
                entry_data.rigthts = atom_get_rights_tag(data)
            elif data.tag == '{' + atom_xmlns + '}source':
                entry_data.source = atom_get_source_tag(
                    data, xml_base, atom_xmlns
                )
            elif data.tag == '{' + atom_xmlns + '}summary':
                entry_data.summary = atom_get_summary_tag(data)
        entries_data.append(entry_data)
    return entries_data


def atom_get_xml_base(data, default):
    if '{' + XML_XMLNS + '}base' in data.attrib:
        return data.attrib['{' + XML_XMLNS + '}base']
    else:
        return default


def atom_get_id_tag(data, xml_base):
    xml_base = atom_get_xml_base(data, xml_base)
    return urlparse.urljoin(xml_base, data.text)


def atom_get_title_tag(data):
    return atom_parse_text_construct(data)


def atom_parse_datetime(data):
    try:
        return Rfc3339().decode(data.text)
    except DecodeError:
        return Rfc822().decode(data.text)


def atom_get_category_tag(data):
    if not data.get('term'):
        return
    category = Category()
    category.term = data.get('term')
    category.scheme_uri = data.get('scheme')
    category.label = data.get('label')
    return category


def atom_get_link_tag(data, xml_base):
    xml_base = atom_get_xml_base(data, xml_base)
    link = Link(
        uri=urlparse.urljoin(xml_base, data.get('href')),
        mimetype=data.get('type'),
        language=data.get('hreflang'),
        title=data.get('title'),
        byte_size=data.get('length')
    )
    rel = data.get('rel')
    if rel:
        link.relation = rel
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


def atom_get_source_tag(data_dump, xml_base, atom_xmlns):
    source = Source()
    xml_base = atom_get_xml_base(data_dump[0], xml_base)
    authors = []
    categories = []
    contributors = []
    links = []
    for data in data_dump:
        xml_base = atom_get_xml_base(data, xml_base)
        if data.tag == '{' + atom_xmlns + '}author':
            authors.extend(
                atom_parse_person_construct(data, xml_base, atom_xmlns, True)
            )
            source.authors = authors
        elif data.tag == '{' + atom_xmlns + '}category':
            categories.append(atom_get_category_tag(data))
            source.categories = categories
        elif data.tag == '{' + atom_xmlns + '}contributor':
            contributors.extend(
                atom_parse_person_construct(data, xml_base, atom_xmlns, True)
            )
            source.contributors = contributors
        elif data.tag == '{' + atom_xmlns + '}link':
            links.append(atom_get_link_tag(data, xml_base))
            source.links = links
        elif data.tag == '{' + atom_xmlns + '}id':
            source.id = atom_get_id_tag(data, xml_base)
        elif data.tag == '{' + atom_xmlns + '}title':
            source.title = atom_get_title_tag(data)
        elif data.tag == '{' + atom_xmlns + '}updated':
            source.updated_at = atom_parse_datetime(data)
        elif data.tag == '{' + atom_xmlns + '}generator':
            source.generator = atom_get_generator_tag(data, xml_base)
        elif data.tag == '{' + atom_xmlns + '}icon':
            source.icon = atom_get_icon_tag(data, xml_base)
        elif data.tag == '{' + atom_xmlns + '}logo':
            source.logo = atom_get_logo_tag(data, xml_base)
        elif data.tag == '{' + atom_xmlns + '}rights':
            source.rights = atom_get_rights_tag(data)
        elif data.tag == '{' + atom_xmlns + '}subtitle':
            source.subtitle = atom_get_subtitle_tag(data)
    return source


def atom_get_summary_tag(data):
    summary_tag = atom_parse_text_construct(data)
    return summary_tag
