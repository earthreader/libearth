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
    entry_data = atom_get_entry_data(entries)
    return feed_data


def atom_get_feed_data(root):
    feed_data = {}
    required = ['id', 'title', 'updated']
    multiple = ['author', 'category', 'contributor', 'link']
    for tag in multiple:
        feed_data[tag] = []
    _iter = root.iter() if sys.version_info >= (2, 7) else root.getiterator()
    data = next(_iter)
    while not data.tag == XMLNS_ATOM + 'entry':
        if data.tag == XMLNS_ATOM + 'id':
            feed_data['id'] = atom_common_attribute(data, None)
            feed_data['id']['uri'] = data.text
        elif data.tag == XMLNS_ATOM + 'title':
            title_optional_attrib = [XMLNS_ATOM + 'type']
            feed_data['title'] = atom_common_attribute(data,
                                                       title_optional_attrib)
            feed_data['title']['type'] = data.attrib['type']
            feed_data['title']['text'] = data.text
        elif data.tag == XMLNS_ATOM + 'updated':
            feed_data['updated'] = atom_common_attribute(data, None)
            feed_data['updated']['datetime'] = atom_date_time(data.text)
        data = next(_iter)
    return feed_data


def atom_get_entry_data(entried):
    return


def atom_common_attribute(data, *args):
    common_attribute = {}
    for attrib in data.attrib:
        if attrib == XMLNS_XML + 'base':
            common_attribute['xml:base'] = data.attrib[attrib]
        elif attrib == XMLNS_XML + 'lang':
            common_attribute['xml:lang'] = data.attrib[attrib]
        elif not attrib in args:
            common_attribute[attrib] = data.attrib[attrib]
    return common_attribute


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
