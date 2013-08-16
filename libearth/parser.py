""":mod:`libearth.parser` --- Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import datetime
import re
import sys
try:
    from lxml import etree
except ImportError:
    try:
        from xml.etree import cElementTree as etree
    except ImportError:
        from xml.etree import ElementTree as etree


XMLNS_ATOM = '{http://www.w3.org/2005/Atom}'
XMLNS_XML = "{http://www.w3.org/XML/1998/namespace}"


def parse_atom(xml):
    root = etree.fromstring(xml)
    entries = root.findall(XMLNS_ATOM + 'entry')
    feed_data = atom_get_feed_data(root)
    entries_data = atom_get_entry_data(entries)
    feed_data['entry'] = entries_data
    return feed_data


def atom_get_feed_data(root):
    feed_data = {}
    multiple = ['author', 'category', 'contributor', 'link']
    for tag in multiple:
        feed_data[tag] = []
    _iter = root.iter() if sys.version_info >= (2, 7) else root.getiterator()
    data = next(_iter)
    while not data.tag == XMLNS_ATOM + 'entry':
        if data.tag == XMLNS_ATOM + 'feed':
            feed_data['feed'] = atom_get_common_attribute(data, None)
        elif data.tag == XMLNS_ATOM + 'id':
            feed_data['id'] = atom_get_id_tag(data)
        elif data.tag == XMLNS_ATOM + 'title':
            feed_data['title'] = atom_get_title_tag(data)
        elif data.tag == XMLNS_ATOM + 'updated':
            feed_data['updated'] = atom_get_updated_tag(data)
        elif data.tag == XMLNS_ATOM + 'author':
            author_tag = atom_get_author_tag(data)
            feed_data['author'].append(author_tag)
        elif data.tag == XMLNS_ATOM + 'category':
            category_tag = atom_get_category_tag(data)
            feed_data['category'].append(category_tag)
        elif data.tag == XMLNS_ATOM + 'contributor':
            contributor_tag = atom_get_contributor_tag(data)
            feed_data['contributor'].append(contributor_tag)
        elif data.tag == XMLNS_ATOM + 'link':
            link_tag = atom_get_link_tag(data)
            feed_data['link'].append(link_tag)
        elif data.tag == XMLNS_ATOM + 'generator':
            feed_data['generator'] = atom_get_generator_tag(data)
        elif data.tag == XMLNS_ATOM + 'icon':
            feed_data['icon'] = atom_get_icon_tag(data)
        elif data.tag == XMLNS_ATOM + 'logo':
            feed_data['logo'] = atom_get_logo_tag(data)
        elif data.tag == XMLNS_ATOM + 'rights':
            feed_data['rights'] = atom_get_rights_tag(data)
        elif data.tag == XMLNS_ATOM + 'subtitle':
            feed_data['subtitle'] = atom_get_subtitle_tag(data)
        data = next(_iter)
    return feed_data


def atom_get_entry_data(entries):
    entries_data = []
    multiple = ['author', 'category', 'contributor', 'link']
    for entry in entries:
        entry_data = {}
        for tag in multiple:
            entry_data[tag] = []
        for data in entry:
            if data.tag == XMLNS_ATOM + 'entry':
                entry_data['entry'] = atom_get_common_attribute(data, None)
            elif data.tag == XMLNS_ATOM + 'id':
                entry_data['id'] = atom_get_id_tag(data)
            elif data.tag == XMLNS_ATOM + 'title':
                entry_data['title'] = atom_get_title_tag(data)
            elif data.tag == XMLNS_ATOM + 'updated':
                entry_data['updated'] = atom_get_updated_tag(data)
            elif data.tag == XMLNS_ATOM + 'author':
                author_tag = atom_get_author_tag(data)
                entry_data['author'].append(author_tag)
            elif data.tag == XMLNS_ATOM + 'category':
                category_tag = atom_get_category_tag(data)
                entry_data['category'].append(category_tag)
            elif data.tag == XMLNS_ATOM + 'contributor':
                contributor_tag = atom_get_contributor_tag(data)
                entry_data['contributor'].append(contributor_tag)
            elif data.tag == XMLNS_ATOM + 'link':
                link_tag = atom_get_link_tag(data)
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


def atom_get_optional_attribute(data, attrib_name):
    if attrib_name in data.attrib:
        return data.attrib[attrib_name]


def atom_get_common_attribute(data, *args):
    common_attribute = {}
    for attrib in data.attrib:
        if attrib == XMLNS_XML + 'base':
            common_attribute['xml:base'] = data.attrib[attrib]
        elif attrib == XMLNS_XML + 'lang':
            common_attribute['xml:lang'] = data.attrib[attrib]
        elif not attrib in args:
            common_attribute[attrib] = data.attrib[attrib]
    return common_attribute


def atom_get_id_tag(data):
    id_tag = atom_get_common_attribute(data, None)
    id_tag['uri'] = data.text
    return id_tag


def atom_get_title_tag(data):
    title_optional_attribute = ['type']
    title_tag = atom_get_common_attribute(data, title_optional_attribute)
    title_tag['text'] = data.text
    title_tag['type'] = atom_get_optional_attribute(data, 'type')
    return title_tag


def atom_get_updated_tag(data):
    updated_tag = atom_get_common_attribute(data, None)
    updated_tag['datetime'] = atom_date_time(data.text)
    return updated_tag


def atom_get_author_tag(data):
    author_tag = atom_get_common_attribute(data, None)
    for child in data:
        if child.tag == XMLNS_ATOM + 'name':
            author_tag['name'] = child.text
        elif child.tag == XMLNS_ATOM + 'uri':
            author_tag['uri'] = child.text
        elif child.tag == XMLNS_ATOM + 'email':
            author_tag['email'] = child.text
    return author_tag


def atom_get_category_tag(data):
    category_required_attribute = ['term']
    category_optional_attribute = ['scheme', 'label']
    category_tag = atom_get_common_attribute(data,
                                             category_required_attribute,
                                             category_optional_attribute)
    category_tag['term'] = atom_get_optional_attribute(data, 'term')
    category_tag['scheme'] = atom_get_optional_attribute(data, 'scheme')
    category_tag['label'] = atom_get_optional_attribute(data, 'label')
    return category_tag


def atom_get_contributor_tag(data):
    contributor_tag = atom_get_common_attribute(data, None)
    for child in data:
        if child.tag == XMLNS_ATOM + 'name':
            contributor_tag['name'] = child.text
        elif child.tag == XMLNS_ATOM + 'url':
            contributor_tag['uri'] = child.text
        elif child.tag == XMLNS_ATOM + 'email':
            contributor_tag['email'] = child.text
    return contributor_tag


def atom_get_link_tag(data):
    link_optional_attribute = ['href', 'rel', 'type', 'hreflang',
                               'title', 'length']
    link_tag = atom_get_common_attribute(data, link_optional_attribute)
    link_tag['href'] = atom_get_optional_attribute(data, 'href')
    link_tag['rel'] = atom_get_optional_attribute(data, 'rel')
    link_tag['type'] = atom_get_optional_attribute(data, 'type')
    link_tag['hreflang'] = atom_get_optional_attribute(data, 'hreflang')
    link_tag['title'] = atom_get_optional_attribute(data, 'title')
    link_tag['length'] = atom_get_optional_attribute(data, 'length')
    return link_tag


def atom_get_generator_tag(data):
    generator_optional_attribute = ['uri', 'version']
    generator_tag = \
        atom_get_common_attribute(data, generator_optional_attribute)
    generator_tag['text'] = data.text
    generator_tag['uri'] = atom_get_optional_attribute(data, 'uri')
    generator_tag['version'] = atom_get_optional_attribute(data, 'version')
    return generator_tag


def atom_get_icon_tag(data):
    icon_tag = atom_get_common_attribute(data, None)
    icon_tag['uri'] = data.text
    return icon_tag


def atom_get_logo_tag(data):
    logo_tag = atom_get_common_attribute(data, None)
    logo_tag['uri'] = data.text
    return logo_tag


def atom_get_rights_tag(data):
    rights_optional_attribute = ['type']
    rights_tag = atom_get_common_attribute(data, rights_optional_attribute)
    rights_tag['text'] = data.text
    rights_tag['type'] = atom_get_optional_attribute(data, 'type')
    return rights_tag


def atom_get_subtitle_tag(data):
    subtitle_optional_attribute = ['type']
    subtitle_tag = atom_get_common_attribute(data, subtitle_optional_attribute)
    subtitle_tag['text'] = data.text
    subtitle_tag['type'] = atom_get_optional_attribute(data, 'type')
    return subtitle_tag


def atom_get_content_tag(data):
    content_optional_attribute = ['type']
    content_tag = atom_get_common_attribute(data, content_optional_attribute)
    content_tag['text'] = data.text
    content_tag['type'] = atom_get_optional_attribute(data, 'type')
    return content_tag


def atom_get_published_tag(data):
    published_tag = atom_get_common_attribute(data, None)
    published_tag['datetime'] = atom_date_time(data.text)
    return published_tag


def atom_get_source_tag(data_dump):
    source_tag = atom_get_common_attribute(data_dump, None)
    multiple = ['author', 'category', 'contributor', 'link']
    for tag in multiple:
        source_tag[tag] = []
    for data in data_dump:
        if data.tag == XMLNS_ATOM + 'author':
            author_tag = atom_get_author_tag(data)
            source_tag['author'].append(author_tag)
        elif data.tag == XMLNS_ATOM + 'category':
            category_tag = atom_get_category_tag(data)
            source_tag['category'].append(category_tag)
        elif data.tag == XMLNS_ATOM + 'contributor':
            contributor_tag = atom_get_contributor_tag(data)
            source_tag['contributor'].append(contributor_tag)
        elif data.tag == XMLNS_ATOM + 'link':
            link_tag = atom_get_link_tag(data)
            source_tag['link'].append(link_tag)
        elif data.tag == XMLNS_ATOM + 'id':
            source_tag['id'] = atom_get_id_tag(data)
        elif data.tag == XMLNS_ATOM + 'title':
            source_tag['title'] = atom_get_title_tag(data)
        elif data.tag == XMLNS_ATOM + 'updated':
            source_tag['updated'] = atom_get_updated_tag(data)
        elif data.tag == XMLNS_ATOM + 'generator':
            source_tag['generator'] = atom_get_generator_tag(data)
        elif data.tag == XMLNS_ATOM + 'icon':
            source_tag['icon'] = atom_get_icon_tag(data)
        elif data.tag == XMLNS_ATOM + 'logo':
            source_tag['logo'] = atom_get_logo_tag(data)
        elif data.tag == XMLNS_ATOM + 'rights':
            source_tag['rights'] = atom_get_rights_tag(data)
        elif data.tag == XMLNS_ATOM + 'subtitle':
            source_tag['subtitle'] = atom_get_subtitle_tag(data)
    return source_tag


def atom_get_summary_tag(data):
    summary_optional_attribute = ['type']
    summary_tag = atom_get_common_attribute(data, summary_optional_attribute)
    summary_tag['text'] = data.text
    return summary_tag


class FixedOffset(datetime.tzinfo):

    def __init__(self, offset):
        self.sign = offset[0]
        self.hours = offset[1:3]
        self.minutes = offset[4:6]

    def utcoffset(self, dt):
        if self.sign == '+':
            return datetime.timedelta(hours=int(self.hours),
                                      minutes=int(self.minutes))
        else:
            return datetime.timedelta(hours=int(self.hours)*(-1),
                                      minutes=int(self.minutes)*(-1))

    def dst(self, dt):
        return datetime.timedelta(0)


def atom_date_time(text):
    date_and_time = text[:19]
    second_fraction_and_timezone = re.search('\.?([^\+\-Z]*)(.+)', text[19:])
    datetime_object = datetime.datetime.strptime(date_and_time,
                                                 '%Y-%m-%dT%H:%M:%S')
    if second_fraction_and_timezone.group(1):
        second_fraction = second_fraction_and_timezone.group(1)
        microsecond = int(second_fraction)*pow(10, 6-len(second_fraction))
        datetime_object = datetime_object.replace(microsecond=microsecond)
    if not second_fraction_and_timezone.group(2).startswith('Z'):
        offset = second_fraction_and_timezone.group(2)
        datetime_object = datetime_object.replace(tzinfo=FixedOffset(offset))
    return datetime_object
