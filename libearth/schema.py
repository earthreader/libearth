""":mod:`libearth.schema` --- Declarative schema for pulling DOM parser of XML
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import weakref
import xml.sax
import xml.sax.handler

__all__ = 'Child', 'DocumeneElement', 'Element'


class Child(object):
    """Declare a possible child element as a descriptor.

    :param tag: the tag name
    :type tag: :class:`str`
    :param element_type: the type of child element(s).
                         it has to be a subtype of :class:`Element`
    :type element_type: :class:`type`
    :param required: whether the child is required or not.
                     it's exclusive to ``multiple``.
                     :const:`False` by default
    :type multiple: :class:`bool`
    :param multiple: whether the child can be multiple.
                     it's exclusive to ``required``.
                     :const:`False` by default
    :type multiple: :class:`bool`

    """

    def __init__(self, tag, element_type, required=False, multiple=False):
        if not isinstance(element_type, type):
            raise TypeError('element_type must be a class, not ' +
                            repr(element_type))
        elif not issubclass(element_type, Element):
            raise TypeError(
                'element_type must be a subtype of {0.__module__}.'
                '{0.__name__}, not {1!r}'.format(Element, element_type)
            )
        elif required and multiple:
            raise TypeError('required and multiple are exclusive')
        self.tag = tag
        self.element_type = element_type
        self.required = bool(required)
        self.multiple = bool(multiple)

    def __get__(self, obj, cls=None):
        if isinstance(obj, Element):
            # FIXME: it should reach the end if self.multiple
            root = obj._root()
            handler = root._handler
            parser = root._parser
            iterable = root._iterable
            while (obj._data.get(self.tag) is None and
                   (not handler.stack or handler.stack[-1])):
                try:
                    parser.feed(next(iterable))
                except StopIteration:
                    break
            return obj._data.get(self.tag)
        return self

    def __set__(self, obj, value):
        if isinstance(value, self.element_type):
            obj._data[self.tag] = value
        else:
            raise AttributeError('cannot change the class attribute')


class Content(object):
    """Declare possible text nodes as a descriptor."""

    def __get__(self, obj, cls=None):
        if isinstance(obj, Element):
            root = obj._root()
            handler = root._handler
            parser = root._parser
            iterable = root._iterable
            while (obj._content is None and
                   (not handler.stack or handler.stack[-1])):
                try:
                    parser.feed(next(iterable))
                except StopIteration:
                    break
            return obj._content or ''
        return self

    def __set__(self, obj, value):
        obj._content = value


class Element(object):

    __slots__ = '_content', '_data', '_parent', '_root'

    def __init__(self, _parent, *args, **kwargs):
        self._content = None
        self._data = {}
        self._parent = weakref.ref(_parent)
        self._root = _parent._root
        assert not kwargs, 'implement sqla-style initializer'


class DocumentElement(Element):

    __slots__ = '_parser', '_iterable', '_handler'

    def __init__(self, *args, **kwargs):
        if kwargs and args:
            raise TypeError('pass keywords only or one iterable')
        elif args and len(args) > 1:
            raise TypeError('takes only one iterable')
        self._root = weakref.ref(self)
        super(DocumentElement, self).__init__(self, **kwargs)
        if args:
            parser = xml.sax.make_parser(['xml.sax.IncrementalParser'])
            self._handler = ContentHandler(self)
            parser.setContentHandler(self._handler)
            self._parser = parser
            self._iterable = iter(args[0])


class ContentHandler(xml.sax.handler.ContentHandler):

    def __init__(self, document):
        self.document = document
        self.stack = []

    def startElement(self, name, attrs):
        try:
            parent_name, parent_element, characters = self.stack[-1]
        except IndexError:
            # document element
            expected = self.document.__tag__
            if name != expected:
                raise SyntaxError('document element must be {0}, '
                                  'not {1}'.format(expected, name))
            self.stack.append((name, self.document, []))
        else:
            element_type = type(parent_element)
            try:
                child = getattr(element_type, name)
            except AttributeError:
                raise SyntaxError('unexpected element: ' + name)
            if isinstance(child, Child):
                child_element = child.element_type(parent_element)
                setattr(parent_element, name, child_element)
                # FIXME: it should append instead if child.multiple
                self.stack.append((name, child_element, []))
            elif isinstance(child, Content):
                raise NotImplementedError()
            else:
                raise SyntaxError('unexpected element: ' + name)

    def characters(self, content):
        name, element, characters = self.stack[-1]
        characters.append(content)

    def endElement(self, name):
        parent_name, parent_element, characters = self.stack.pop()
        assert name == parent_name
        element_type = type(parent_element)
        try:
            attr = element_type.__content__
        except AttributeError:
            for attr in dir(element_type):
                desc = getattr(element_type, attr)
                if isinstance(desc, Content):
                    break
            else:
                attr = None
            element_type.__content__ = attr
        if attr is None:
            return
        setattr(parent_element, attr, ''.join(characters))
