""":mod:`libearth.parser.common` --- Common functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Common functions used in rss2 and atom module.

"""


try:
    import urlparse
except:
    import urllib.parse as urlparse


def get_tag_attribute(data, attrib_name, xml_base=None):
    """Parse attribute in tag and return.

    :param data: tag data
    :type data: :class:`etree.Element`
    :param attrib_name: attribute name to parse
    :type attrib_name: :class:`str`
    :returns: attribute data
    :rtype: :class:`str`

    """

    iri = ['href', 'src', 'uri']
    if attrib_name in data.attrib:
        if attrib_name in iri:
            return urlparse.urljoin(xml_base, data.attrib[attrib_name])
        return data.attrib[attrib_name]
