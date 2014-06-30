""":mod:`libearth.parser.base` --- Base Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Common interfaces used in both Atom parser and RSS2 parser.

"""
import copy


#: (:class:`str`) The XML namespace for the predefined ``xml:`` prefix.
XML_XMLNS = 'http://www.w3.org/XML/1998/namespace'


def get_element_id(name_space, element_name):
    return '{' + name_space + '}' + element_name


def get_xml_base(data, default):
    if get_element_id(XML_XMLNS, 'base') in data.attrib:
        return data.attrib['{' + XML_XMLNS + '}base']
    else:
        return default


class ParserBase(object):

    def __init__(self, parser=None):
        if parser:
            self.parser = parser
        self.children_parser = {}

    def __call__(self, root_element, session):
        root, root_session = self.parser(root_element, session)
        for element_name, (parser, attr_name) \
                in self.children_parser.items():
            elements = root_element.findall(
                get_element_id(session.element_ns, element_name))
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
            if isinstance(func, ParserBase):
                func = func.parser
            parser = ParserBase(func)
            self.children_parser[element_name] = (parser,
                                                  attr_name or element_name)
            return parser

        return decorator


class SessionBase(object):

    element_ns = None
    xml_base = None

    def __init__(self, element_ns, xml_base):
        self.element_ns = element_ns
        self.xml_base = xml_base
