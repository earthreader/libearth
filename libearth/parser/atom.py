""":mod:`libearth.parser.atom` --- Atom parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parsing Atom feed. Atom specification is :rfc:`4287`

.. todo::

   Parsing text construct which ``type`` is ``'xhtml'``.

"""
from libearth.codecs import Rfc3339

try:
    import urlparse
except:
    import urllib.parse as urlparse
try:
    from lxml import etree
except ImportError:
    try:
        from xml.etree import cElementTree as etree
    except ImportError:
        from xml.etree import ElementTree as etree

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
    :returns: feed data as internal representation
    :rtype: :class:`dict`

    """
    root = etree.fromstring(xml)
    entries = root.findall('{' + XMLNS_ATOM + '}' + 'entry')
    feed_data = atom_get_feed_data(root, feed_url)
    if parse_entry:
        entries_data = atom_get_entry_data(entries, feed_url)
        feed_data['entry'] = entries_data
    return feed_data, None


def atom_parse_text_construct(data):
    text = {}
    text['type'] = data.get('type')
    if text['type'] in (None, 'text', 'html'):
        text['text'] = data.text
    elif text['type'] == 'xhtml':
        text['text'] = ''  # TODO
    return text


def atom_parse_person_construct(data, xml_base):
    person = {}
    xml_base = atom_get_xml_base(data, xml_base)
    for child in data:
        if child.tag == '{' + XMLNS_ATOM + '}' + 'name':
            person['name'] = child.text
        elif child.tag == '{' + XMLNS_ATOM + '}' + 'uri':
            person['uri'] = urlparse.urljoin(xml_base, child.text)
        elif child.tag == '{' + XMLNS_ATOM + '}' + 'email':
            person['email'] = child.text
    return person


def atom_get_feed_data(root, feed_url):
    feed_data = {}
    xml_base = atom_get_xml_base(root, feed_url)
    multiple = ['author', 'category', 'contributor', 'link']
    for tag in multiple:
        feed_data[tag] = []
    for data in root:
        if data.tag == '{' + XMLNS_ATOM + '}' + 'id':
            feed_data['id'] = atom_get_id_tag(data, xml_base)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'title':
            feed_data['title'] = atom_get_title_tag(data)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'updated':
            feed_data['updated'] = atom_get_updated_tag(data)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'author':
            author_tag = atom_get_author_tag(data, xml_base)
            feed_data['author'].append(author_tag)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'category':
            category_tag = atom_get_category_tag(data)
            feed_data['category'].append(category_tag)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'contributor':
            contributor_tag = atom_get_contributor_tag(data, xml_base)
            feed_data['contributor'].append(contributor_tag)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'link':
            link_tag = atom_get_link_tag(data, xml_base)
            feed_data['link'].append(link_tag)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'generator':
            feed_data['generator'] = atom_get_generator_tag(data, xml_base)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'icon':
            feed_data['icon'] = atom_get_icon_tag(data, xml_base)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'logo':
            feed_data['logo'] = atom_get_logo_tag(data, xml_base)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'rights':
            feed_data['rights'] = atom_get_rights_tag(data)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'subtitle':
            feed_data['subtitle'] = atom_get_subtitle_tag(data)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'entry':
            break
    return feed_data


def atom_get_entry_data(entries, feed_url):
    entries_data = []
    multiple = ['author', 'category', 'contributor', 'link']
    for entry in entries:
        entry_data = {}
        xml_base = atom_get_xml_base(entry, feed_url)
        for tag in multiple:
            entry_data[tag] = []
        for data in entry:
            if data.tag == '{' + XMLNS_ATOM + '}' + 'entry':
                entry_data['entry'] = atom_get_xml_base(data)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'id':
                entry_data['id'] = atom_get_id_tag(data, xml_base)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'title':
                entry_data['title'] = atom_get_title_tag(data)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'updated':
                entry_data['updated'] = atom_get_updated_tag(data)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'author':
                author_tag = atom_get_author_tag(data, xml_base)
                entry_data['author'].append(author_tag)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'category':
                category_tag = atom_get_category_tag(data)
                entry_data['category'].append(category_tag)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'contributor':
                contributor_tag = atom_get_contributor_tag(data, xml_base)
                entry_data['contributor'].append(contributor_tag)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'link':
                link_tag = atom_get_link_tag(data, xml_base)
                entry_data['link'].append(link_tag)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'content':
                entry_data['content'] = atom_get_content_tag(data, xml_base)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'published':
                entry_data['published'] = atom_get_published_tag(data)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'rights':
                entry_data['rigths'] = atom_get_rights_tag(data)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'source':
                entry_data['source'] = atom_get_source_tag(data)
            elif data.tag == '{' + XMLNS_ATOM + '}' + 'summary':
                entry_data['source'] == atom_get_summary_tag(data)
        entries_data.append(entry_data)
    return entries_data


def atom_get_xml_base(data, default):
    if '{' + XMLNS_XML + '}' + 'base' in data.attrib:
        return data.attrib['{' + XMLNS_XML + '}' + 'base']
    else:
        return default


def atom_get_id_tag(data, xml_base):
    id_tag = {}
    xml_base = atom_get_xml_base(data, xml_base)
    id_tag['uri'] = urlparse.urljoin(xml_base, data.text)
    return id_tag


def atom_get_title_tag(data):
    title_tag = atom_parse_text_construct(data)
    return title_tag


def atom_get_updated_tag(data):
    updated_tag = Rfc3339().decode(data.text)
    return updated_tag


def atom_get_author_tag(data, xml_base):
    author_tag = atom_parse_person_construct(data, xml_base)
    return author_tag


def atom_get_category_tag(data):
    category_tag = {}
    category_tag['term'] = data.get('term')
    category_tag['scheme'] = data.get('scheme')
    category_tag['label'] = data.get('label')
    return category_tag


def atom_get_contributor_tag(data, xml_base):
    contributor_tag = atom_parse_person_construct(data, xml_base)
    return contributor_tag


def atom_get_link_tag(data, xml_base):
    link_tag = {}
    xml_base = atom_get_xml_base(data, xml_base)
    link_tag['href'] = urlparse.urljoin(xml_base, data.get('href'))
    link_tag['rel'] = data.get('rel')
    link_tag['type'] = data.get('type')
    link_tag['hreflang'] = data.get('hreflang')
    link_tag['title'] = data.get('title')
    link_tag['length'] = data.get('length')
    return link_tag


def atom_get_generator_tag(data, xml_base):
    generator_tag = {}
    xml_base = atom_get_xml_base(data, xml_base)
    generator_tag['text'] = data.text
    if 'uri' in data.attrib:
        generator_tag['uri'] = urlparse.urljoin(xml_base, data.attrib['uri'])
    else:
        generator_tag['uri'] = None
    generator_tag['version'] = data.get('version')
    return generator_tag


def atom_get_icon_tag(data, xml_base):
    icon_tag = {}
    xml_base = atom_get_xml_base(data, xml_base)
    icon_tag['uri'] = urlparse.urljoin(xml_base, data.text)
    return icon_tag


def atom_get_logo_tag(data, xml_base):
    logo_tag = {}
    xml_base = atom_get_xml_base(data, xml_base)
    logo_tag['uri'] = urlparse.urljoin(xml_base, data.text)
    return logo_tag


def atom_get_rights_tag(data):
    rights_tag = atom_parse_text_construct(data)
    return rights_tag


def atom_get_subtitle_tag(data):
    subtitle_tag = atom_parse_text_construct(data)
    return subtitle_tag


def atom_get_content_tag(data, xml_base):
    content_tag = {}
    content_tag['text'] = data.text
    content_tag['type'] = data.get('type')
    if 'src' in data.attrib:
        content_tag['src'] = urlparse.urljoin(xml_base, data.attrib['src'])
    else:
        content_tag['src'] = None
    return content_tag


def atom_get_published_tag(data):
    published_tag = Rfc3339().decode(data.text)
    return published_tag


def atom_get_source_tag(data_dump, xml_base):
    source_tag = {}
    xml_base = atom_get_xml_base(data_dump[0], xml_base)
    multiple = ['author', 'category', 'contributor', 'link']
    for tag in multiple:
        source_tag[tag] = []
    for data in data_dump:
        xml_base = atom_get_xml_base(data, xml_base)
        if data.tag == '{' + XMLNS_ATOM + '}' + 'author':
            author_tag = atom_get_author_tag(data, xml_base)
            source_tag['author'].append(author_tag)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'category':
            category_tag = atom_get_category_tag(data)
            source_tag['category'].append(category_tag)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'contributor':
            contributor_tag = atom_get_contributor_tag(data, xml_base)
            source_tag['contributor'].append(contributor_tag)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'link':
            link_tag = atom_get_link_tag(data, xml_base)
            source_tag['link'].append(link_tag)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'id':
            source_tag['id'] = atom_get_id_tag(data)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'title':
            source_tag['title'] = atom_get_title_tag(data)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'updated':
            source_tag['updated'] = atom_get_updated_tag(data)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'generator':
            source_tag['generator'] = atom_get_generator_tag(data, xml_base)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'icon':
            source_tag['icon'] = atom_get_icon_tag(data, xml_base)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'logo':
            source_tag['logo'] = atom_get_logo_tag(data, xml_base)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'rights':
            source_tag['rights'] = atom_get_rights_tag(data)
        elif data.tag == '{' + XMLNS_ATOM + '}' + 'subtitle':
            source_tag['subtitle'] = atom_get_subtitle_tag(data)
    return source_tag


def atom_get_summary_tag(data):
    summary_tag = atom_parse_text_construct(data)
    return summary_tag
