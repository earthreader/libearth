""":mod:`libearth.parser` --- Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pasring RSS feed of RSS2.0 and Atom and translate into Atom. Atom specification
is :rfc:`4287`

.. todo::

    - RSS2.0 Parser
    - Parsing text construct which type is 'xhtml'

"""
import datetime
import re

from .tz import FixedOffset

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


XMLNS_ATOM = '{http://www.w3.org/2005/Atom}'
XMLNS_XML = "{http://www.w3.org/XML/1998/namespace}"


def parse_atom(xml, feed_url):
    """Parsing function of Atom. This function parse the Atom XML and
    return feed data.

    :param xml: Target Atom XML to parse.
    :type xml: :class:`str`
    :param feed_url: Source of Atom XML. If xml:base is not defined in XML,
                     it became default base url.
    :type feed_url: :class:`str`

    """
    root = etree.fromstring(xml)
    entries = root.findall(XMLNS_ATOM + 'entry')
    feed_data = atom_get_feed_data(root, feed_url)
    entries_data = atom_get_entry_data(entries, feed_url)
    feed_data['entry'] = entries_data
    return feed_data


def atom_parse_text_construct(data):
    text = {}
    text['type'] = atom_get_optional_attribute(data, 'type')
    if text['type'] in (None, 'text', 'html'):
        text['text'] = data.text
    elif text['type'] == 'xhtml':
        text['text'] = ''  # TODO
    return text


def atom_parse_person_construct(data, xml_base):
    person = {}
    xml_base = atom_get_xml_base(data, xml_base)
    for child in data:
        if child.tag == XMLNS_ATOM + 'name':
            person['name'] = child.text
        elif child.tag == XMLNS_ATOM + 'uri':
            person['uri'] = urlparse.urljoin(xml_base, data.text)
        elif child.tag == XMLNS_ATOM + 'email':
            person['email'] = child.text
    return person


def atom_parse_date_construct(data):
    date = {}
    text = data.text
    date_and_time = text[:19]
    second_fraction_and_timezone = re.search('\.?([^\+\-Z]*)(.+)', text[19:])
    datetime_object = datetime.datetime.strptime(date_and_time,
                                                 '%Y-%m-%dT%H:%M:%S')
    if second_fraction_and_timezone.group(1):
        second_fraction = second_fraction_and_timezone.group(1)
        microsecond = int(second_fraction)*pow(10, 6-len(second_fraction))
        datetime_object = datetime_object.replace(microsecond=microsecond)
    if not second_fraction_and_timezone.group(2).startswith('Z'):
        dump = second_fraction_and_timezone.group(2)
        sign = dump[0]
        hours = dump[1:3]
        minutes = dump[4:6]
        if sign == '+':
            offset = int(hours)*60+int(minutes)
        else:
            offset = int(hours)*60+int(minutes)*(-1)
        datetime_object = datetime_object.replace(tzinfo=FixedOffset(offset))
    date['datetime'] = datetime_object
    return date


def atom_get_feed_data(root, feed_url):
    feed_data = {}
    xml_base = feed_url
    if XMLNS_XML + 'base' in root.attrib:
        xml_base = root.attrib[XMLNS_XML + 'base']
    multiple = ['author', 'category', 'contributor', 'link']
    for tag in multiple:
        feed_data[tag] = []
    for data in root:
        if data.tag == XMLNS_ATOM + 'id':
            feed_data['id'] = atom_get_id_tag(data, xml_base)
        elif data.tag == XMLNS_ATOM + 'title':
            feed_data['title'] = atom_get_title_tag(data)
        elif data.tag == XMLNS_ATOM + 'updated':
            feed_data['updated'] = atom_get_updated_tag(data)
        elif data.tag == XMLNS_ATOM + 'author':
            author_tag = atom_get_author_tag(data, xml_base)
            feed_data['author'].append(author_tag)
        elif data.tag == XMLNS_ATOM + 'category':
            category_tag = atom_get_category_tag(data)
            feed_data['category'].append(category_tag)
        elif data.tag == XMLNS_ATOM + 'contributor':
            contributor_tag = atom_get_contributor_tag(data, xml_base)
            feed_data['contributor'].append(contributor_tag)
        elif data.tag == XMLNS_ATOM + 'link':
            link_tag = atom_get_link_tag(data, xml_base)
            feed_data['link'].append(link_tag)
        elif data.tag == XMLNS_ATOM + 'generator':
            feed_data['generator'] = atom_get_generator_tag(data, xml_base)
        elif data.tag == XMLNS_ATOM + 'icon':
            feed_data['icon'] = atom_get_icon_tag(data, xml_base)
        elif data.tag == XMLNS_ATOM + 'logo':
            feed_data['logo'] = atom_get_logo_tag(data, xml_base)
        elif data.tag == XMLNS_ATOM + 'rights':
            feed_data['rights'] = atom_get_rights_tag(data)
        elif data.tag == XMLNS_ATOM + 'subtitle':
            feed_data['subtitle'] = atom_get_subtitle_tag(data)
        elif data.tag == XMLNS_ATOM + 'entry':
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
            if data.tag == XMLNS_ATOM + 'entry':
                entry_data['entry'] = atom_get_xml_base(data)
            elif data.tag == XMLNS_ATOM + 'id':
                entry_data['id'] = atom_get_id_tag(data, xml_base)
            elif data.tag == XMLNS_ATOM + 'title':
                entry_data['title'] = atom_get_title_tag(data)
            elif data.tag == XMLNS_ATOM + 'updated':
                entry_data['updated'] = atom_get_updated_tag(data)
            elif data.tag == XMLNS_ATOM + 'author':
                author_tag = atom_get_author_tag(data, xml_base)
                entry_data['author'].append(author_tag)
            elif data.tag == XMLNS_ATOM + 'category':
                category_tag = atom_get_category_tag(data)
                entry_data['category'].append(category_tag)
            elif data.tag == XMLNS_ATOM + 'contributor':
                contributor_tag = atom_get_contributor_tag(data, xml_base)
                entry_data['contributor'].append(contributor_tag)
            elif data.tag == XMLNS_ATOM + 'link':
                link_tag = atom_get_link_tag(data, xml_base)
                entry_data['link'].append(link_tag)
            elif data.tag == XMLNS_ATOM + 'content':
                entry_data['content'] = atom_get_content_tag(data)
            elif data.tag == XMLNS_ATOM + 'published':
                entry_data['published'] = atom_get_published_tag(data)
            elif data.tag == XMLNS_ATOM + 'rights':
                entry_data['rigths'] = atom_get_rights_tag(data)
            elif data.tag == XMLNS_ATOM + 'source':
                entry_data['source'] = atom_get_source_tag(data)
            elif data.tag == XMLNS_ATOM + 'summary':
                entry_data['source'] == atom_get_summary_tag(data)
        entries_data.append(entry_data)
    return entries_data


def atom_get_optional_attribute(data, attrib_name, xml_base=None):
    iri = ['href', 'src', 'uri']
    if attrib_name in iri:
        return urlparse.urljoin(xml_base, data.attrib[attrib_name])
    if attrib_name in data.attrib:
        return data.attrib[attrib_name]


def atom_get_xml_base(data, default):
    if XMLNS_XML + 'base' in data.attrib:
        return data.attrib[XMLNS_XML + 'base']
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
    updated_tag = atom_parse_date_construct(data)
    return updated_tag


def atom_get_author_tag(data, xml_base):
    author_tag = atom_parse_person_construct(data, xml_base)
    return author_tag


def atom_get_category_tag(data):
    category_tag = {}
    category_tag['term'] = atom_get_optional_attribute(data, 'term')
    category_tag['scheme'] = atom_get_optional_attribute(data, 'scheme')
    category_tag['label'] = atom_get_optional_attribute(data, 'label')
    return category_tag


def atom_get_contributor_tag(data, xml_base):
    contributor_tag = atom_parse_person_construct(data, xml_base)
    return contributor_tag


def atom_get_link_tag(data, xml_base):
    link_tag = {}
    xml_base = atom_get_xml_base(data, xml_base)
    link_tag['href'] = atom_get_optional_attribute(data, 'href', xml_base)
    link_tag['rel'] = atom_get_optional_attribute(data, 'rel')
    link_tag['type'] = atom_get_optional_attribute(data, 'type')
    link_tag['hreflang'] = atom_get_optional_attribute(data, 'hreflang')
    link_tag['title'] = atom_get_optional_attribute(data, 'title')
    link_tag['length'] = atom_get_optional_attribute(data, 'length')
    return link_tag


def atom_get_generator_tag(data, xml_base):
    generator_tag = {}
    xml_base = atom_get_xml_base(data, xml_base)
    generator_tag['text'] = data.text
    generator_tag['uri'] = atom_get_optional_attribute(data, 'uri', xml_base)
    generator_tag['version'] = atom_get_optional_attribute(data, 'version')
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


def atom_get_content_tag(data):
    content_tag = {}
    content_tag['text'] = data.text
    content_tag['type'] = atom_get_optional_attribute(data, 'type')
    return content_tag


def atom_get_published_tag(data):
    published_tag = atom_parse_date_construct(data)
    return published_tag


def atom_get_source_tag(data_dump, xml_base):
    source_tag = {}
    xml_base = atom_get_xml_base(data_dump[0], xml_base)
    multiple = ['author', 'category', 'contributor', 'link']
    for tag in multiple:
        source_tag[tag] = []
    for data in data_dump:
        xml_base = atom_get_xml_base(data, xml_base)
        if data.tag == XMLNS_ATOM + 'author':
            author_tag = atom_get_author_tag(data, xml_base)
            source_tag['author'].append(author_tag)
        elif data.tag == XMLNS_ATOM + 'category':
            category_tag = atom_get_category_tag(data)
            source_tag['category'].append(category_tag)
        elif data.tag == XMLNS_ATOM + 'contributor':
            contributor_tag = atom_get_contributor_tag(data, xml_base)
            source_tag['contributor'].append(contributor_tag)
        elif data.tag == XMLNS_ATOM + 'link':
            link_tag = atom_get_link_tag(data, xml_base)
            source_tag['link'].append(link_tag)
        elif data.tag == XMLNS_ATOM + 'id':
            source_tag['id'] = atom_get_id_tag(data)
        elif data.tag == XMLNS_ATOM + 'title':
            source_tag['title'] = atom_get_title_tag(data)
        elif data.tag == XMLNS_ATOM + 'updated':
            source_tag['updated'] = atom_get_updated_tag(data)
        elif data.tag == XMLNS_ATOM + 'generator':
            source_tag['generator'] = atom_get_generator_tag(data, xml_base)
        elif data.tag == XMLNS_ATOM + 'icon':
            source_tag['icon'] = atom_get_icon_tag(data, xml_base)
        elif data.tag == XMLNS_ATOM + 'logo':
            source_tag['logo'] = atom_get_logo_tag(data, xml_base)
        elif data.tag == XMLNS_ATOM + 'rights':
            source_tag['rights'] = atom_get_rights_tag(data)
        elif data.tag == XMLNS_ATOM + 'subtitle':
            source_tag['subtitle'] = atom_get_subtitle_tag(data)
    return source_tag


def atom_get_summary_tag(data):
    summary_tag = atom_parse_text_construct(text)
    return summary_tag
