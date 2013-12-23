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

"""
import collections
import copy
import inspect
import itertools
import operator
import platform
import weakref
import xml.sax
import xml.sax.handler
import xml.sax.saxutils

from .compat import UNICODE_BY_DEFAULT, binary_type, string_type
from .compat.xmlpullreader import PullReader

__all__ = ('PARSER_LIST',
           'Attribute', 'Child', 'Codec', 'CodecDescriptor', 'CodecError',
           'Content', 'ContentHandler', 'DecodeError', 'Descriptor',
           'DescriptorConflictError', 'DocumentElement', 'Element',
           'ElementList', 'EncodeError', 'IntegrityError',
           'SchemaError', 'Text',
           'complete', 'element_list_for',
           'index_descriptors', 'inspect_attributes', 'inspect_child_tags',
           'inspect_content_tag', 'inspect_xmlns_set', 'is_partially_loaded',
           'read', 'validate', 'write')


class SchemaError(TypeError):
    """Error which rises when a schema definition has logical errors."""


class DescriptorConflictError(SchemaError, AttributeError):
    """Error which rises when a schema has duplicate descriptors more than
    one for the same attribute, the same child element, or the text node.

    """


class IntegrityError(SchemaError, AttributeError):
    """Rise when an element is invalid according to the schema."""


class CodecError(SchemaError, ValueError):
    """Rise when encoding/decoding between Python values and XML data
    goes wrong.

    """


class EncodeError(CodecError):
    """Rise when encoding Python values into XML data goes wrong."""


class DecodeError(CodecError):
    """Rise when decoding XML data to Python values goes wrong."""


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

    #: (:class:`collections.Callable`) An optional function to be used
    #: for sorting multiple elements.  It has to take an element and
    #: return a value for sort key.  It is the same to ``key`` option of
    #: :func:`sorted()` built-in function.
    #:
    #: It's available only when :attr:`multiple` is :const:`True`.
    #:
    #: Use :attr:`sort_reverse` for descending order.
    #:
    #: .. note::
    #:
    #:    It doesn't guarantee that all elements must be sorted in
    #:    runtime, but all elements become sorted when it's written
    #:    using :func:`write()` function.
    sort_key = None

    #: (:class:`bool`) Whether to reverse elements when they become
    #: sorted.  It is the same to ``reverse`` option of :func:`sorted()`
    #: built-in function.
    #:
    #: It's available only when :attr:`sort_key` is present.
    sort_reverse = None

    def __init__(self, tag, xmlns=None, required=False, multiple=False,
                 sort_key=None, sort_reverse=None):
        global _descriptor_counter
        if required and multiple:
            raise TypeError('required and multiple are exclusive')
        elif not multiple and sort_key is not None:
            raise TypeError('sort_key function can be used only for multiple '
                            'children')
        elif not (sort_key is None or callable(sort_key)):
            raise TypeError('sort_key function must be callable, not ' +
                            repr(sort_key))
        elif sort_key is None and sort_reverse is not None:
            raise TypeError('sort_reverse option is available only when '
                            'sort_key is also present')
        self.tag = tag
        self.xmlns = xmlns
        self.key_pair = self.xmlns, self.tag
        self.required = bool(required)
        self.multiple = bool(multiple)
        self.sort_key = sort_key
        self.sort_reverse = bool(sort_reverse)
        try:
            _descriptor_counter += 1
        except NameError:
            _descriptor_counter = 1
        self.descriptor_counter = _descriptor_counter

    def __get__(self, obj, cls=None):
        if isinstance(obj, Element):
            if self.multiple:
                return ElementList(obj, self)
            root = obj._root() if hasattr(obj, '_root') else None
            if root is not None and getattr(root, '_handler', None):
                handler = root._handler
                stack = handler.stack
                while ((obj._data.get(self) is None and
                       (not stack or stack[-1]))):
                    if not root._parse_next():
                        break
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

    In order to have :class:`Child` of the element type which is not
    defined yet (or self-referential) pass the class name of the element
    type to contain.  The name will be lazily evaluated e.g.::

        class Person(Element):
            '''Everyone can have their children, that also are a Person.'''

            children = Child('child', 'Person', multiple=True)

    :param tag: the tag name
    :type tag: :class:`str`
    :param xmlns: an optional XML namespace URI
    :type xmlns: :class:`str`
    :param element_type: the type of child element(s).
                         it has to be a subtype of :class:`Element`.
                         if it's a string it means referring the class name
                         which is going to be lazily evaluated
    :type element_type: :class:`type`, :class:`str`
    :param required: whether the child is required or not.
                     it's exclusive to ``multiple``.
                     :const:`False` by default
    :type required: :class:`bool`
    :param multiple: whether the child can be multiple.
                     it's exclusive to ``required``.
                     :const:`False` by default
    :type multiple: :class:`bool`
    :param sort_key: an optional function to be used for sorting
                     multiple child elements.  it has to take a child as
                     :class:`Element` and return a value for sort key.
                     it is the same to ``key`` option of :func:`sorted()`
                     built-in function.
                     note that *it doesn't guarantee that all elements must
                     be sorted in runtime*, but all elements become sorted
                     when it's written using :func:`write()` function.
                     it's available only when ``multiple`` is :const:`True`.
                     use ``sort_reverse`` for descending order.
    :type sort_key: :class:`collections.Callable`
    :param sort_reverse: ehether to reverse elements when they become
                         sorted.  it is the same to ``reverse`` option of
                         :func:`sorted()` built-in function.
                         it's available only when ``sort_key`` is present
    :type sort_reverse: :class:`bool`

    .. todo::

       It crashes when the document has any non-ASCII characters.

    """

    def __init__(self, tag, element_type, xmlns=None, required=False,
                 multiple=False, sort_key=None, sort_reverse=None):
        if isinstance(element_type, type):
            if not issubclass(element_type, Element):
                raise TypeError(
                    'element_type must be a subtype of {0.__module__}.'
                    '{0.__name__}, not {1!r}'.format(Element, element_type)
                )
        elif isinstance(element_type, string_type):
            frame = inspect.currentframe().f_back
            element_type = element_type, frame.f_locals, frame.f_globals
        else:
            raise TypeError('element_type must be a class (or a string '
                            'referring its name), not ' + repr(element_type))
        super(Child, self).__init__(
            tag,
            xmlns=xmlns,
            required=required,
            multiple=multiple,
            sort_key=sort_key,
            sort_reverse=sort_reverse
        )
        self._element_type = element_type

    @property
    def element_type(self):
        """(:class:`type`) The class of this child can contain.  It must
        be a subtype of :class:`Element`.

        """
        if not isinstance(self._element_type, type):
            name, loc, glob = self._element_type
            try:
                self._element_type = loc[name]
            except KeyError:
                try:
                    self._element_type = glob[name]
                except KeyError:
                    raise NameError('name {0!r} is not defined'.format(name))
        return self._element_type

    def __get__(self, obj, cls=None):
        if isinstance(obj, Element):
            if self.multiple:
                return ElementList(obj, self, self.element_type)
        return super(Child, self).__get__(obj, cls)

    def __set__(self, obj, value):
        if isinstance(obj, Element):
            element_type = self.element_type
            if self.multiple:
                if isinstance(value, collections.Sequence):
                    if len(value) < 1 or \
                       isinstance(value[0], element_type):
                        value = [e if isinstance(e, element_type)
                                 else element_type.__coerce_from__(e)
                                 for e in value]
                        for e in value:
                            if not isinstance(e, element_type):
                                raise TypeError(
                                    'expected instances of {0.__module__}.'
                                    '{0.__name__}, not {1!r}'.format(e)
                                )
                        obj._data[self] = value
                    else:
                        raise TypeError(
                            'expected a sequence of {0.__module__}.'
                            '{0.__name__}, not {1!r}'.format(
                                element_type, value
                            )
                        )
                else:
                    raise TypeError('Child property of multiple=True option '
                                    'only accepts a sequence, not ' +
                                    repr(value))
            else:
                if not (value is None or isinstance(value, element_type)):
                    value = element_type.__coerce_from__(value)
                if not (value is None or isinstance(value, element_type)):
                    raise TypeError(
                        'expected an instance of {0.__module__}.{0.__name__}, '
                        'not {1!r}'.format(element_type, value)
                    )
                obj._data[self] = value
        else:
            raise AttributeError('cannot change the class attribute')

    def start_element(self, element, attribute):
        child_element = self.element_type(element)
        if self.multiple:
            element_list = element._data.setdefault(self, [])
            element_list.append(child_element)
        else:
            if self not in element._data:
                setattr(element, attribute, child_element)
        return child_element

    def end_element(self, reserved_value, content):
        element_type = type(reserved_value)
        attr = inspect_content_tag(element_type)
        if attr is not None:
            content_desc = attr[1]
            content_desc.read(reserved_value, content)
        reserved_value._partial = False


class Codec(object):
    """Abstract base class for codecs to serialize Python values to be
    stored in XML and deserialize XML texts to Python values.

    In most cases encoding and decoding are implementation details of
    *format* which is well-defined, so these two functions could be
    paired.  The interface rely on that idea.

    To implement a codec, you have to subclass :class:`Codec` and
    override a pair of methods: :meth:`encode()` and :meth:`decode()`.

    Codec objects are acceptable by :class:`Attribute`, :class:`Text`, and
    :class:`Content` (all they subclass :class:`CodecDescriptor`).

    """

    def encode(self, value):
        """Encode the given Python ``value`` into XML text.

        :param value: Python value to encode
        :returns: the encoded XML text
        :rtype: :class:`str`
        :raise EncodeError: when encoding the given ``value`` goes wrong

        .. note::

           Every :class:`Codec` subtype has to override this method.

        """
        cls = type(self)
        raise NotImplementedError('{0.__module__}.{0.__name__}.encode() '
                                  'is not implemented'.format(cls))

    def decode(self, text):
        """Decode the given XML ``text`` to Python value.

        :param text: XML text to decode
        :type text: :class:`str`
        :returns: the decoded Python value
        :raise DecodeError: when decoding the given XML ``text`` goes wrong

        .. note::

           Every :class:`Codec` subtype has to override this method.

        """
        cls = type(self)
        raise NotImplementedError('{0.__module__}.{0.__name__}.decode() '
                                  'is not implemented'.format(cls))


# Semi-structured record type for only internal use.
CodecFunction = collections.namedtuple('CodecFunction', 'function descriptor')


class CodecDescriptor(object):
    """Mixin class for descriptors that provide :meth:`decoder` and
    :meth:`encoder`.

    :class:`Attribute`, :class:`Content` and :class:`Text` can take
    ``encoder`` and ``decoder`` functions for them.  It's used for encoding
    from Python values to XML string and decoding raw values from XML to
    natural Python representations.

    It can take a ``codec``, or ``encode`` and ``decode`` separately.
    (Of course they all can be present at a time.)  In most cases,
    you'll need only ``codec`` parameter that encoder and decoder
    are coupled::

        Text('dob', Rfc3339(prefer_utc=True))

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

    :param codec: an optional codec object to use.  if it's callable and
                  not an instance of :class:`Codec`, its return value will
                  be used instead.  it means this can take class object of
                  :class:`Codec` subtype that is not instantiated yet
                  unless the constructor require any arguments
    :type codec: :class:`Codec`, :class:`collections.Callable`
    :param encoder: an optional function that encodes Python value into
                    XML text value e.g. :func:`str()`.  the encoder function
                    has to take an argument
    :type encoder: :class:`collections.Callable`
    :param decoder: an optional function that decodes XML text value into
                    Python value e.g. :func:`int()`.  the decoder function
                    has to take a string argument
    :type decoder: :class:`collections.Callable`

    """

    def __init__(self, codec=None, encoder=None, decoder=None):
        self.encoders = []
        self.decoders = []
        if callable(codec) and not isinstance(codec, Codec):
            codec = codec()
        if codec is not None:
            if not isinstance(codec, Codec):
                raise TypeError('codec must be an instance of {0.__module__}.'
                                '{0.__name__}, not {1!r}'.format(Codec, codec))
            self.encoders.append(CodecFunction(codec.encode, descriptor=False))
            self.decoders.append(CodecFunction(codec.decode, descriptor=False))
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
    :param codec: an optional codec object to use.  if it's callable and
                  not an instance of :class:`Codec`, its return value will
                  be used instead.  it means this can take class object of
                  :class:`Codec` subtype that is not instantiated yet
                  unless the constructor require any arguments
    :type codec: :class:`Codec`, :class:`collections.Callable`
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
    :param sort_key: an optional function to be used for sorting
                     multiple child elements.  it has to take a child as
                     :class:`Element` and return a value for sort key.
                     it is the same to ``key`` option of :func:`sorted()`
                     built-in function.
                     note that *it doesn't guarantee that all elements must
                     be sorted in runtime*, but all elements become sorted
                     when it's written using :func:`write()` function.
                     it's available only when ``multiple`` is :const:`True`.
                     use ``sort_reverse`` for descending order.
    :type sort_key: :class:`collections.Callable`
    :param sort_reverse: ehether to reverse elements when they become
                         sorted.  it is the same to ``reverse`` option of
                         :func:`sorted()` built-in function.
                         it's available only when ``sort_key`` is present
    :type sort_reverse: :class:`bool`

    """

    def __init__(self, tag, codec=None, xmlns=None, required=False,
                 multiple=False, encoder=None, decoder=None,
                 sort_key=None, sort_reverse=None):
        Descriptor.__init__(self, tag,
                            xmlns=xmlns, required=required, multiple=multiple,
                            sort_key=sort_key, sort_reverse=sort_reverse)
        CodecDescriptor.__init__(self, codec=codec,
                                 encoder=encoder, decoder=decoder)

    def __get__(self, obj, cls=None):
        if isinstance(obj, Element):
            if self.multiple:
                return ElementList(obj, self, string_type)
        return super(Text, self).__get__(obj, cls)

    def start_element(self, element, attribute):
        return element

    def end_element(self, reserved_value, content):
        content = self.decode(content, reserved_value)
        if self.multiple:
            reserved_value._data.setdefault(self, []).append(content)
        else:
            reserved_value._data.setdefault(self, content)


class Attribute(CodecDescriptor):
    """Declare possible element attributes as a descriptor.

    :param name: the XML attribute name
    :type name: :class:`str`
    :param codec: an optional codec object to use.  if it's callable and
                  not an instance of :class:`Codec`, its return value will
                  be used instead.  it means this can take class object of
                  :class:`Codec` subtype that is not instantiated yet
                  unless the constructor require any arguments
    :type codec: :class:`Codec`, :class:`collections.Callable`
    :param xmlns: an optional XML namespace URI
    :type xmlns: :class:`str`
    :param required: whether the child is required or not.
                     :const:`False` by default
    :type required: :class:`bool`
    :param default: an optional function that returns default value when
                    the attribute is not present.  the function takes an
                    argument which is an :class:`Element` instance
    :type default: :class:`collections.Callable`
    :param encoder: an optional function that encodes Python value into
                    XML text value e.g. :func:`str()`.  the encoder function
                    has to take an argument
    :type encoder: :class:`collections.Callable`
    :param decoder: an optional function that decodes XML text value into
                    Python value e.g. :func:`int()`.  the decoder function
                    has to take a string argument
    :type decoder: :class:`collections.Callable`

    .. versionchanged:: 0.2.0
       The ``default`` option becomes to accept only callable objects.
       Below 0.2.0, ``default`` is not a function but a value which
       is simply used as it is.

    """

    #: (:class:`str`) The XML attribute name.
    name = None

    #: (:class:`str`) The optional XML namespace URI.
    xmlns = None

    #: (:class:`tuple`) The pair of (:attr:`xmlns`, :attr:`name`).
    key_pair = None

    #: (:class:`bool`) Whether it is required for the element.
    required = None

    #: (:class:`collections.Callable`) The function that returns default
    #: value when the attribute is not present.  The function takes an
    #: argument which is an :class:`Element` instance.
    #:
    #: .. versionchanged:: 0.2.0
    #:    It becomes to accept only callable objects.  Below 0.2.0,
    #:    :attr:`default` attribute is not a function but a value which
    #:    is simply used as it is.
    default = None

    def __init__(self, name, codec=None, xmlns=None, required=False,
                 default=None, encoder=None, decoder=None):
        if not (default is None or callable(default)):
            raise TypeError('default must be callable, not ' + repr(default))
        super(Attribute, self).__init__(codec=codec,
                                        encoder=encoder,
                                        decoder=decoder)
        self.name = name
        self.xmlns = xmlns
        self.key_pair = xmlns, name
        self.required = bool(required)
        self.default = default

    def __get__(self, obj, cls=None):
        if isinstance(obj, Element):
            attrs = obj._attrs
            if self.default is None:
                return attrs.get(self)
            return attrs.setdefault(self, self.default(obj))
        return self

    def __set__(self, obj, value):
        if isinstance(obj, Element):
            obj._attrs[self] = value


class Content(CodecDescriptor):
    """Declare possible text nodes as a descriptor.

    :param codec: an optional codec object to use.  if it's callable and
                  not an instance of :class:`Codec`, its return value will
                  be used instead.  it means this can take class object of
                  :class:`Codec` subtype that is not instantiated yet
                  unless the constructor require any arguments
    :type codec: :class:`Codec`, :class:`collections.Callable`
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
                if getattr(root, '_parser', None):
                    handler = root._handler
                    while (obj._content is None and
                           (not handler.stack or handler.stack[-1])):
                        if not root._parse_next():
                            break
            return obj._content
        return self

    def __set__(self, obj, value):
        obj._content = value

    def read(self, element, value):
        """Read raw ``value`` from XML, decode it, and then set the attribute
        for content of the given ``element`` to the decoded value.

        .. note::

           Internal method.

        """
        decoded = self.decode(value, element)
        self.__set__(element, decoded)


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

    __slots__ = '_attrs', '_content', '_data', '_parent', '_root', '_partial'

    def __init__(self, _parent=None, **attributes):
        self._attrs = getattr(self, '_attrs', {})  # FIXME
        self._content = getattr(self, '_content', None)
        self._data = getattr(self, '_data', {})
        self._partial = False
        if _parent is not None:
            if not isinstance(_parent, Element):
                raise TypeError('expected a {0.__module__}.{0.__name__} '
                                'instance, not {1!r}'.format(Element, _parent))
            self._parent = weakref.ref(_parent)
            self._root = _parent._root
            if hasattr(self._root(), '_handler'):
                self._stack_top = (1 if self._root() is self
                                   else len(self._root()._handler.stack))
                self._partial = True
        cls = type(self)
        acceptable_desc_types = Descriptor, Content, Attribute, property
        # FIXME: ^-- hardcoded type list
        for attr_name, attr_value in attributes.items():
            if isinstance(getattr(cls, attr_name, None), acceptable_desc_types):
                setattr(self, attr_name, attr_value)
            else:
                raise SchemaError('{0.__module__}.{0.__name__} has no such '
                                  'attribute: {1}'.format(cls, attr_name))

    def __entity_id__(self):
        """Identify the entity object.  It returns the entity object itself
        by default, but should be overridden.

        :returns: any value to identify the entity object

        """
        return self

    def __merge_entities__(self, other):
        """Merge two entities (``self`` and ``other``).  It can return one
        of the two, or even a new entity object.  This method is used by
        :class:`~libearth.session.Session` objects to merge conflicts between
        concurrent updates.

        :param other: other entity to merge.  it's guaranteed that it's
                      older session's (note that it doesn't mean this entity
                      is older than ``self``, but the session's last update
                      is)
        :type other: :class:`Element`
        :returns: on of the two, or even an new entity object that merges
                  two entities
        :rtype: :class:`Element`

        .. note::

           The default implementation simply returns ``self``.
           That means the entity of the newer session will always win
           unless the method is overridden.

        """
        return self

    @classmethod
    def __coerce_from__(cls, value):
        """Cast a value which isn't an instance of the element type to
        the element type.  It's useful when a boxed element type could
        be more naturally represented using builtin type.

        For example, :class:`~libearth.feed.Mark` could be represented
        as a boolean value, and :class:`~libearth.feed.Text` also
        could be represented as a string.

        The following example shows how the element type can be
        automatically casted from string by implementing
        :meth:`__coerce_from__()` class method::

            @classmethod
            def __coerce_from__(cls, value):
                if isinstance(value, str):
                    return Text(value=value)
                raise TypeError('expected a string or Text')

        """
        raise TypeError('expected an instance of {0.__module__}.{0.__name__}, '
                        'not {1!r}'.format(cls, value))


class DocumentElement(Element):
    """The root element of the document.

    .. attribute:: __tag__

       (:class:`str`) Every :class:`DocumentElement` subtype has to define
       this attribute to the root tag name.

    .. attribute:: __xmlns__

       (:class:`str`) A :class:`DocumentElement` subtype may define this
       attribute to the XML namespace of the document element.

    """

    __slots__ = '_parser', '_iterator', '_handler'

    __tag__ = NotImplemented
    __xmlns__ = None

    def __init__(self, _parent=None, **kwargs):
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
        super(DocumentElement, self).__init__(_parent or self, **kwargs)

    def _parse_next(self):
        """Parse the next step of iteration.

        :returns: whether it's not complete or consumed all.
                  :const:`False` if it's completely consumed
        :rtype: :class:`bool`

        """
        parser = getattr(self, '_parser', None)
        if not parser:
            return False
        if isinstance(parser, PullReader):
            if parser.feed():
                return True
        else:
            try:
                chunk = next(self._iterator)
            except StopIteration:
                pass
            else:
                parser.feed(chunk)
                return True
        try:
            parser.close()
        except xml.sax.SAXException:
            pass
        return False


class ElementList(collections.MutableSequence):
    """List-like object to represent multiple chidren.  It makes the parser
    to lazily consume the buffer when an element of a particular offset
    is requested.

    You can extend methods or properties for a particular element type
    using :func:`element_list_for()` class decorator e.g.::

        @element_list_for(Link)
        class LinkList(collections.Sequence):
            '''Specialized ElementList for Link elements.'''

            def filter_by_mimetype(self, mimetype):
                '''Filter links by their mimetype.'''
                return [link for link in self if link.mimetype == mimetype]

    Extended methods/properties can be used for element lists for the type::

        assert isinstance(feed.links, LinkList)
        assert isinstance(feed.links, ElementList)
        feed.links.filter_by_mimetype('text/html')

    """

    __slots__ = ('element', 'descriptor', 'value_type',
                 'tag', 'xmlns', 'key_pair')

    #: (:class:`collections.MutableMapping`) The internal table for
    #: specialized subtypes used by :meth:`register_specialized_type()`
    #: method and :func:`element_list_for()` class decorator.
    specialized_types = {}

    @classmethod
    def register_specialized_type(cls, value_type, specialized_type):
        """Register specialized :class:`collections.Sequence` type for
        a particular ``value_type``.

        An imperative version of :func`element_list_for()` class decorator.

        :param value_type: a particular element type that ``specialized_type``
                             would be used for instead of default
                             :class:`ElementList` class.
                             it has to be a subtype of :class:`Element`
        :type value_type: :class:`type`
        :param specialized_type: a :class:`collections.Sequence` type which
                                 extends methods and properties for
                                 ``value_type``
        :type specialized_type: :class:`type`

        """
        if not isinstance(value_type, type):
            raise TypeError('value_type must be a type object, not ' +
                            repr(value_type))
        elif not issubclass(value_type, Element):
            raise TypeError(
                'value_type must be a subtype of {0.__module__}.{0.__name__},'
                ' not {1.__module__}.{1.__name__}'.format(Element, value_type)
            )
        elif not isinstance(specialized_type, type):
            raise TypeError('specialized_type must be a type object, not ' +
                            repr(specialized_type))
        elif not issubclass(specialized_type, collections.Sequence):
            raise TypeError(
                'specialized_type must be a subtype of {0.__module__}.'
                '{0.__name__}, not {1.__module__}.{1.__name__}'
                ''.format(collections.Sequence, specialized_type)
            )
        try:
            t, t2 = cls.specialized_types[value_type]
        except KeyError:
            pass
        else:
            if t is specialized_type or t2 is specialized_type:
                return
            raise TypeError(
                '{0.__module__}.{0.__name__} already has its own specialized '
                'subtype: {1.__module__}.{1.__name__}'.format(value_type, t)
            )
        cls.specialized_types[value_type] = specialized_type, None

    def __new__(cls, element, descriptor, value_type=None):
        try:
            supcls, subcls = cls.specialized_types[value_type]
        except KeyError:
            subcls = cls
        else:
            if issubclass(supcls, cls):
                cls = supcls
                subcls = supcls
                cls.specialized_types[value_type] = supcls, supcls
            if subcls is None:
                subcls = type(supcls.__name__, (cls, supcls), {})
                subcls.__module__ = supcls.__module__
                cls.specialized_types[value_type] = supcls, subcls
        return object.__new__(subcls)

    def __init__(self, element, descriptor, value_type=None):
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
        elif not (value_type is None or isinstance(value_type, type)):
            raise TypeError('value_type must be a type, not ' +
                            repr(value_type))
        self.element = element
        self.descriptor = descriptor
        self.value_type = value_type

    def consume_buffer(self):
        """Consume the buffer for the parser.  It returns a generator,
        so can be stopped using :keyword:`break` statement by caller.

        .. note::

           Internal method.

        """
        root_ref = getattr(self.element, '_root', None)
        if not root_ref:
            return
        root = root_ref()
        if not getattr(root, '_parser', None):
            return
        data = self.element._data
        while not self.consumes_all():
            yield data
            if not root._parse_next():
                break
        yield data

    def consumes_all(self):
        element = self.element
        if getattr(element, '_parent', None) is None:
            return True
        parent = element._parent()
        root = element._root()
        handler = getattr(root, '_handler', None)
        if handler is None:
            return True
        stack = handler.stack
        top = element._stack_top
        if len(stack) < top:
            return True
        for context in reversed(stack):
            if context.reserved_value is parent:
                return False
        return True

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
        return self.element._data.setdefault(key, [])

    def validate_value(self, value):
        if self.value_type is None or isinstance(value, self.value_type):
            return value
        elif self.value_type is string_type:
            raise TypeError('expected a string, not ' + repr(value))
        elif issubclass(self.value_type, Element):
            value = self.value_type.__coerce_from__(value)
            if isinstance(value, self.value_type):
                return value
        raise TypeError('expected an instance of {0.__module__}.{0.__name__}, '
                        'not {1!r}'.format(self.value_type, value))

    def __len__(self):
        key = self.descriptor
        data = self.element._data
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
        if isinstance(index, slice):
            data[index] = map(self.validate_value, value)
        else:
            data[index] = self.validate_value(value)

    def __delitem__(self, index):
        data = self.consume_index(index)
        del data[index]

    def insert(self, index, value):
        data = self.consume_index(index)
        data.insert(index, self.validate_value(value))

    def __nonzero__(self):
        data = self.consume_index(1)
        return bool(data)

    def __repr__(self):
        consumed = self.element._data.get(self.descriptor, [])
        list_repr = repr(consumed)
        if not self.consumes_all():
            if consumed:
                list_repr = list_repr[:-1] + ', ...]'
            else:
                list_repr = '[...]'
        return '<{0.__module__}.{0.__name__} {1}>'.format(
            type(self), list_repr
        )


class element_list_for(object):
    """Class decorator which registers specialized :class:`ElementList`
    subclass for a particular ``value_type`` e.g.::

        @element_list_for(Link)
        class LinkList(collections.Sequence):
            '''Specialized ElementList for Link elements.'''

            def filter_by_mimetype(self, mimetype):
                '''Filter links by their mimetype.'''
                return [link for link in self if link.mimetype == mimetype]

    :param value_type: a particular element type that ``specialized_type``
                         would be used for instead of default
                         :class:`ElementList` class.
                         it has to be a subtype of :class:`Element`
    :type value_type: :class:`type`

    """

    def __init__(self, value_type):
        if not isinstance(value_type, type):
            raise TypeError('value_type must be a type object, not ' +
                            repr(value_type))
        elif not issubclass(value_type, Element):
            raise TypeError(
                'value_type must be a subtype of {0.__module__}.{0.__name__},'
                ' not {1.__module__}.{1.__name__}'.format(Element, value_type)
            )
        self.value_type = value_type

    def __call__(self, specialized_type):
        ElementList.register_specialized_type(self.value_type, specialized_type)
        return specialized_type


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
                raise IntegrityError('document element must be {0}, '
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
                available_children = [
                    '{0} (namespace: {1})'.format(name, ns) if xmlns else name
                    for ns, name in child_tags
                ]
                available_children.sort()
                available_children = ', '.join(available_children)
                if xmlns:
                    raise IntegrityError(
                        'unexpected element: {0} (namespace: {1}); available '
                        'elements: {2}'.format(name, xmlns, available_children)
                    )
                raise IntegrityError(
                    'unexpected element: {0}; available elements: '.format(
                        name,
                        available_children
                    )
                )
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
                    raise IntegrityError('unexpected element: {0} (namespace: '
                                         '{1})'.format(name, xmlns))
                raise IntegrityError('unexpected element: ' + name)
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
            context.reserved_value._partial = False
        else:
            context.descriptor.end_element(context.reserved_value, text)


def complete(element):
    """Completely load the given ``element``.

    :param element: an element loaded by :func:`read()`
    :type element: :class:`Element`

    """
    if not isinstance(element, Element):
        raise TypeError('element must be an instance of {0.__module__}.'
                        '{0.__name__}, not {1!r}'.format(Element, element))
    if element._partial:
        parse_next = element._root()._parse_next
        while element._partial:
            parse_next()


def is_partially_loaded(element):
    """Return whether the given ``element`` is not completely loaded
    by :func:`read()` yet.

    :param element: an element
    :type element: :class:`Element`
    :returns: whether :const:`True` if the given ``element`` is partially
              loaded
    :rtype: :class:`bool`

    """
    if not isinstance(element, Element):
        raise TypeError('element must be an instance of {0.__module__}.'
                        '{0.__name__}, not {1!r}'.format(Element, element))
    return element._partial


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
    if not (isinstance(element_type, type) and
            issubclass(element_type, Element)):
        raise TypeError('element_type must be a subtype of {0.__name__}.'
                        '{0.__name__}, not {1!r}'.format(Element, element_type))
    elif (issubclass(element_type, DocumentElement) and
          getattr(element_type, '__xmlns__', None)):
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
    else:
        # FIXME: it should be tested, and considered in inspect_content_tag(),
        # inspect_xmlns_set(), and inspect_attributes() as well.
        if any(hasattr(sup, '__child_tags__') and
               sup.__child_tags__ is child_tags
               for sup in element_type.__bases__):
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


#: (:class:`collections.Sequence`) The list of :mod:`xml.sax` parser
#: implementations to try to import.
PARSER_LIST = []

if platform.python_implementation() == 'IronPython':
    PARSER_LIST = ['libearth.compat.clrxmlreader']


def read(cls, iterable):
    """Initialize a document in read mode by opening the ``iterable``
    of XML string.  ::

        with open('doc.xml', 'rb') as f:
            read(Person, f)

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
    doc = cls()
    parser = xml.sax.make_parser(PARSER_LIST)
    handler = ContentHandler(doc)
    parser.setContentHandler(handler)
    parser.setFeature(xml.sax.handler.feature_namespaces, True)
    if isinstance(parser, PullReader):
        parser.prepareParser(iterable)
    else:
        doc._iterator = iter(iterable)
    doc._parser = parser
    doc._handler = handler
    stack = handler.stack
    while not stack:
        if not doc._parse_next():
            break
    Element.__init__(doc, doc)
    return doc


def validate(element, recurse=True, raise_error=True):
    """Validate the given ``element`` according to the schema.  ::

        from libearth.schema import IntegrityError, validate

        try:
            validate(element)
        except IntegrityError:
            print('the element {0!r} is invalid!'.format(element))

    :param element: the element object to validate
    :type element: :class:`Element`
    :param recurse: recursively validate the whole tree (child nodes).
                    :const:`True` by default
    :type recurse: :class:`bool`
    :param raise_error: raise exception when the ``element`` is invalid.
                        if it's :const:`False` it returns :const:`False`
                        instead of raising an exception.
                        :const:`True` by default
    :type raise_error: :class:`bool`
    :returns: :const:`True` if the ``element`` is valid.
              :const:`False` if the ``element`` is invalid and
              ``raise_error`` option is :const:`False``
    :raise IntegrityError: when the ``element`` is invalid and
                           ``raise_error`` option is :const:`True`

    """
    element_type = type(element)
    for name, desc in inspect_attributes(element_type).values():
        if desc.required and not getattr(element, name, None):
            if raise_error:
                raise IntegrityError(
                    '{0.__module__}.{0.__name__}.{1} is required, but '
                    '{2!r} lacks it'.format(element_type, name, element)
                )
            return False
    for name, desc in inspect_child_tags(element_type).values():
        child_element = getattr(element, name, None)
        if desc.required and not child_element:
            if raise_error:
                raise IntegrityError(
                    '{0.__module__}.{0.__name__}.{1} is required, but '
                    '{2!r} lacks it'.format(element_type, name, element)
                )
            return False
        if recurse and child_element is not None:
            if validate(child_element, recurse=True, raise_error=raise_error):
                continue
            return False
    return True


class write(collections.Iterable):
    r"""Write the given ``document`` to XML string.  The return value is
    an iterator that yields chunks of an XML string.  ::

        with open('doc.xml', 'w') as f:
            for chunk in write(document):
                f.write(chunk)

    :param document: the document element to serialize
    :type document: :class:`DocumentElement`
    :param validate: whether validate the ``document`` or not.
                     :const:`True` by default
    :type validate: :class:`bool`
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
    :param as_bytes: return chunks as :class:`bytes` (:class:`str` in Python 2)
                     if :const:`True`.  return chunks as :class:`str`
                     (:class:`unicode` in Python 3) if :const:`False`.
                     return chunks as default string type (:class:`str`)
                     by default
    :returns: chunks of an XML string
    :rtype: :class:`collections.Iterable`

    """

    def __init__(self, document, validate=True, indent='  ', newline='\n',
                 canonical_order=False, as_bytes=None):
        if not isinstance(document, DocumentElement):
            raise TypeError(
                'document must be an instance of {0.__module__}.{0.__name__}, '
                'not {1!r}'.format(DocumentElement, document)
            )
        self.document = document
        self.document_type = type(document)
        self.validate = validate
        self.indent = indent
        self.newline = newline
        self.as_bytes = as_bytes
        self.sort = sorted if canonical_order else lambda l, *a, **k: l
        xmlns_set = inspect_xmlns_set(self.document_type)
        self.xmlns_alias = dict(
            (uri, 'ns{0}'.format(i))
            for i, uri in enumerate(self.sort(xmlns_set))
        )

    def __iter__(self):
        result = itertools.chain(['<?xml version="1.0" encoding="utf-8"?>\n'],
                                 self.export(self.document,
                                             self.document_type.__tag__,
                                             self.document_type.__xmlns__))
        if UNICODE_BY_DEFAULT and self.as_bytes:
            return (binary_type(chunk, 'utf-8') for chunk in result)
        elif not UNICODE_BY_DEFAULT and self.as_bytes is False:
            return (chunk.decode('utf-8') for chunk in result)
        return result

    if UNICODE_BY_DEFAULT:
        encode = staticmethod(lambda s: s)
    else:
        encode = staticmethod(lambda s: s.encode('utf-8'))

    def export(self, element, tag, xmlns, depth=0):
        if self.validate:
            validate(element, recurse=False, raise_error=True)
        element_type = type(element)
        for s in itertools.repeat(self.indent, depth):
            yield s
        yield '<'
        if xmlns:
            yield self.xmlns_alias[xmlns]
            yield ':'
        yield tag
        quoteattr = xml.sax.saxutils.quoteattr
        if not depth:
            for uri, prefix in self.sort(self.xmlns_alias.items(),
                                         key=operator.itemgetter(0)):
                yield ' xmlns:'
                yield prefix
                yield '='
                yield quoteattr(uri)
        attr_descriptors = self.sort(
            inspect_attributes(element_type).values(),
            key=operator.itemgetter(0)
        )
        encode = self.encode
        for attr, desc in attr_descriptors:
            raw_attr_value = getattr(element, attr, None)
            if raw_attr_value is None:
                continue
            encoded_attr_value = desc.encode(raw_attr_value, element)
            if encoded_attr_value is None:
                continue
            elif not isinstance(encoded_attr_value, string_type):
                raise EncodeError(
                    '{0.__module__}.{0.__name__}.{1} attribute value {2!r} '
                    'is incorrectly encoded to {3!r}'.format(
                        element_type, attr, raw_attr_value, encoded_attr_value
                    )
                )
            yield ' '
            if desc.xmlns:
                yield self.xmlns_alias[desc.xmlns]
                yield ':'
            yield desc.name
            yield '='
            yield encode(quoteattr(encoded_attr_value))
        content = inspect_content_tag(element_type)
        children = inspect_child_tags(element_type)
        escape = xml.sax.saxutils.escape
        newline = self.newline
        if content or children:
            assert not (content and children)
            yield '>'
            if content:
                raw_content_value = getattr(element, content[0], None)
                encoded_content_value = content[1].encode(raw_content_value,
                                                          element)
                if encoded_content_value is not None:
                    if not isinstance(encoded_content_value, string_type):
                        raise EncodeError(
                            '{0.__module__}.{0.__name__}.{1} attribute value '
                            '{2!r} is incorrectly encoded to {3!r}'.format(
                                element_type, content[0],
                                raw_content_value, encoded_content_value
                            )
                        )
                    yield encode(escape(encoded_content_value))
            else:
                children = self.sort(
                    children.values(),
                    key=lambda pair: pair[1].descriptor_counter
                )
                for attr, desc in children:
                    child_elements = getattr(element, attr, None)
                    if not desc.multiple:
                        child_elements = [child_elements]
                    if desc.sort_key is not None:
                        child_elements = sorted(
                            child_elements,
                            key=desc.sort_key,
                            reverse=bool(desc.sort_reverse)
                        )
                    for child_element in child_elements:
                        if isinstance(desc, Text):  # FIXME: remove type query
                            if child_element is None:
                                continue
                            encoded_child = desc.encode(child_element, element)
                            if encoded_child is None:
                                continue
                            elif not isinstance(encoded_child, string_type):
                                raise EncodeError(
                                    '{0.__module__}.{0.__name__}.{1} attribute '
                                    'value {2!r} is incorrectly encoded to '
                                    '{3!r}'.format(element_type,
                                                   attr,
                                                   child_element,
                                                   encoded_child)
                                )
                            yield newline
                            for s in itertools.repeat(self.indent, depth + 1):
                                yield s
                            yield '<'
                            if desc.xmlns:
                                yield self.xmlns_alias[desc.xmlns]
                                yield ':'
                            yield desc.tag
                            yield '>'
                            yield encode(escape(encoded_child))
                            yield '</'
                            if desc.xmlns:
                                yield self.xmlns_alias[desc.xmlns]
                                yield ':'
                            yield desc.tag
                            yield '>'
                        elif child_element is not None:
                            yield newline
                            subiter = self.export(child_element,
                                                  desc.tag,
                                                  desc.xmlns,
                                                  depth=depth + 1)
                            for chunk in subiter:
                                yield chunk
                yield newline
            if children:
                for s in itertools.repeat(self.indent, depth):
                    yield s
            yield '</'
            if xmlns:
                yield self.xmlns_alias[xmlns]
                yield ':'
            yield tag
            yield '>'
        else:
            yield '/>'
