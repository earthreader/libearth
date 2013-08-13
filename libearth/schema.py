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
   <person version="1.0">
     <name>Hong Minhee</name>
     <url>http://dahlia.kr/</url>
     <url>https://github.com/dahlia</url>
     <url>https://bitbucket.org/dahlia</url>
     <dob>1988-08-04</dob>
   </person>

You can declare the schema for this like the following class definition::

    class Person(DocumentElement):
        __tag__ = 'person'
        format_version = Attribute('version')
        name = Text('name')
        url = Child('url', URL, multiple=True)
        dob = Child('dob', Date)

.. todo::

   - Codec
   - Syntax error
   - :func:`write()` should be aware of :attr:`Descriptor.required`

"""
import collections
import copy
import itertools
import operator
import weakref
import xml.sax
import xml.sax.handler
import xml.sax.saxutils

from .compat import UNICODE_BY_DEFAULT, string_type, text_type

__all__ = ('Attribute', 'Child', 'CodecDescriptor', 'Content',
           'ContentHandler', 'Descriptor', 'DescriptorConflictError',
           'DocumentElement', 'Element', 'ElementList', 'SchemaError', 'Text',
           'read', 'index_descriptors', 'inspect_attributes',
           'inspect_child_tags', 'inspect_content_tag', 'inspect_xmlns_set',
           'write')


class SchemaError(TypeError):
    """Error which rises when a schema definition has logical errors."""


class DescriptorConflictError(SchemaError, AttributeError):
    """Error which rises when a schema has duplicate descriptors more than
    one for the same attribute, the same child element, or the text node.

    """


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
            if getattr(root, '_handler', None):
                handler = root._handler
                parser = root._parser
                iterable = root._iterator
                stack = handler.stack
                while ((obj._data.get(self) is None and
                       (not stack or stack[-1]))):
                    try:
                        chunk = next(iterable)
                    except StopIteration:
                        break
                    parser.feed(chunk)
            return obj._data.get(self)
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

    .. todo::

       It crashes when the document has any non-ASCII characters.

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
                    if len(value) < 1 or \
                       isinstance(value[0], self.element_type):
                        obj._data[self] = value
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
                    obj._data[self] = value
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
            element_list = element._data.setdefault(self, [])
            element_list.append(child_element)
        else:
            setattr(element, attribute, child_element)
        return child_element

    def end_element(self, reserved_value, content):
        element_type = type(reserved_value)
        attr = inspect_content_tag(element_type)
        if attr is None:
            return
        content_desc = attr[1]
        content_desc.read(reserved_value, content)


# Semi-structured record type for only internal use.
CodecFunction = collections.namedtuple('CodecFunction', 'function descriptor')


class CodecDescriptor(object):
    """Mixin class for descriptors that provide :meth:`decoder` and
    :meth:`encoder`.

    :class:`Attribute`, :class:`Content` and :class:`Text` can take
    ``encoder`` and ``decoder`` functions for them.  It's used for encoding
    from Python values to XML string and decoding raw values from XML to
    natural Python representations.

    Encoders can be specified using ``encoder`` parameter of descriptor's
    constructor, or :meth:`encoder()` decorator.

    Decoders can be specified using ``decoder`` parameter of descriptor's
    constructor, or :meth:`decoder()` decorator::

        class Person(DocumentElement):
            __tag__ = 'person'
            format_version = Attribute('version')
            name = Text('name')
            url = Child('url', URL, multiple=True)
            dob = Text('dob',
                       encoder=datetime.date.strftime.isoformat,
                       decoder=lambda s: datetime.date.strptime(s, '%Y-%m-%d'))

            @format_version.encoder
            def format_version(self, value):
                return '.'.join(map(str, value))

            @format_version.decoder
            def format_version(self, value):
                return tuple(map(int, value.split('.')))

    :param encoder: an optional function that encodes Python value into
                    XML text value e.g. :func:`str()`.  the encoder function
                    has to take an argument
    :type encoder: :class:`collections.Callable`
    :param decoder: an optional function that decodes XML text value into
                    Python value e.g. :func:`int()`.  the decoder function
                    has to take a string argument
    :type decoder: :class:`collections.Callable`

    """

    def __init__(self, encoder=None, decoder=None):
        self.encoders = []
        self.decoders = []
        if encoder is not None:
            if not callable(encoder):
                raise TypeError('encoder must be callable, not ' +
                                repr(encoder))
            self.encoders.append(CodecFunction(encoder, descriptor=False))
        if decoder is not None:
            if not callable(decoder):
                raise TypeError('decoder must be callable, not ' +
                                repr(decoder))
            self.decoders.append(CodecFunction(decoder, descriptor=False))

    def encoder(self, function):
        r"""Decorator which sets the encoder to the decorated function::

            import datetime

            class Person(DocumentElement):
                '''Person.dob will be written to ISO 8601 format'''

                __tag__ = 'person'
                dob = Text('dob')

                @dob.encoder
                def dob(self, dob):
                    if not isinstance(dob, datetime.date):
                        raise TypeError('expected datetime.date')
                    return dob.strftime('%Y-%m-%d')

        >>> isinstance(p, Person)
        True
        >>> p.dob
        datetime.date(1987, 7, 26)
        >>> ''.join(write(p, indent='', newline=''))
        '<person><dob>1987-07-26</dob></person>'

        If it's applied multiple times, all decorated functions are piped
        in the order::

            class Person(Element):
                '''Person.email will have mailto: prefix when it's written
                to XML.

                '''

                email = Text('email', encoder=lambda email: 'mailto:' + email)

                @age.encoder
                def email(self, email):
                    return email.strip()

                @email.encoder
                def email(self, email):
                    login, host = email.split('@', 1)
                    return login + '@' + host.lower()

        >>> isinstance(p, Person)
        True
        >>> p.email
        '  earthreader@librelist.com  '
        >>> ''.join(write(p, indent='', newline=''))
        >>> '<person><email>mailto:earthreader@librelist.com</email></person>')

        .. note::

           This creates a copy of the descriptor instance rather than
           manipulate itself in-place.

        """
        desc = copy.copy(self)
        desc.encoders = self.encoders[:]
        desc.encoders.append(CodecFunction(function, descriptor=True))
        return desc

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
        desc = copy.copy(self)
        desc.decoders = self.decoders[:]
        desc.decoders.append(CodecFunction(function, descriptor=True))
        return desc

    def encode(self, value, instance):
        for encoder in self.encoders:
            if encoder.descriptor and hasattr(encoder.function, '__get__'):
                value = encoder.function.__get__(instance)(value)
            else:
                value = encoder.function(value)
        return value

    def decode(self, text, instance):
        """Decode the given ``text`` as it's programmed.

        :param text: the raw text to decode.  xml attribute value or
                     text node value in most cases
        :type text: :class:`str`
        :param instance: the instance that is associated with the descriptor
        :type instance: :class:`Element`
        :returns: decoded value

        .. note::

           Internal method.

        """
        for decoder in self.decoders:
            if decoder.descriptor and hasattr(decoder.function, '__get__'):
                text = decoder.function.__get__(instance)(text)
            else:
                text = decoder.function(text)
        return text


class Text(Descriptor, CodecDescriptor):
    """Descriptor that declares a possible child element that only cosists
    of character data.  All other attributes and child nodes are ignored.

    :param tag: the XML tag name
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
    :param encoder: an optional function that encodes Python value into
                    XML text value e.g. :func:`str()`.  the encoder function
                    has to take an argument
    :type encoder: :class:`collections.Callable`
    :param decoder: an optional function that decodes XML text value into
                    Python value e.g. :func:`int()`.  the decoder function
                    has to take a string argument
    :type decoder: :class:`collections.Callable`

    """

    def __init__(self, tag, xmlns=None, required=False, multiple=False,
                 encoder=None, decoder=None):
        Descriptor.__init__(self, tag,
                            xmlns=xmlns, required=required, multiple=multiple)
        CodecDescriptor.__init__(self, encoder=encoder, decoder=decoder)

    def start_element(self, element, attribute):
        return element

    def end_element(self, reserved_value, content):
        content = self.decode(content, reserved_value)
        if self.multiple:
            reserved_value._data.setdefault(self, []).append(content)
        else:
            reserved_value._data[self] = content


class Attribute(CodecDescriptor):
    """Declare possible element attributes as a descriptor.

    :param name: the XML attribute name
    :type name: :class:`str`
    :param xmlns: an optional XML namespace URI
    :type xmlns: :class:`str`
    :param required: whether the child is required or not.
                     :const:`False` by default
    :type required: :class:`bool`
    :param encoder: an optional function that encodes Python value into
                    XML text value e.g. :func:`str()`.  the encoder function
                    has to take an argument
    :type encoder: :class:`collections.Callable`
    :param decoder: an optional function that decodes XML text value into
                    Python value e.g. :func:`int()`.  the decoder function
                    has to take a string argument
    :type decoder: :class:`collections.Callable`

    """

    #: (:class:`str`) The XML attribute name.
    name = None

    #: (:class:`str`) The optional XML namespace URI.
    xmlns = None

    #: (:class:`tuple`) The pair of (:attr:`xmlns`, :attr:`name`).
    key_pair = None

    #: (:class:`bool`) Whether it is required for the element.
    required = None

    def __init__(self, name, xmlns=None, required=False,
                 encoder=None, decoder=None):
        super(Attribute, self).__init__(encoder=encoder, decoder=decoder)
        self.name = name
        self.xmlns = xmlns
        self.key_pair = xmlns, name
        self.required = bool(required)

    def __get__(self, obj, cls=None):
        if isinstance(obj, Element):
            return obj._attrs.get(self)
        return self


class Content(CodecDescriptor):
    """Declare possible text nodes as a descriptor.

    :param encoder: an optional function that encodes Python value into
                    XML text value e.g. :func:`str()`.  the encoder function
                    has to take an argument
    :type encoder: :class:`collections.Callable`
    :param decoder: an optional function that decodes XML text value into
                    Python value e.g. :func:`int()`.  the decoder function
                    has to take a string argument
    :type decoder: :class:`collections.Callable`

    """

    def __get__(self, obj, cls=None):
        if isinstance(obj, Element):
            if getattr(obj, '_root', None):
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

    def read(self, element, value):
        """Read raw ``value`` from XML, decode it, and then set the attribute
        for content of the given ``element`` to the decoded value.

        .. note::

           Internal method.

        """
        self.__set__(element, self.decode(value, element))


class Element(object):
    """Represent an element in XML document.

    It provides the default constructor which takes keywords
    and initializes the attributes by given keyword arguments.
    For example, the following code that uses the default
    constructor::

        assert issubclass(Person, Element)

        author = Person(
            name='Hong Minhee',
            url='http://dahlia.kr/'
        )

    is equivalent to the following code::

        author = Person()
        author.name = 'Hong Minhee'
        author.url = 'http://dahlia.kr/'

    """

    __slots__ = '_attrs', '_content', '_data', '_parent', '_root'

    def __init__(self, _parent=None, *args, **attributes):
        self._attrs = getattr(self, '_attrs', {})  # FIXME
        self._content = None
        self._data = {}
        if _parent is not None:
            self._parent = weakref.ref(_parent)
            self._root = _parent._root
            if hasattr(self._root(), '_handler'):
                self._stack_top = len(self._root()._handler.stack)
        cls = type(self)
        acceptable_desc_types = Descriptor, Content, Attribute  # FIXME
        for attr_name, attr_value in attributes.items():
            if isinstance(getattr(cls, attr_name, None), acceptable_desc_types):
                setattr(self, attr_name, attr_value)
            else:
                raise SchemaError('{0.__module__}.{0.__name__} has no such '
                                  'attribute: {1}'.format(cls, attr_name))


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
        self._root = weakref.ref(self)
        super(DocumentElement, self).__init__(self, **kwargs)


class ElementList(collections.MutableSequence):
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

    def consume_buffer(self):
        """Consume the buffer for the parser.  It returns a generator,
        so can be stopped using :keyword:`break` statement by caller.

        .. note::

           Internal method.

        """
        element = self.element()
        root_ref = getattr(element, '_root', None)
        if not root_ref:
            return
        root = root_ref()
        parser = getattr(root, '_parser', None)
        if not parser:
            return
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
        if not getattr(element, '_parent', None):
            return True
        parent = element._parent()
        root = element._root()
        handler = getattr(root, '_handler', None)
        if not handler:
            return True
        stack = handler.stack
        top = element._stack_top
        return len(stack) < top or stack[top - 1].reserved_value is not parent

    def consume_index(self, index):
        if isinstance(index, slice):
            if index.start is not None and index.start >= 0 and \
               index.stop is not None and index.stop >= 0:
                index = max(index.start, index.stop)
            else:
                index = -1
        key = self.descriptor
        if index >= 0:
            for data in self.consume_buffer():
                if key in data and len(data[key]) > index:
                    return data[key]
        else:
            for data in self.consume_buffer():
                continue
        return self.element()._data.setdefault(key, [])

    def __len__(self):
        key = self.descriptor
        data = self.element()._data
        for data in self.consume_buffer():
            continue
        try:
            lst = data[key]
        except KeyError:
            return 0
        return len(lst)

    def __getitem__(self, index):
        return self.consume_index(index)[index]

    def __setitem__(self, index, value):
        data = self.consume_index(index)
        data[index] = value

    def __delitem__(self, index):
        data = self.consume_index(index)
        del data[index]

    def insert(self, index, value):
        data = self.consume_index(index)
        data.insert(index, value)

    def __nonzero__(self):
        data = self.consume_index(1)
        return bool(data)

    def __repr__(self):
        consumed = self.element()._data.get(self.descriptor, [])
        list_repr = repr(consumed)
        if not self.consumes_all():
            if consumed:
                list_repr = list_repr[:-1] + ', ...]'
            else:
                list_repr = '[...]'
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
        self.document = weakref.ref(document)
        self.stack = []

    def startElementNS(self, tag, qname, attrs):
        xmlns, name = tag
        try:
            parent_context = self.stack[-1]
        except IndexError:
            # document element
            doc = self.document()
            expected = getattr(doc, '__xmlns__', None), doc.__tag__
            if tag != expected:
                raise SyntaxError('document element must be {0}, '
                                  'not {1}'.format(expected, name))
            self.stack.append(
                ParserContext(
                    tag=name,
                    xmlns=xmlns,
                    descriptor=None,
                    reserved_value=doc,
                    content_buffer=[]
                )
            )
            reserved_value = doc
        else:
            parent_element = parent_context.reserved_value
            element_type = type(parent_element)
            child_tags = inspect_child_tags(element_type)
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
        if isinstance(reserved_value, Element):
            instance = reserved_value
            instance_type = type(instance)
            attributes = inspect_attributes(instance_type)
            instance_attrs_dict = instance._attrs
            for xml_attr, raw_value in attrs.items():
                try:
                    _, attr_desc = attributes[xml_attr]
                except KeyError:
                    continue
                instance_attrs_dict[attr_desc] = attr_desc.decode(
                    raw_value,
                    instance
                )

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
            attr = inspect_content_tag(type(context.reserved_value))
            if attr is not None:
                content_desc = attr[1]
                content_desc.read(context.reserved_value, text)
        else:
            context.descriptor.end_element(context.reserved_value, text)


def index_descriptors(element_type):
    """Index descriptors of the given ``element_type`` to make them
    easy to be looked up by their identifiers (pairs of XML namespace URI
    and tag name).

    :param element_type: a subtype of :class:`Element`
                         to index its descriptors
    :type element_type: :class:`type`

    .. note::

       Internal function.

    """
    if issubclass(element_type, DocumentElement) and \
       getattr(element_type, '__xmlns__', None):
        xmlns_set = set([element_type.__xmlns__])
    else:
        xmlns_set = set()
    attributes = {}
    child_tags = {}
    content = None
    element_type.__xmlns_set__ = xmlns_set  # to avoid infinite loop
    for attr in dir(element_type):
        desc = getattr(element_type, attr)
        if isinstance(desc, Content):
            if content is not None:
                raise DescriptorConflictError(
                    'there are more than a descriptor for the element content '
                    '(text node): {0!r} and {1!r}; there must not be any '
                    'duplicate descriptors for the same content'.format(
                        content[0], attr
                    )
                )
            content = attr, desc
        elif isinstance(desc, Attribute):
            if desc.key_pair in attributes:
                if desc.xmlns:
                    name = '{{{0}}}{1}'.format(*desc.key_pair)
                else:
                    name = desc.name
                raise DescriptorConflictError(
                    'there are more than a descriptor for the same attribute '
                    '{0!r}: {1!r} and {2!r}; there must not be any duplicate '
                    'descriptors for the same attribute'.format(
                        name, attributes[desc.key_pair], attr
                    )
                )
            attributes[desc.key_pair] = attr, desc
            if desc.xmlns:
                xmlns_set.add(desc.xmlns)
        elif isinstance(desc, Descriptor):
            if desc.key_pair in child_tags:
                if desc.xmlns:
                    tag = '{{{0}}}{1}'.format(*desc.key_pair)
                else:
                    tag = desc.tag
                raise DescriptorConflictError(
                    'there are more than a descriptor for the same element '
                    '{0!r}: {1!r} and {2!r}; there must not be any duplicate '
                    'descriptors for the same element'.format(
                        tag, child_tags[desc.key_pair], attr
                    )
                )
            child_tags[desc.key_pair] = attr, desc
            if desc.xmlns:
                xmlns_set.add(desc.xmlns)
            if isinstance(desc, Child):  # FIXME: should be polymorphic
                xmlns_set.update(inspect_xmlns_set(desc.element_type))
    element_type.__xmlns_set__ = frozenset(xmlns_set)
    element_type.__attributes__ = attributes
    element_type.__child_tags__ = child_tags
    element_type.__content_tag__ = content


def inspect_xmlns_set(element_type):
    """Get the set of XML namespaces used in the given ``element_type``,
    recursively including all child elements.

    :param element_type: a subtype of :class:`Element` to inspect
    :type element_type: :class:`type`
    :returns: a set of uri strings of used all xml namespaces
    :rtype: :class:`collections.Set`

    .. note::

       Internal function.

    """
    try:
        return element_type.__xmlns_set__
    except AttributeError:
        index_descriptors(element_type)
        return element_type.__xmlns_set__


def inspect_attributes(element_type):
    """Get the dictionary of :class:`Attribute` descriptors of
    the given ``element_type``.

    :param element_type: a subtype of :class:`Element` to inspect
    :type element_type: :class:`type`
    :returns: a dictionary of attribute identifiers (pairs of
              xml namespace uri and xml attribute name) to pairs of
              instance attribute name and associated :class:`Attribute`
              descriptor
    :rtype: :class:`collections.Mapping`

    .. note::

       Internal function.

    """
    try:
        return element_type.__attributes__
    except AttributeError:
        index_descriptors(element_type)
        return element_type.__attributes__


def inspect_child_tags(element_type):
    """Get the dictionary of :class:`Descriptor` objects of
    the given ``element_type``.

    :param element_type: a subtype of :class:`Element` to inspect
    :type element_type: :class:`type`
    :returns: a dictionary of child node identifiers (pairs of
              xml namespace uri and tag name) to pairs of
              instance attribute name and associated :class:`Descriptor`
    :rtype: :class:`collections.Mapping`

    .. note::

       Internal function.

    """
    try:
        child_tags = element_type.__child_tags__
    except AttributeError:
        index_descriptors(element_type)
        child_tags = element_type.__child_tags__
    return child_tags


def inspect_content_tag(element_type):
    """Gets the :class:`Content` descriptor of the given ``element_type``.

    :param element_type: a subtype of :class:`Element` to inspect
    :type element_type: :class:`type`
    :returns: a pair of instance attribute name and associated
              :class:`Content` descriptor
    :rtype: :class:`tuple`

    .. note::

       Internal function.

    """
    try:
        content = element_type.__content_tag__
    except AttributeError:
        index_descriptors(element_type)
        content = element_type.__content_tag__
    return content


def read(cls, iterable):
    """Initialize a document in read mode by opening the ``iterable``
    of XML string.

    Returned document element is not fully read but partially loaded
    into memory, and then lazily (and eventually) loaded when these
    are actually needed.

    :param cls: a subtype of :class:`DocumentElement`
    :type cls: :class:`type`
    :param iterable: chunks of XML string to read
    :type iterable: :class:`collections.Iterable`
    :returns: initialized document element in read mode
    :rtype: :class:`DocumentElement`

    """
    if not isinstance(cls, type):
        raise TypeError('cls must be a type object, not ' + repr(cls))
    elif not issubclass(cls, DocumentElement):
        raise TypeError(
            'cls must be a subtype of {0.__module__}.{0.__name__}, not '
            '{1.__module__}.{1.__name__}'.format(cls, DocumentElement)
        )
    iterator = iter(iterable)
    doc = cls()
    parser = xml.sax.make_parser()
    handler = ContentHandler(doc)
    parser.setContentHandler(handler)
    parser.setFeature(xml.sax.handler.feature_namespaces, True)
    doc._parser = parser
    doc._handler = handler
    doc._iterator = iterator
    stack = handler.stack
    while not stack:
        try:
            chunk = next(iterator)
        except StopIteration:
            break
        parser.feed(chunk)
    Element.__init__(doc, doc)
    return doc


def write(document, indent='  ', newline='\n', canonical_order=False):
    """Write the given ``document`` to XML string.  The return value is
    an iterator that yields chunks of an XML string.

    :param document: the document element to serialize
    :type document: :class:`DocumentElement`
    :param indent: an optional string to be used for indent.
                   default is four spaces (``'    '``)
    :type indent: :class:`str`
    :param newline: an optional character to be used for newline.
                    default is ``'\n'``
    :type newline: :class:`str`
    :param canonical_order: make the order of attributes and child nodes
                            consistent to any python versions and
                            implementations.  useful for testing.
                            :const:`False` by default
    :type canonical_order: :class:`bool`
    :returns: chunks of an XML string
    :rtype: :class:`types.GeneratorType`

    """
    if not isinstance(document, DocumentElement):
        raise TypeError(
            'document must be an instance of {0.__module__}.{0.__name__}, '
            'not {1!r}'.format(DocumentElement, document)
        )
    escape = xml.sax.saxutils.escape
    quoteattr = xml.sax.saxutils.quoteattr
    doc_cls = type(document)
    sort = sorted if canonical_order else lambda l, *a, **k: l
    xmlns_alias = dict(
        (uri, 'ns{0}'.format(i))
        for i, uri in enumerate(sort(inspect_xmlns_set(doc_cls)))
    )
    if UNICODE_BY_DEFAULT:
        encode = lambda s: s
    else:
        encode = lambda s: s.encode('utf-8')

    def _export(element, tag, xmlns, depth=0):
        element_type = type(element)
        for s in itertools.repeat(indent, depth):
            yield s
        yield '<'
        if xmlns:
            yield xmlns_alias[xmlns]
            yield ':'
        yield tag
        if not depth:
            for uri, prefix in sort(xmlns_alias.items(),
                                    key=operator.itemgetter(0)):
                yield ' xmlns:'
                yield prefix
                yield '='
                yield quoteattr(uri)
        attr_descriptors = sort(inspect_attributes(element_type).values(),
                                key=operator.itemgetter(0))
        for attr, desc in attr_descriptors:
            attr_value = desc.encode(getattr(element, attr, None),
                                     element)
            if attr_value is None:
                continue
            yield ' '
            if desc.xmlns:
                yield xmlns_alias[desc.xmlns]
                yield ':'
            yield desc.name
            yield '='
            yield encode(quoteattr(attr_value))
        content = inspect_content_tag(element_type)
        children = inspect_child_tags(element_type)
        if content or children:
            assert not (content and children)
            yield '>'
            if content:
                content_value = content[1].encode(
                    getattr(element, content[0], None),
                    element
                )
                if content_value is not None:
                    yield encode(escape(content_value))
            else:
                children = sort(children.values(),
                                key=operator.itemgetter(0))
                for attr, desc in children:
                    child_elements = getattr(element, attr, None)
                    if not desc.multiple:
                        child_elements = [child_elements]
                    for child_element in child_elements:
                        if isinstance(desc, Text):  # FIXME: remote type query
                            child_element = desc.encode(child_element, element)
                            if child_element is None:
                                continue
                            yield newline
                            for s in itertools.repeat(indent, depth + 1):
                                yield s
                            yield '<'
                            if desc.xmlns:
                                yield xmlns_alias[desc.xmlns]
                                yield ':'
                            yield desc.tag
                            yield '>'
                            child_value = text_type(child_element)
                            yield encode(escape(child_value))
                            yield '</'
                            if desc.xmlns:
                                yield xmlns_alias[desc.xmlns]
                                yield ':'
                            yield desc.tag
                            yield '>'
                        elif child_element is not None:
                            yield newline
                            subiter = _export(child_element,
                                              desc.tag,
                                              desc.xmlns,
                                              depth=depth + 1)
                            for chunk in subiter:
                                yield chunk
                yield newline
            yield '</'
            if xmlns:
                yield xmlns_alias[xmlns]
                yield ':'
            yield tag
            yield '>'
        else:
            yield '/>'
    return itertools.chain(
        ['<?xml version="1.0" encoding="utf-8"?>\n'],
        _export(document, doc_cls.__tag__, doc_cls.__xmlns__)
    )
