try:
    import urlparse
except:
    import urllib.parse as urlparse


def get_tag_attribute(data, attrib_name, xml_base=None):
    iri = ['href', 'src', 'uri']
    if attrib_name in data.attrib:
        if attrib_name in iri:
            return urlparse.urljoin(xml_base, data.attrib[attrib_name])
        return data.attrib[attrib_name]
