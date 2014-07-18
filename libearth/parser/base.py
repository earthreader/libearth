""":mod:`libearth.parser.base` --- Base Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Common interfaces used in both Atom parser and RSS2 parser.

"""
import collections
import copy

__all__ = 'ParserBase', 'SessionBase'


class ParserBase(object):
    """The ParserBase object purposes to define parsers. Defined parsers
    take an XML element, and then return a parsed
    :class:`~libearth.feed.Element` object.
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
        :param session: The additional data which help parsing the element.
        :type root_element: :class:`~libearth.parser.base.SessionBase`

        """
        root, root_session = self.parser(root_element, session)
        for element in root_element:
            try:
                parser, attr_name = self.children_parser[element.tag]
            except Exception:
                # TODO: Logging unexpected element
                continue
            session = copy.copy(root_session)
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
    """The additional data which are needed for parsing the elements.
    For example, an xml:base is needed to retrieve the full uri when an
    relative uri is given in the Atom element.
    A session object is passed from root parser to its children parsers, and
    A change of the session only affects in the parser
    where the change occurs and its children parsers.

    """
    pass
