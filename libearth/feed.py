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

from .codecs import Enum
from .compat import UNICODE_BY_DEFAULT
from .schema import Attribute, Content, Element

__all__ = 'MarkupTagCleaner', 'Text'


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
            return cgi.escape(self.value).replace('\n', '<br>\n')

    def __repr__(self):
        return '{0.__module__}.{0.__name__}(type={1!r}, value={2!r})'.format(
            type(self), self.type, self.value
        )
