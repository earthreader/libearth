""":mod:`libearth.schema` --- Declarative schema for pulling DOM parser of XML
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are well-known two ways to parse XML:

Document Object Model
   It reads the whole XML and then makes a tree in memory.  You can easily
   treverse the document as a tree, but the parsing can't be streamed.
   Moreover it uses memory for data you don't use.

Simple API for XML
   It's an event-based sequential access parser.  It means you need to
   listen events from it and then utilize its still unstructured data
   by yourself.  In other words, you don't need to pay memory to data
   you never use if you simply do nothing for them when you listen
   the event.

Pros and cons between these two ways are obvious, but there could be
another way to parse XML: *mix them*.

The basic idea of this pulling DOM parser (which this module implements)
is that the parser can consume the stream just in time when you actually
reach the child node.  There should be an assumption for that: parsed XML
has a schema for it.  If the document is schema-free, this heuristic approach
loses the most of its efficiency.

So the parser should have the information about the schema of XML document
it'd parser, and we can declare the schema by defining classes.  It's a thing
like ORM for XML.  For example, suppose there is a small XML document:

.. code-block:: xml

   <?xml version="1.0"?>
   <person>
     <name>Hong Minhee</name>
     <url>http://dahlia.kr/</url>
     <url>https://github.com/dahlia</url>
     <url>https://bitbucket.org/dahlia</url>
     <dob>1988-08-04</dob>
   </person>

You can declare the schema for this like the following class definition::

    class Person(DocumentElement):
        __tag__ = 'person'
        name = Text('name')
        url = Child('url', URL, multiple=True)
        dob = Child('dob', Date)

"""
import collections
import weakref
import xml.sax
import xml.sax.handler

__all__ = ('Child', 'Content', 'ContentHandler', 'Descriptor',
           'DocumeneElement', 'Element', 'ElementList', 'Text')


class Descriptor(object):
    """Base class for :class:`Child` and :class:`Text`."""

    #: (:class:`str`) The tag name.
    tag = None

    #: (:class:`bool`) Whether it is required for the element.
    #: If it's :const:`True` :attr:`multiple` has to be :const:`False`.
    required = None

    #: (:class:`bool`) Whether it can be zero or more for the element.
    #: If it's :const:`True` :attr:`required` has to be :const:`False`.
    multiple = None

    def __init__(self, tag, required=False, multiple=False):
        if required and multiple:
            raise TypeError('required and multiple are exclusive')
        self.tag = tag
        self.required = bool(required)
        self.multiple = bool(multiple)

    def __get__(self, obj, cls=None):
        if isinstance(obj, Element):
            if self.multiple:
                return ElementList(obj, self)
            root = obj._root()
            handler = root._handler
            parser = root._parser
            iterable = root._iterator
            stack = handler.stack
            while (obj._data.get(self.tag) is None and
                   (not stack or stack[-1])):
                try:
                    chunk = next(iterable)
                except StopIteration:
                    break
                parser.feed(chunk)
            return obj._data.get(self.tag)
        return self


class Child(Descriptor):
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
        super(Child, self).__init__(tag, required=required, multiple=multiple)
        self.element_type = element_type

    def __set__(self, obj, value):
        if isinstance(obj, Element):
            if self.multiple:
                if isinstance(value, collections.Sequence):
                    if (len(value) < 1 or
                        isinstance(value[0], self.element_type)):
                        obj._data[self.tag] = value
                    else:
                        raise TypeError(
                            'expected a sequence of {0.__module__}.'
                            '{0.__name__}, not {1!r}'.format(
                                self.element_type, value
                            )
                        )
                else:
                    raise TypeError('Child property of multiple=True option '
                                    'only accepts a sequence, not ' +
                                    repr(value))
            else:
                if isinstance(value, self.element_type):
                    obj._data[self.tag] = value
                else:
                    raise TypeError(
                        'expected an instance of {0.__module__}.{0.__name__}, '
                        'not {1!r}'.format(self.element_type, value)
                    )
        else:
            raise AttributeError('cannot change the class attribute')


class Text(Descriptor):

    pass


class Content(object):
    """Declare possible text nodes as a descriptor."""

    def __get__(self, obj, cls=None):
        if isinstance(obj, Element):
            root = obj._root()
            handler = root._handler
            parser = root._parser
            iterable = root._iterator
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
    """Represent an element in XML document."""

    __slots__ = '_content', '_data', '_parent', '_root'

    def __init__(self, _parent, *args, **kwargs):
        self._content = None
        self._data = {}
        self._parent = weakref.ref(_parent)
        self._root = _parent._root
        self._stack_top = len(self._root()._handler.stack)
        assert not kwargs, 'implement sqla-style initializer'  # TODO


class DocumentElement(Element):
    """The root element of the document."""

    __slots__ = '_parser', '_iterator', '_handler'

    def __init__(self, *args, **kwargs):
        if kwargs and args:
            raise TypeError('pass keywords only or one iterable')
        elif args and len(args) > 1:
            raise TypeError('takes only one iterable')
        self._root = weakref.ref(self)
        if args:
            parser = xml.sax.make_parser(['xml.sax.IncrementalParser'])
            handler = ContentHandler(self)
            self._handler = handler
            parser.setContentHandler(self._handler)
            self._parser = parser
            iterator = iter(args[0])
            self._iterator = iterator
            stack = handler.stack
            while not stack:
                try:
                    chunk = next(iterator)
                except StopIteration:
                    break
                parser.feed(chunk)
        super(DocumentElement, self).__init__(self, **kwargs)


class ElementList(collections.Sequence):
    """List-like object to represent multiple chidren.  It makes the parser
    to lazily consume the buffer when an element of a particular offset
    is requested.

    """

    def __init__(self, element, descriptor):
        if not isinstance(element, Element):
            raise TypeError(
                'element must be an instance of {0.__module__}.{0.__name__}, '
                'not {1!r}'.format(Element, element)
            )
        elif not isinstance(descriptor, Descriptor):
            raise TypeError(
                'descriptor must be an instance of {0.__module__}.{0.__name__}'
                ', not {1!r}'.format(Child, descriptor)
            )
        self.element = weakref.ref(element)
        self.descriptor = descriptor
        self.tag = descriptor.tag

    def consume_buffer(self):
        """Consume the buffer for the parser.  It returns a generator,
        so can be stopped using :keyword:`break` statement by caller.

        .. note::

           Internal method.

        """
        element = self.element()
        root = element._root()
        parser = root._parser
        iterable = root._iterator
        data = element._data
        while not self.consumes_all():
            yield data
            try:
                chunk = next(iterable)
            except StopIteration:
                break
            parser.feed(chunk)
        yield data

    def consumes_all(self):
        element = self.element()
        parent = element._parent()
        root = element._root()
        handler = root._handler
        stack = handler.stack
        top = element._stack_top
        #return not (len(stack) >= top and stack[top - 1][2] is parent)
        return len(stack) < top or stack[top - 1][2] is not parent

    def __len__(self):
        for data in self.consume_buffer():
            continue
        try:
            lst = data[self.tag]
        except KeyError:
            return 0
        return len(lst)

    def __getitem__(self, index):
        for data in self.consume_buffer():
            if self.tag in data and len(data[self.tag]) > index:
                break
        return data[self.tag][index]

    def __repr__(self):
        list_repr = repr(self.element()._data.get(self.tag, []))
        if not self.consumes_all():
            list_repr = list_repr[:-1] + '...]'
        return '<{0.__module__}.{0.__name__} {1}>'.format(
            type(self), list_repr
        )


class ContentHandler(xml.sax.handler.ContentHandler):
    """Event handler implementation for SAX parser."""

    def __init__(self, document):
        self.document = document
        self.stack = []

    def startElement(self, name, attrs):
        try:
            (parent_name, parent_descriptor, parent_element,
             characters) = self.stack[-1]
        except IndexError:
            # document element
            expected = self.document.__tag__
            if name != expected:
                raise SyntaxError('document element must be {0}, '
                                  'not {1}'.format(expected, name))
            self.stack.append((name, None, self.document, []))
        else:
            element_type = type(parent_element)
            child_tags = self.get_child_tags(element_type)
            try:
                attr, child = child_tags[name]
            except KeyError:
                raise SyntaxError('unexpected element: ' + name)
            if isinstance(child, Child):
                child_element = child.element_type(parent_element)
                if child.multiple:
                    element_list = parent_element._data.setdefault(name, [])
                    element_list.append(child_element)
                else:
                    setattr(parent_element, attr, child_element)
                self.stack.append((name, child, child_element, []))
            elif isinstance(child, Text):
                self.stack.append((name, child, parent_element, [])) # FIXME
            else:
                raise SyntaxError('unexpected element: ' + name)

    def characters(self, content):
        name, descriptor, element, characters = self.stack[-1]
        characters.append(content)

    def endElement(self, name):
        parent_name, descriptor, parent_element, characters = self.stack.pop()
        assert name == parent_name
        text = ''.join(characters)
        if isinstance(descriptor, Text):
            if descriptor.multiple:
                parent_element._data.setdefault(descriptor.tag, []).append(text)
            else:
                parent_element._data[descriptor.tag] = text
        else:
            element_type = type(parent_element)
            attr = self.get_content_tag(element_type)
            if attr is None:
                return
            setattr(parent_element, attr, text)

    def index_descriptors(self, element_type):
        child_tags = {}
        content = None
        for attr in dir(element_type):
            desc = getattr(element_type, attr)
            if isinstance(desc, Content):
                content = attr, desc
            elif isinstance(desc, Descriptor):
                child_tags[desc.tag] = attr, desc
        element_type.__child_tags__ = child_tags
        element_type.__content__ = content

    def get_child_tags(self, element_type):
        try:
            child_tags = element_type.__child_tags__
        except AttributeError:
            self.index_descriptors(element_type)
            child_tags = element_type.__child_tags__
        return child_tags

    def get_content_tag(self, element_type):
        try:
            content = element_type.__content__
        except AttributeError:
            self.index_descriptors(element_type)
            content = element_type.__content__
        return content and content[0]
