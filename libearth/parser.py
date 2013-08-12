""":mod:`libearth.parser` --- Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

import re
import sys
try:
    from lxml import etree
except ImportError:
    try:
        from xml.etree import cElementTree as etree
    except ImportError:
        from xml.etree import ElementTree as etree


class ParserError(TypeError):
    """Error which rises when feed data are logically wrong."""


class RequiredDuplicatedError(ParserError, AttributeError):
    """Error which rieses when a tag which has to be only one defined
    twice"""

ATOM_XMLNS = 'http://www.w3.org/2005/Atom'
ATOM_XMLNS_TAG = '{http://www.w3.org/2005/Atom}'
XMLNS_XML_TAG = "{http://www.w3.org/XML/1998/namespace}"


def parse_atom(xml):
    root = etree.fromstring(xml)
    entries = root.findall(ATOM_XMLNS_TAG + 'entry')
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
    while not data.tag == ATOM_XMLNS_TAG + 'entry':
        if data.tag == ATOM_XMLNS_TAG + 'id':
            if 'id' in feed_data:
                raise RequiredDuplicatedError(
                    'required tag duplicated')
            feed_data['id'] = atom_common_attribute(data, None)
            feed_data['id']['uri'] = data.text
        data = next(_iter)
    return feed_data


def atom_get_entry_data(entried):
    return


def atom_common_attribute(data, *args):
    common_attribute = {}
    for attrib in data.attrib:
        if attrib == XMLNS_XML_TAG + 'base':
            common_attribute['xml:base'] = data.attrib[attrib]
        elif attrib == XMLNS_XML_TAG + 'lang':
            common_attribute['xml:lang'] = data.attrib[attrib]
        elif not attrib in args:
            kcommon_attribute[attrib] = data.attrib[attrib]
    return common_attribute
