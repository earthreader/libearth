""":mod:`libearth.feedlist` --- Feed list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from collections import MutableSequence

from .codecs import Boolean, Integer, Rfc822
from .compat import text_type
from .schema import (Attribute, Child, Codec, DocumentElement, Element, Text,
                     read, write)
from .tz import now

__all__ = ('AlreadyExistException', 'CommaSeparatedList', 'Feed',
           'FeedCategory', 'FeedList', 'FeedTree', 'SaveOpmlError',)


class CommaSeparatedList(Codec):
    """Encode strings e.g. ``['a', 'b', 'c']`` into a comma-separated list
    e.g. ``'a,b,c'``, and decode it back to a Python list.  Whitespaces
    between commas are ignored.

    >>> codec = CommaSeparatedList()
    >>> codec.encode(['technology', 'business'])
    'technology,business'
    >>> codec.decode('technology, business')
    ['technology', 'business']

    """

    def encode(self, value):
        if value is None:
            res = ""
        elif isinstance(value, text_type):
            res = value
        else:
            res = ",".join(value)
        return res

    def decode(self, text):
        if text is None:
            lst = []
        else:
            lst = [elem.strip() for elem in text.split(',')]
        return lst


class FeedTree(object):
    """Joint base type of :class:`FeedCategory`, :class:`Feed`.  It has
    two common attributes: :attr:`type` and :attr:`title`.

    """

    def __init__(self, type, title):
        self.type = type
        self.title = title

    def __repr__(self):
        return '<{0.__module__}.{0.__name__} type={1!r} title={2!r}>'.format(
            type(self), self.type, self.title
        )


class FeedCategory(FeedTree, MutableSequence):
    """Category of feeds to organize.  It can recursively contains other
    categories as well.  It implements :class:`~collections.MutableSequence`
    interface.

    :param title: human-readable title of the category.
                  it can replace with ``text`` when ``text`` is not present
    :type title: :class:`str`
    :param type: ``type`` attribute of ``outline`` element.
                 not used but OPML spec says `outline` element can has
                 `type` attribute
    :type type: :class:`str`
    :param text: ``text`` attribute of ``outline`` element.
                 it is set to :arg:`title` if omitted
    :type text: :class:`str`
    :param category: ``category`` attribute of ``outline`` element.
                     not used but OPML spec says ``outline`` element can have
                     ``category`` attribute
    :type category: :class:`str`
    :param is_breakpoint: ``isBreakpoint`` attribute of ``outline`` element.
                          not used but OPML spec says ``outline`` element can
                          have ``isBreakpoint`` attribute
    :type is_breakpoint: :class:`str`
    :param created: ``created`` attribute for ``outline`` element.
    :type created: :class:`datetime.datetime`

    """

    type = 'category'

    def __init__(self, title, type=None, text=None, category=None,
                 created=None):
        super(FeedCategory, self).__init__('category', title)
        self.text = text
        self._type = type
        self.text = text or title
        self.created = created  # FIXME: created must be a valid rfc822 string.
                                # so prefer to use datetime
        self.children = []
        self.urls = []  # to avoid duplication of feeds for the same category

    def insert(self, index, value):
        if not isinstance(value, FeedTree):
            raise TypeError('expected an instance of {0.__module__}.'
                            '{0.__name__}, not {1!r}'.format(FeedTree, value))
        if value.type == 'feed':
            if value.xml_url in self.urls:
                raise AlreadyExistException(
                    '{0!r} is already added'.format(value)
                )
            else:
                self.urls.append(value.xml_url)
        elif value.type == 'category':
            if value in self:
                raise AlreadyExistException(
                    '{0!r} is already added'.format(value)
                )
            elif self in value:
                raise AlreadyExistException(
                    '{0!r} already contains {1!r}; '
                    'circular reference is not allowed'.format(value, self)
                )
            elif value is self:
                raise AlreadyExistException('cannot contain itself')

        self.children.insert(index, value)

    def __contains__(self, key):
        if not isinstance(key, FeedTree):
            raise TypeError('key has to be an instance of {0.__module__}.'
                            '{0.__name__}, not {1!r}'.format(FeedTree, key))
        if key in self.children:
            return True
        for child in self.children:
            if child.type == 'category' and key in child:
                return True
        return False

    def __iter__(self):
        return iter(self.children)

    def __len__(self):
        return len(self.children)

    def __getitem__(self, index):
        return self.children[index]

    def __setitem__(self, index, value):
        if not isinstance(value, FeedTree):
            raise TypeError('value must be an instance of {0.__module__}.'
                            '{0.__name__}, not {1!r}'.format(FeedTree, value))
        self.children[index] = value

    def __delitem__(self, index):
        del self.children[index]


class Feed(FeedTree):
    """Subscription feed.  This class has attributes to represent
    an OPML ``outline`` element.

    .. note::

       :attr:`type` cannot be changed from ``'rss'``.
       If you want to get ``type`` attribute of outline,
       use :attr:`rsstype` instead.

    :param rsstype: ``type`` attribute of ``outline`` element
    :type rsstype: :class:`str`
    :param title: ``title`` attribute of ``outline`` element
    :type title: :class:`str`
    :param xml_url: ``xmlUrl`` attribute of ``outline`` element
    :type xml_url: :class:`str`
    :param html_url: ``htmlUrl`` attribute of ``outline`` element
    :type html_url: :class:`str`
    :param text: ``text`` attribute of ``outline`` element.
                 set to :arg:`title` if omitted
    :type text: :class:`str`
    :param category: ``category`` attribute of ``outline`` element
    :type category: :class:`str`
    :param is_breakpoint: ``isBreakpoint`` attribute of ``outline`` element
    :type is_breakpoint: :class:`str`
    :param created: ``created`` attribute of ``outline`` element.
                    it is valid :rfc:`822` format
    :type created: :class:`datetime.datetime`

    """

    def __init__(self, rsstype, title, xml_url, html_url=None, text=None,
                 category=None, is_breakpoint=None, created=None):
        super(Feed, self).__init__('feed', title)
        self.rsstype = rsstype
        self.xml_url = xml_url
        self.html_url = html_url
        self.text = text or title

        self.category = category
        self.is_breakpoint = is_breakpoint
        self.created = created


class OutlineElement(Element):
    """Represent ``outline`` element of OPML document."""

    text = Attribute('text', required=True)
    title = Attribute('title')
    type = Attribute('type')
    xml_url = Attribute('xmlUrl')
    html_url = Attribute('htmlUrl')
    category = Attribute('category', CommaSeparatedList)
    is_breakpoint = Attribute('isBreakpoint', Boolean)
    created = Attribute('created', Rfc822)

    children = Child('outline', 'OutlineElement', multiple=True)


class HeadElement(Element):
    """Represent ``head`` element of OPML document."""

    title = Text('title')

    date_created = Text('dateCreated', Rfc822)
    date_modified = Text('dateModified', Rfc822)

    owner_name = Text('ownerName')
    owner_email = Text('ownerEmail')
    owner_id = Text('ownerId')
    docs = Text('docs')
    expansion_state = Text('expansionState', CommaSeparatedList)
    vert_scroll_state = Text('vertScrollState', Integer)
    window_top = Text('windowTop', Integer)
    window_bottom = Text('windowBottom', Integer)
    window_left = Text('windowLeft', Integer)
    window_right = Text('windowRight', Integer)


class BodyElement(Element):
    """Represent ``body`` element of OPML document.
    :attr:`outline` contains child :class:`OutlineElement` objects.

    """

    outline = Child('outline', OutlineElement, multiple=True)


class OpmlDoc(DocumentElement):

    __tag__ = 'opml'
    head = Child('head', HeadElement)
    body = Child('body', BodyElement)


class FeedList(MutableSequence):
    """Represent OPML document.

    :param path: file path to save the document.  if not present, the document
                 won't be saved but just on memory
    :type path: :class:`str`

    """

    #: (:class:`collections.Mapping`)  Entire :class:`Feed` objects contained
    #: by one or multiple categories.  Hashed by triple of (:attr:`~Feed.type`,
    #: :attr:`~Feed.title`, :attr:`~Feed.xml_url`).
    all_feeds = None

    def __init__(self, path=None, is_xml_string=False):
        # default values  FIXME: the following magic constants should be avoided
        self.title = "EarthReader"
        self.owner_name = "EarthReader"
        self.owner_email = "earthreader@librelist.com"
        self.owner_id = "earthreader.org"
        self.docs = "http://dev.opml.org/spec2.html"
        self.expansion_state = []
        self.vert_scroll_state = 0
        self.window_top = 0
        self.window_left = 0
        self.window_bottom = 0
        self.window_right = 0
        self.date_created = 0
        self.date_modified = 0

        self.path = path
        self.feedlist = FeedCategory(self.title)
        self.all_feeds = {}

        if self.path:
            self.open_file(is_xml_string)

    def open_file(self, is_xml_string):
        if is_xml_string:
            xml = self.path
            self.doc = read(OpmlDoc, xml)
            self.parse_doc()
        else:
            with open(self.path) as fp:
                xml = fp.read()
                self.doc = read(OpmlDoc, xml)
            self.parse_doc()

    def parse_doc(self):
        self.title = self.doc.head.title
        self.owner_name = self.doc.head.owner_name
        self.owner_email = self.doc.head.owner_email
        self.owner_id = self.doc.head.owner_id
        self.docs = self.doc.head.docs
        self.expansion_state = self.doc.head.expansion_state
        self.vert_scroll_state = self.doc.head.vert_scroll_state

        self.window_top = self.doc.head.window_top
        self.window_left = self.doc.head.window_left
        self.window_bottom = self.doc.head.window_bottom
        self.window_right = self.doc.head.window_right

        self.date_created = self.doc.head.date_created
        self.date_modified = self.doc.head.date_modified

        for outline in self.doc.body.outline:
            self.feedlist.append(self.convert_from_outline(outline))

    def save_file(self, filename=None):
        """Save the document as an OPML to the file.
        If ``filename`` is not present, the path the constructor gave will
        be used instead.

        """
        self.doc.head.title = self.title
        self.doc.head.owner_name = self.owner_name
        self.doc.head.owner_email = self.owner_email
        self.doc.head.owner_id = self.owner_id
        self.doc.head.docs = self.docs
        self.doc.head.expansion_state = self.expansion_state
        self.doc.head.vert_scroll_state = self.vert_scroll_state

        self.doc.head.window_top = self.window_top
        self.doc.head.window_left = self.window_left
        self.doc.head.window_bottom = self.window_bottom
        self.doc.head.window_right = self.window_right

        self.doc.body.outline[:] = []
        for feed in self.feedlist:
            self.doc.body.outline.append(self.convert_to_outline(feed))

        timestamp = now()
        self.doc.head.date_modified = timestamp
        if not self.doc.head.date_created:
            self.doc.head.date_created = timestamp

        try:
            filename = filename or self.path
            with open(filename, 'w') as fp:
                for chunk in write(self.doc):
                    fp.write(chunk)
        except Exception as e:
            raise SaveOpmlError(e)

    def add_feed(self, type, title, xml_url, html_url=None, text=None,
                 category=None, is_breakoint=None, created=None):
        feed = self.make_feed(type, title, xml_url, html_url, text,
                              category=None, is_breakoint=None, created=None)
        self.feedlist.append(feed)

    def insert(self, index, feed):
        xml_url = feed.xml_url if hasattr(feed, 'xml_url') else None
        key = (feed.type, feed.title, xml_url)
        if key in self.all_feeds:
            orig_feed = self.all_feeds.get(key)
            self.feedlist.insert(index, orig_feed)
            orig_feed.html_url = feed.html_url
            orig_feed.text = feed.text
        else:
            self.feedlist.insert(index, feed)

    def make_feed(self, type, title, xml_url, html_url=None, text=None,
                  category=None, is_breakoint=None, created=None):
        """Find the existing feed, or add one to include it into multiple
        categories.

        """
        text = text or title

        key = (type, title, xml_url)

        feed = self.all_feeds.get(key)
        if feed:
            feed.html_url = html_url
            feed.text = text
        else:
            feed = Feed(type, title, xml_url, html_url, text, category=None,
                        is_breakpoint=None, created=None)
            self.all_feeds[key] = feed

        return feed

    def convert_from_outline(self, outline_obj):
        if outline_obj.children:
            title = outline_obj.title or outline_obj.text
            type = outline_obj.type
            text = outline_obj.text
            xml_url = outline_obj.xml_url
            html_url = outline_obj.html_url
            category = outline_obj.category
            is_breakpoint = outline_obj.is_breakpoint
            created = outline_obj.created

            res = FeedCategory(title)

            for outline in outline_obj.children:
                res.append(self.convert_from_outline(outline))
        else:
            type = outline_obj.type
            title = outline_obj.title or outline_obj.text
            xml_url = outline_obj.xml_url
            html_url = outline_obj.html_url
            text = outline_obj.text

            category = outline_obj.category
            is_breakpoint = outline_obj.is_breakpoint
            created = outline_obj.created

            res = self.make_feed(type, title, xml_url, html_url, text,
                                 category, is_breakpoint, created)

        return res

    def convert_to_outline(self, feed_obj):
        res = OutlineElement()
        if feed_obj.type == 'category':
            res.type = 'category'
            res.text = feed_obj.text
            res.title = feed_obj.title

            res.children = []
            for child in feed_obj:
                res.children.append(self.convert_to_outline(child))
        else:
            res.type = feed_obj.rsstype
            res.text = feed_obj.text
            res.title = feed_obj.title
            res.xml_url = feed_obj.xml_url
            res.html_url = feed_obj.html_url

        return res

    def __contains__(self, key):
        return key in self.feedlist

    def __len__(self):
        return len(self.feedlist)

    def __iter__(self):
        return iter(self.feedlist)

    def __getitem__(self, key):
        return self.feedlist[key]

    def __setitem__(self, key, value):
        self.feedlist[key] = value

    def __delitem__(self, key):
        del self.feedlist[key]


class AlreadyExistException(Exception):

    pass


class SaveOpmlError(Exception):

    pass
