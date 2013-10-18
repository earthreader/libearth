""":mod:`libearth.sanitizer` --- Sanitize HTML tags
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import cgi
try:
    import htmlentitydefs
    import HTMLParser
except ImportError:
    from html import entities as htmlentitydefs, parser as HTMLParser
import re

from .compat import unichr

__all__ = 'HtmlSanitizer', 'MarkupTagCleaner', 'clean_html', 'sanitize_html'


def clean_html(html):
    """Strip *all* markup tags from ``html`` string.
    That means, it simply makes the given ``html`` document a plain text.

    :param html: html string to clean
    :type html: :class:`str`
    :returns: cleaned plain text
    :rtype: :class:`str`

    """
    parser = MarkupTagCleaner()
    parser.feed(html)
    return ''.join(parser.fed)


def sanitize_html(html):
    """Sanitize the given ``html`` string.  It removes the following
    tags and attributes that are not secure nor useful for RSS reader layout:

    - ``<script>`` tags
    - ``display: none;`` styles
    - JavaScript event attributes e.g. ``onclick``, ``onload``
    - ``href`` attributes that start with ``javascript:``, ``jscript:``,
      ``livescript:``, ``vbscript:``, ``data:``, ``about:``, or ``mocha:``.

    :param html: html string to sanitize
    :type html: :class:`str`
    :returns: cleaned plain text
    :rtype: :class:`str`

    """
    parser = HtmlSanitizer()
    parser.feed(html)
    return ''.join(parser.fed)


class MarkupTagCleaner(HTMLParser.HTMLParser):
    """HTML parser that is internally used by :func:`clean_html()` function."""

    entity_map = htmlentitydefs.name2codepoint

    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def handle_entityref(self, name):
        try:
            codepoint = self.entity_map[name]
        except KeyError:
            pass
        else:
            self.fed.append(unichr(codepoint))

    def handle_charref(self, name):
        if name.startswith('x'):
            codepoint = int(name[1:], 16)
        else:
            codepoint = int(name)
        self.fed.append(unichr(codepoint))


class HtmlSanitizer(HTMLParser.HTMLParser):
    """HTML parser that is internally used by :func:`sanitize_html()`
    function.

    """

    #: (:class:`re.RegexObject`) The regular expression pattern that matches to
    #: disallowed CSS properties.
    DISALLOWED_STYLE_PATTERN = re.compile(
        r'(^|;)\s*display\s*:\s*[a-z-]+\s*(?:;\s*|$)',
        re.IGNORECASE
    )

    #: (:class:`collections.Set`) The set of disallowed URI schemes e.g.
    #: ``javascript:``.
    DISALLOWED_SCHEMES = frozenset([
        'javascript', 'jscript', 'livescript', 'vbscript', 'data',
        'about', 'mocha'
    ])

    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.fed = []
        self.ignore = False

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.ignore = True
            return
        elif self.ignore:
            return
        remove_css = self.DISALLOWED_STYLE_PATTERN.sub
        self.fed.extend(('<', tag))
        disallowed_schemes = tuple(scheme + ':'
                                   for scheme in self.DISALLOWED_SCHEMES)
        self.fed.extend(
            chunk
            for name, value in attrs
            if not name.startswith('on')
            for chunk in (
                [' ', name]
                if value is None else
                [
                    ' ', name, '="', cgi.escape(
                        ('' if value.startswith(disallowed_schemes) else value)
                        if name == 'href' else
                        (remove_css('\\1', value) if name == 'style' else value)
                    ), '"'
                ]
            )
        )
        self.fed.append('>')

    def handle_endtag(self, tag):
        if tag == 'script':
            self.ignore = False
            return
        self.fed.extend(('</', tag, '>'))

    def handle_data(self, d):
        if self.ignore:
            return
        self.fed.append(d)

    def handle_entityref(self, name):
        if self.ignore:
            return
        self.fed.extend(('&', name, ';'))

    def handle_charref(self, name):
        if self.ignore:
            return
        self.fed.extend(('&#' + name + ';'))

    def handle_comment(self, data):
        if self.ignore:
            return
        self.fed.extend(('<!-- ', data, ' -->'))
