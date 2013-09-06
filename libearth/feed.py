""":mod:`libearth.feed` --- Feeds
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:mod:`libearth` internally stores archive data as Atom format.  It's exactly
not a complete set of :rfc:`4287`, but a subset of the most of that.
Since it's not intended for crawling but internal representation, it does not
follow robustness principle or such thing.  It simply treats stored data are
all valid and well-formed.

"""
import cgi
try:
    import HTMLParser
except ImportError:
    from html import parser as HTMLParser
import re

from .codecs import Enum, Rfc3339
from .compat import UNICODE_BY_DEFAULT, text_type
from .schema import (Attribute, Child, Content, DocumentElement, Element,
                     Text as TextChild)

__all__ = ('ATOM_XMLNS', 'Category', 'Content', 'Entry', 'Link',
           'MarkupTagCleaner', 'Metadata', 'Person', 'Source', 'Text')


#: (:class:`str`) The XML namespace name used for Atom (:rfc:`4287`).
ATOM_XMLNS = 'http://www.w3.org/2005/Atom'


class MarkupTagCleaner(HTMLParser.HTMLParser):
    """Strip all markup tags from HTML string."""

    @classmethod
    def clean(cls, html):
        parser = cls()
        parser.feed(html)
        return ''.join(parser.fed)

    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)


class Text(Element):
    """Text construct defined in :rfc:`4287#section-3.1` (section 3.1)."""

    #: (:class:`str`) The type of the text.  It could be one of ``'text'``
    #: or ``'html'``.  It corresponds to :rfc:`4287#section-3.1.1` (section
    #: 3.1.1).
    #:
    #: .. note::
    #:
    #:    It currently does not support ``'xhtml'``.
    #:
    #: .. todo::
    #:
    #:    Default value should be ``'text'``.
    type = Attribute('type', Enum(['text', 'html']), required=True)

    #: (:class:`str`) The content of the text.  Interpretation for this
    #: has to differ according to its :attr:`type`.  It corresponds to
    #: :rfc:`4287#section-3.1.1.1` (section 3.1.1.1) if :attr:`type` is
    #: ``'text'``, and :rfc:`4287#section-3.1.1.2` (section 3.1.1.2) if
    #: :attr:`type` is ``'html'``.
    value = Content()

    def __unicode__(self):
        if self.type == 'html':
            return MarkupTagCleaner.clean(self.value)
        elif self.type == 'text':
            return self.value

    if UNICODE_BY_DEFAULT:
        __str__ = __unicode__
    else:
        __str__ = lambda self: unicode(self).encode('utf-8')

    def __html__(self):
        if self.type == 'html':
            return self.value
        elif self.type == 'text':
            return cgi.escape(self.value, quote=True).replace('\n', '<br>\n')

    def __repr__(self):
        return '{0.__module__}.{0.__name__}(type={1!r}, value={2!r})'.format(
            type(self), self.type, self.value
        )


class Person(Element):
    """Person construct defined in :rfc:`4287#section-3.2` (section 3.2)."""

    #: (:class:`str`) The human-readable name for the person.  It corresponds
    #: to ``atom:name`` element of :rfc:`4287#section-3.2.1` (section 3.2.1).
    name = TextChild('name', xmlns=ATOM_XMLNS, required=True)

    #: (:class:`str`) The optional URI associated with the person.
    #: It corresponds to ``atom:uri`` element of :rfc:`4287#section-3.2.2`
    #: (section 3.2.2).
    uri = TextChild('uri', xmlns=ATOM_XMLNS)

    #: (:class:`str`) The optional email address associated with the person.
    #: It corresponds to ``atom:email`` element of :rfc:`4287#section-3.2.3`
    #: (section 3.2.3).
    email = TextChild('email', xmlns=ATOM_XMLNS)

    def __unicode__(self):
        ref = self.uri or self.email
        if ref:
            return text_type('{0} <{1}>').format(self.name, ref)
        return self.name

    if UNICODE_BY_DEFAULT:
        __str__ = __unicode__
    else:
        __str__ = lambda self: unicode(self).encode('utf-8')

    def __html__(self):
        name = cgi.escape(self.name, quote=True)
        ref = self.uri or self.email and 'mailto:' + self.email
        if ref:
            return text_type('<a href="{1}">{0}</a>').format(
                name,
                cgi.escape(ref, quote=True)
            )
        return name

    def __repr__(self):
        return ('{0.__module__}.{0.__name__}(name={1!r}, uri={2!r}'
                ', email={3!r})').format(type(self), self.name, self.uri,
                                         self.email)


class Link(Element):
    """Link element defined in :rfc:`4287#section-4.2.7` (section 4.2.7)."""

    #: (:class:`str`) The link's required URI.  It corresponds to ``href``
    #: attribute of :rfc:`4287#section-4.2.7.1` (section 4.2.7.1).
    uri = Attribute('href', required=True)

    #: (:class:`str`) The relation type of the link.  It corresponds to
    #: ``rel`` attribute of :rfc:`4287#section-4.2.7.2` (section 4.2.7.2).
    relation = Attribute('rel')  # TODO: default should be 'alternate'

    #: (:class:`str`) The optional hint for the MIME media type of the linked
    #: content.  It corresponds to ``type`` attribute of
    #: :rfc:`4287#section-4.2.7.3` (section 4.2.7.3).
    mimetype = Attribute('type')

    #: (:class:`str`) The language of the linked content.  It corresponds
    #: to ``hreflang`` attribute of :rfc:`4287#section-4.2.7.4` (section
    #: 4.2.7.4).
    language = Attribute('hreflang')

    #: (:class:`str`) The title of the linked resource.  It corresponds to
    #: ``title`` attribute of :rfc:`4287#section-4.2.7.5` (section 4.2.7.5).
    title = Attribute('title')

    #: (:class:`numbers.Integral`) The optional hint for the length of
    #: the linked content in octets.  It corresponds to ``length`` attribute
    #: of :rfc:`4287#section-4.2.7.6` (section 4.2.7.6).
    byte_size = Attribute('length')

    def __unicode__(self):
        return self.uri

    if UNICODE_BY_DEFAULT:
        __str__ = __unicode__
    else:
        __str__ = lambda self: unicode(self).encode('utf-8')

    def __html__(self):
        mapping = [
            ('rel', self.relation),
            ('type', self.mimetype),
            ('hreflang', self.language),
            ('href', self.uri),
            ('title', self.title)
        ]
        return text_type('<link{0}>').format(
            text_type('').join(
                text_type(' {0}="{1}"').format(attr, value)
                for attr, value in mapping if value
            )
        )

    def __repr__(self):
        return ('{0.__module__}.{0.__name__}(uri={1!r}, relation={2!r}'
                ', mimetype={3!r}, language={4!r}, title={5!r}'
                ', byte_size={6!r})').format(type(self), self.uri,
                                             self.relation, self.mimetype,
                                             self.language, self.title,
                                             self.byte_size)


class Category(Element):
    """Category element defined in :rfc:`4287#section-4.2.2` (section 4.2.2)."""

    #: (:class:`str`) The required machine-readable identifier string of
    #: the cateogry.  It corresponds to ``term`` attribute of
    #: :rfc:`4287#section-4.2.2.1` (section 4.2.2.1).
    term = Attribute('term', required=True)

    #: (:class:`str`) The URI that identifies a categorization scheme.
    #: It corresponds to ``scheme`` attribute of :rfc:`4287#section-4.2.2.2`
    #: (section 4.2.2.2).
    #:
    #: .. seealso::
    #:
    #:    - `Tag Scheme?`__ by Tim Bray
    #:    - `Representing tags in Atom`__ by Edward O'Connor
    #:
    #:    __ http://www.tbray.org/ongoing/When/200x/2007/02/01/Tag-Scheme
    #:    __ http://edward.oconnor.cx/2007/02/representing-tags-in-atom
    scheme_uri = Attribute('scheme')

    #: (:class:`str`) The optional human-readable label for display in
    #: end-user applications.  It corresponds to ``label`` attribute of
    #: :rfc:`4287#section-4.2.2.3` (section 4.2.2.3).
    label = Attribute('label')

    def __unicode__(self):
        return self.label or self.term

    if UNICODE_BY_DEFAULT:
        __str__ = __unicode__
    else:
        __str__ = lambda self: unicode(self).encode('utf-8')

    def __repr__(self):
        return ('{0.__module__}.{0.__name__}(term={1!r}, scheme_uri={2!r}'
                ', label={3!r})').format(type(self), self.term,
                                         self.scheme_uri, self.label)


class Content(Text):
    """Content construct defined in :rfc:`4287#section-4.1.3`
    (section 4.1.3).

    """

    #: (:class:`collections.Mapping`) The mapping of :attr:`type` string
    #: (e.g. ``'text'``) to the corresponding MIME type
    #: (e.g. :mimetype:`text/plain`).
    TYPE_MIMETYPE_MAP = {
        'text': 'text/plain',
        'html': 'text/html',
        'xhtml': 'application/xhtml+xml'
    }

    #: (:class:`re.RegexObject`) The regular expression pattern that matches
    #: with valid MIME type strings.
    MIMETYPE_PATTERN = re.compile(r'''
        ^
        (?P<type> [A-Za-z0-9!#$&.+^_-]{1,127} )
        /
        (?P<subtype> [A-Za-z0-9!#$&.+^_-]{1,127} )
        $
    ''', re.VERBOSE)

    #: (:class:`str`) An optional remote content URI to retrieve the content.
    source_uri = Attribute('src')

    @property
    def mimetype(self):
        """(:class:`str`) The mimetype of the content."""
        try:
            mimetype = self.TYPE_MIMETYPE_MAP[self.type]
        except KeyError:
            mimetype = self.type
        if self.MIMETYPE_PATTERN.match(mimetype):
            return mimetype
        raise ValueError(repr(mimetype) + ' is invalid mimetype')

    @mimetype.setter
    def mimetype(self, mimetype):
        match = self.MIMETYPE_PATTERN.match(mimetype)
        if not match:
            raise ValueError(repr(mimetype) + ' is invalid mimetype')
        if match.group('type') == 'text':
            subtype = match.group('subtype')
            if subtype == 'plain':
                self.type = 'text'
                return
            elif subtype == 'html':
                self.type = 'html'
                return
        self.type = mimetype

    def __repr__(self):
        if not self.source_uri:
            return super(Content, self).__repr__()
        format_string = ('{0.__module__}.{0.__name__}'
                         '(mimetype={1!r}, source_uri={2!r})')
        return format_string.format(type(self), self.mimetype, self.source_uri)


class Metadata(Element):
    """Common metadata shared by :class:`Source`, :class:`Entry`, and
    :class:`Feed`.

    """

    #: (:class:`str`) The URI that conveys a permanent, universally unique
    #: identifier for an entry or feed.  It corresponds to ``atom:id``
    #: element of :rfc:`4287#section-4.2.6` (section 4.2.6).
    id = TextChild('id', xmlns=ATOM_XMLNS, required=True)

    #: (:class:`Text`) The human-readable title for an entry or feed.
    #: It corresponds to ``atom:title`` element of :rfc:`4287#section-4.2.14`
    #: (section 4.2.14).
    title = TextChild('title', xmlns=ATOM_XMLNS, required=True)

    #: (:class:`collections.Seqeuence`) The list of :class:`Link` objects
    #: that define a reference from an entry or feed to a web resource.
    #: It corresponds to ``atom:link`` element of :rfc:`4287#section-4.2.7`
    #: (section 4.2.7).
    links = Child('link', Link, xmlns=ATOM_XMLNS, multiple=True)

    #: (:class:`datetime.datetime`) The tz-aware :class:`~datetime.datetime`
    #: indicating the most recent instant in time when the entry was modified
    #: in a way the publisher considers significant.  Therefore, not all
    #: modifications necessarily result in a changed :attr:`updated_at` value.
    #: It corresponds to ``atom:updated`` element of :rfc:`4287#section-4.2.15`
    #: (section 4.2.15).
    updated_at = TextChild('updated', Rfc3339, xmlns=ATOM_XMLNS, required=True)

    #: (:class:`collections.Seqeuence`) The list of :class:`Person` objects
    #: which indicates the author of the entry or feed.  It corresponds to
    #: ``atom:author`` element of :rfc:`4287#section-4.2.1` (section 4.2.1).
    authors = Child('author', Person, xmlns=ATOM_XMLNS, multiple=True)

    #: (:class:`collections.Seqeuence`) The list of :class:`Person` objects
    #: which indicates a person or other entity who contributed to the entry
    #: or feed.  It corresponds to ``atom:contributor`` element  of
    #: :rfc:`4287#section-4.2.3` (section 4.2.3).
    contributors = Child('contributor', Person, xmlns=ATOM_XMLNS, multiple=True)

    #: (:class:`collections.Sequence`) The list of :class:`Category` objects
    #: that conveys information about categories associated with an entry or
    #: feed.  It corresponds to ``atom:category`` element of
    #: :rfc:`4287#section-4.2.2` (section 4.2.2).
    categories = Child('category', Category, xmlns=ATOM_XMLNS, multiple=True)

    #: (:class:`Text`) The text field that conveys information about rights
    #: held in and of an entry or feed.  It corresponds to ``atom:rights``
    #: element of :rfc:`4287#section-4.2.10` (section 4.2.10).
    rights = Child('rights', Text, xmlns=ATOM_XMLNS)


class Source(Metadata):
    """All metadata for :class:`Feed` excepting :attr:`Feed.entries`.
    It corresponds to ``atom:source`` element of :rfc:`4287#section-4.2.10`
    (section 4.2.10).

    .. todo::

       Implement metadata for feed as well.

    """


class Entry(DocumentElement, Metadata):
    """Represent an individual entry, acting as a container for metadata and
    data associated with the entry.  It corresponds to ``atom:entry`` element
    of :rfc:`4287#section-4.1.2` (section 4.1.2).

    """

    __tag__ = 'entry'
    __xmlns__ = ATOM_XMLNS

    #: (:class:`datetime.datetime`) The tz-aware :class:`~datetime.datetime`
    #: indicating an instant in time associated with an event early in the
    #: life cycle of the entry.  Typically, :attr:`published_at` will be
    #: associated with the initial creation or first availability of
    #: the resource.  It corresponds to ``atom:published`` element of
    #: :rfc:`4287#section-4.2.9` (section 4.2.9).
    published_at = TextChild('published', Rfc3339, xmlns=ATOM_XMLNS,
                             required=True)

    #: (:class:`Text`) The text field that conveys a short summary, abstract,
    #: or excerpt of the entry.  It corresponds to ``atom:summary`` element
    #: of :rfc:`4287#section-4.2.13` (section 4.2.13).
    summary = Child('summary', Text, xmlns=ATOM_XMLNS)

    #: (:class:`Content`) It either contains or links to the content of
    #: the entry.
    #:
    #: It corresponds to ``atom:content`` element of :rfc:`4287#section-4.1.3`
    #: (section 4.1.3).
    content = Child('content', Content, xmlns=ATOM_XMLNS)

    #: (:class:`Source`) If an entry is copied from one feed into another
    #: feed, then the source feed's metadata may be preserved within
    #: the copied entry by adding :attr:`source` if it is not already present
    #: in the entry, and including some or all of the source feed's metadata
    #: as the :attr:`source`'s data.
    #:
    #: It is designed to allow the aggregation of entries from different feeds
    #: while retaining information about an entry's source feed.
    #:
    #: It corresponds to ``atom:source`` element of :rfc:`4287#section-4.2.10`
    #: (section 4.2.10).
    source = Child('source', Source, xmlns=ATOM_XMLNS)

    def __unicode__(self):
        return unicode(self.title)

    def __str__(self):
        return str(self.title)

    def __repr__(self):
        return '<{0.__module__}.{0.__name__} {1}>'.format(type(self), self.id)
