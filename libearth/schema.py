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

.. todo::

   - :class:`Attribute` descriptor
   - Encoder decorator methods
   - Converter
   - Make it possible to write as well

"""
import collections
import weakref
import xml.sax
import xml.sax.handler

from .compat import string_type

__all__ = ('Child', 'Content', 'ContentHandler', 'Descriptor',
           'DocumentElement', 'Element', 'ElementList', 'Text')


class Descriptor(object):
    """Abstract base class for :class:`Child` and :class:`Text`."""

    #: (:class:`str`) The tag name.
    tag = None

    #: (:class:`str`) The optional XML namespace URI.
    xmlns = None

    #: (:class:`tuple`) The pair of (:attr:`xmlns`, :attr:`tag`).
    key_pair = None

    #: (:class:`bool`) Whether it is required for the element.
    #: If it's :const:`True` :attr:`multiple` has to be :const:`False`.
    required = None

    #: (:class:`bool`) Whether it can be zero or more for the element.
    #: If it's :const:`True` :attr:`required` has to be :const:`False`.
    multiple = None

    def __init__(self, tag, xmlns=None, required=False, multiple=False):
        if required and multiple:
            raise TypeError('required and multiple are exclusive')
        self.tag = tag
        self.xmlns = xmlns
        self.key_pair = self.xmlns, self.tag
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
            while (obj._data.get(self.key_pair) is None and
                   (not stack or stack[-1])):
                try:
                    chunk = next(iterable)
                except StopIteration:
                    break
                parser.feed(chunk)
            return obj._data.get(self.key_pair)
        return self

    def start_element(self, element, attribute):
        """Abstract method that is invoked when the parser meets a start
        of an element related to the descriptor.  It will be called by
        :class:`ContentHandler`.

        :param element: the parent element of the read element
        :type element: :class:`Element`
        :param attribute: the attribute name of the descriptor
        :type attribute: :class:`str`
        :returns: a value to reserve.  it will be passed to
                  ``reserved_value`` parameter of :meth:`end_element()`

        """
        raise NotImplementedError(
            'start_element() method has to be implemented'
        )

    def end_element(self, reserved_value, content):
        """Abstract method that is invoked when the parser meets an end
        of an element related to the descriptor.  It will be called by
        :class:`ContentHandler`.

        :param reserved_value: the value :meth:`start_element()` method
                               returned
        :param content: the content text of the read element
        :type content: :class:`str`

        """
        raise NotImplementedError('end_element() method has to be implemented')


class Child(Descriptor):
    """Declare a possible child element as a descriptor.

    :param tag: the tag name
    :type tag: :class:`str`
    :param xmlns: an optional XML namespace URI
    :type xmlns: :class:`str`
    :param element_type: the type of child element(s).
                         it has to be a subtype of :class:`Element`
    :type element_type: :class:`type`
    :param required: whether the child is required or not.
                     it's exclusive to ``multiple``.
                     :const:`False` by default
    :type required: :class:`bool`
    :param multiple: whether the child can be multiple.
                     it's exclusive to ``required``.
                     :const:`False` by default
    :type multiple: :class:`bool`

    """

    def __init__(self, tag, element_type, xmlns=None, required=False,
                 multiple=False):
        if not isinstance(element_type, type):
            raise TypeError('element_type must be a class, not ' +
                            repr(element_type))
        elif not issubclass(element_type, Element):
            raise TypeError(
                'element_type must be a subtype of {0.__module__}.'
                '{0.__name__}, not {1!r}'.format(Element, element_type)
            )
        super(Child, self).__init__(
            tag,
            xmlns=xmlns,
            required=required,
            multiple=multiple
        )
        self.element_type = element_type

    def __set__(self, obj, value):
        if isinstance(obj, Element):
            if self.multiple:
                if isinstance(value, collections.Sequence):
                    if (len(value) < 1 or
                        isinstance(value[0], self.element_type)):
                        obj._data[self.key_pair] = value
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
                    obj._data[self.key_pair] = value
                else:
                    raise TypeError(
                        'expected an instance of {0.__module__}.{0.__name__}, '
                        'not {1!r}'.format(self.element_type, value)
                    )
        else:
            raise AttributeError('cannot change the class attribute')

    def start_element(self, element, attribute):
        child_element = self.element_type(element)
        if self.multiple:
            element_list = element._data.setdefault(self.key_pair, [])
            element_list.append(child_element)
        else:
            setattr(element, attribute, child_element)
        return child_element

    def end_element(self, reserved_value, content):
        element_type = type(reserved_value)
        attr = reserved_value._root()._handler.get_content_tag(element_type)
        if attr is None:
            return
        setattr(reserved_value, attr, content)


# Semi-structured record type for only internal use.
CodecFunction = collections.namedtuple('CodecFunction', 'function descriptor')


class Text(Descriptor):
    """Descriptor that declares a possible child element that only cosists
    of character data.  All other attributes and child nodes are ignored.

    :param tag: the tag name
    :type tag: :class:`str`
    :param xmlns: an optional XML namespace URI
    :type xmlns: :class:`str`
    :param required: whether the child is required or not.
                     it's exclusive to ``multiple``.
                     :const:`False` by default
    :type required: :class:`bool`
    :param multiple: whether the child can be multiple.
                     it's exclusive to ``required``.
                     :const:`False` by default
    :type multiple: :class:`bool`
    :param decoder: an optional function that decodes XML text value into
                    Python value e.g. :func:`int()`.  the decoder function
                    has to take an argument
    :type decoder: :class:`collections.Callable`

    """

    def __init__(self, tag, xmlns=None, required=False, multiple=False,
                 decoder=None):
        super(Text, self).__init__(
            tag,
            xmlns=xmlns,
            required=required,
            multiple=multiple
        )
        self.decoders = []
        if decoder is not None:
            if not callable(decoder):
                raise TypeError('decoder must be callable, not ' +
                                repr(decoder))
            self.decoders.append(CodecFunction(decoder, descriptor=False))

    def decoder(self, function):
        r"""Decorator which sets the decoder to the decorated function::

            import datetime

            class Person(DocumentElement):
                '''Person.dob will be a datetime.date instance.'''

                __tag__ = 'person'
                dob = Text('dob')

                @dob.decoder
                def dob(self, dob_text):
                    return datetime.date.strptime(dob_text, '%Y-%m-%d')

        >>> p = Person('<person><dob>1987-07-26</dob></person>')
        >>> p.dob
        datetime.date(1987, 7, 26)

        If it's applied multiple times, all decorated functions are piped
        in the order::

            class Person(Element):
                '''Person.age will be an integer.'''

                age = Text('dob', decoder=lambda text: text.strip())

                @age.decoder
                def age(self, dob_text):
                    return datetime.date.strptime(dob_text, '%Y-%m-%d')

                @age.decoder
                def age(self, dob):
                    now = datetime.date.today()
                    d = now.month < dob.month or (now.month == dob.month and
                                                  now.day < dob.day)
                    return now.year - dob.year - d

        >>> p = Person('<person>\n\t<dob>\n\t\t1987-07-26\n\t</dob>\n</person>')
        >>> p.age
        26
        >>> datetime.date.today()
        datetime.date(2013, 7, 30)

        .. note::

           This creates a copy of the descriptor instance rather than
           manipulate itself in-place.

        """
        desc = Text(
            self.tag,
            xmlns=self.xmlns,
            required=self.required,
            multiple=self.multiple
        )
        desc.decoders.extend(self.decoders)
        desc.decoders.append(CodecFunction(function, descriptor=True))
        return desc

    def start_element(self, element, attribute):
        return element

    def end_element(self, reserved_value, content):
        for decoder in self.decoders:
            if decoder.descriptor and hasattr(decoder.function, '__get__'):
                content = decoder.function.__get__(reserved_value)(content)
            else:
                content = decoder.function(content)
        key = self.key_pair
        if self.multiple:
            reserved_value._data.setdefault(key, []).append(content)
        else:
            reserved_value._data[key] = content


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

    #: (:class:`str`) Every :class:`DocumentElement` subtype has to define
    #: this attribute to the root tag name.
    __tag__ = NotImplemented

    #: (:class:`str`) A :class:`DocumentElement` subtype may define this
    #: attribute to the XML namespace of the document element.
    __xmlns__ = None

    def __init__(self, *args, **kwargs):
        cls = type(self)
        if cls.__tag__ is NotImplemented:
            raise NotImplementedError(
                '{0.__module__}.{0.__name__}.__tag__ is not defined; '
                'every subtype of {1.__module__}.{1.__name__} has to '
                'define __tag__ attribute'.format(cls, DocumentElement)
            )
        elif not isinstance(cls.__tag__, string_type):
            raise TypeError(
                '__tag__ has to be a string, not ' + repr(cls.__tag__)
            )
        if kwargs and args:
            raise TypeError('pass keywords only or one iterable')
        elif args and len(args) > 1:
            raise TypeError('takes only one iterable')
        self._root = weakref.ref(self)
        if args:
            parser = xml.sax.make_parser()
            handler = ContentHandler(self)
            self._handler = handler
            parser.setContentHandler(self._handler)
            parser.setFeature(xml.sax.handler.feature_namespaces, True)
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

    __slots__ = 'element', 'descriptor', 'tag', 'xmlns', 'key_pair'

    def __init__(self, element, descriptor):
        if not isinstance(element, Element):
            raise TypeError(
                'element must be an instance of {0.__module__}.{0.__name__}, '
                'not {1!r}'.format(Element, element)
            )
        elif not isinstance(descriptor, Descriptor):
            raise TypeError(
                'descriptor must be an instance of {0.__module__}.{0.__name__}'
                ', not {1!r}'.format(Descriptor, descriptor)
            )
        self.element = weakref.ref(element)
        self.descriptor = descriptor
        self.tag = descriptor.tag
        self.xmlns = descriptor.xmlns
        self.key_pair = descriptor.key_pair

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
        return len(stack) < top or stack[top - 1].reserved_value is not parent

    def __len__(self):
        for data in self.consume_buffer():
            continue
        try:
            lst = data[self.key_pair]
        except KeyError:
            return 0
        return len(lst)

    def __getitem__(self, index):
        key = self.key_pair
        for data in self.consume_buffer():
            if key in data and len(data[key]) > index:
                break
        return data[key][index]

    def __repr__(self):
        list_repr = repr(self.element()._data.get(self.key_pair, []))
        if not self.consumes_all():
            list_repr = list_repr[:-1] + '...]'
        return '<{0.__module__}.{0.__name__} {1}>'.format(
            type(self), list_repr
        )


# Semi-structured record type for only internal use.
ParserContext = collections.namedtuple(
    'ParserContext',
    'tag xmlns descriptor reserved_value content_buffer'
)


class ContentHandler(xml.sax.handler.ContentHandler):
    """Event handler implementation for SAX parser.

    It maintains the stack that contains parsing contexts of
    what element is lastly open, what descriptor is associated
    to the element, and the buffer for chunks of content characters
    the element has.  Every context is represented as the namedtuple
    :class:`ParserContext`.

    Each time its events (:meth:`startElement()`, :meth:`characters()`,
    and :meth:`endElement()`) are called, it forwards the data to
    the associated descriptor.  :class:`Descriptor` subtypes
    implement :meth:`~Descriptor.start_element()` method and
    :meth:`~Descriptor.end_element()`.

    """

    def __init__(self, document):
        self.document = document
        self.stack = []

    def startElementNS(self, tag, qname, attrs):
        xmlns, name = tag
        try:
            parent_context = self.stack[-1]
        except IndexError:
            # document element
            expected = (getattr(self.document, '__xmlns__', None),
                        self.document.__tag__)
            if tag != expected:
                raise SyntaxError('document element must be {0}, '
                                  'not {1}'.format(expected, name))
            self.stack.append(
                ParserContext(
                    tag=name,
                    xmlns=xmlns,
                    descriptor=None,
                    reserved_value=self.document,
                    content_buffer=[]
                )
            )
        else:
            parent_element = parent_context.reserved_value
            element_type = type(parent_element)
            child_tags = self.get_child_tags(element_type)
            try:
                attr, child = child_tags[tag]
            except KeyError:
                if xmlns:
                    raise SyntaxError('unexpected element: {0} (namespace: '
                                      '{1})'.format(name, xmlns))
                raise SyntaxError('unexpected element: ' + name)
            if isinstance(child, Descriptor):
                reserved_value = child.start_element(parent_element, attr)
                self.stack.append(
                    ParserContext(
                        tag=name,
                        xmlns=xmlns,
                        descriptor=child,
                        reserved_value=reserved_value,
                        content_buffer=[]
                    )
                )
            else:
                if xmlns:
                    raise SyntaxError('unexpected element: {0} (namespace: '
                                      '{1})'.format(name, xmlns))
                raise SyntaxError('unexpected element: ' + name)

    def characters(self, content):
        context = self.stack[-1]
        context.content_buffer.append(content)

    def endElementNS(self, tag, qname):
        xmlns, name = tag
        context = self.stack.pop()
        assert name == context.tag
        assert xmlns == context.xmlns
        text = ''.join(context.content_buffer)
        if context.descriptor is None:
            # context.reserved_value is root document
            attr = self.get_content_tag(type(context.reserved_value))
            if attr is not None:
                setattr(context.reserved_value, attr, text)
        else:
            context.descriptor.end_element(context.reserved_value, text)

    def index_descriptors(self, element_type):
        child_tags = {}
        content = None
        for attr in dir(element_type):
            desc = getattr(element_type, attr)
            if isinstance(desc, Content):
                content = attr, desc
            elif isinstance(desc, Descriptor):
                child_tags[desc.xmlns, desc.tag] = attr, desc
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
