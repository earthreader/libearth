""":mod:`libearth.parser.base` --- Base Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Common interfaces used in both Atom parser and RSS2 parser.

"""
import collections
import copy

__all__ = 'ParserBase', 'XML_XMLNS', 'get_element_id', 'get_xml_base'


#: (:class:`str`) The XML namespace for the predefined ``xml:`` prefix.
XML_XMLNS = 'http://www.w3.org/XML/1998/namespace'


def get_element_id(name_space, element_name):
    """Returns combined string of the name_space and element_name.
    The return value is `'{namespace}element_name'`
    """
    if name_space:
        return '{' + name_space + '}' + element_name
    else:
        return element_name


def get_xml_base(data, default):
    """Extract the xml:base in the element.
    If the element does not have xml:base, it returns the default value.
    """
    if get_element_id(XML_XMLNS, 'base') in data.attrib:
        return data.attrib['{' + XML_XMLNS + '}base']
    else:
        return default


class ParserBase(object):
    """The ParserBase object purposes to define parsers. Defined parsers
    take an XML element, and then return a parsed :class:`~libearth.feed.Feed`
    object.
    Every parser is defined together with a path(e.g. ``'channel/item'``) of
    elements to take through :meth:`path()` decorator.

    Every decorated function becomes to a *child* parser of the parser that
    decorats it.  ::

        rss2_parser = Parser()

        @rss2_parser.path('channel')
        def channel_parser(element, session):
            # ...

        @channel_parser.path('item')
        def item_parser(element, session):
            # ...

    """

    def __init__(self, parser=None):
        if parser:
            self.parser = parser
        self.children_parser = {}

    def __call__(self, root_element, session):
        """The parsing starts when a root parser is called.
        When parsing, the root parser parses an element designated to itself and
        it passes the children elements to the children parsers.

        :param root_element: An XML element to be parsed.
        :type root_element: :class:`xml.etree.ElementTree.Element`
        :param session: The data needed for parsing in the hierarchical order.
                        For example, an ATOM_XMLNS and a xml:base is needed to
                        parse an Atom element and its children. A change of the
                        session only affects in the parser where the change
                        occurs and its children.

        """
        root, root_session = self.parser(root_element, session)
        for element_id, (parser, attr_name) \
                in self.children_parser.items():
            elements = root_element.findall(element_id)
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

    def path(self, element_name, namespace_set=None, attr_name=None):
        """The decorator function to define a parser in the top of
        parser hierarchy or its children parsers.

        :param element_name: The element id. It consists of an xml namespace and
                             an element name. The parser should return a
                             :class: `~libearth.feed.Element` matches it.
        :type element_name: :class:`str`
        :param attr_name: The descriptor attribute name of the parent
                          :class: `~libearth.feed.Element` for the designated
                          `Element`

        """

        def decorator(func):
            if isinstance(func, ParserBase):
                func = func.parser
            parser = ParserBase(func)
            if isinstance(namespace_set, collections.Iterable):
                for namespace in namespace_set:
                    self.children_parser[get_element_id(namespace,
                                                        element_name)] = \
                        parser, attr_name or element_name
            else:
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
