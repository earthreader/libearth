""":mod:`libearth.feed` --- Feed list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from collections import MutableSequence

from .codecs import Boolean, Integer, Rfc822
from .compat import text_type
from .schema import (Attribute, Child, Codec, DocumentElement, Element, Text,
                     read, write)
from .tz import now


class CommaSeparatedList(Codec):
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

    def __init__(self, type, title):
        self.type = type
        self.title = title

    def __repr__(self):
        return '<{0.__module__}.{0.__name__} type={1!r} title={2!r}>'.format(
            type(self), self.type, self.title
        )


class FeedCategory(FeedTree, MutableSequence):
    type = 'category'

    def __init__(self, title, type=None, text=None, xml_url=None,
                 html_url=None, category=None, is_breakpoint=None,
                 created=None):
        super(FeedCategory, self).__init__('category', title)
        self.text = text
        self._type = type
        self.text = text or title
        self.xml_url = xml_url
        self.html_url = html_url
        self.category = category
        self.is_breakpoint = is_breakpoint
        self.created = created

        self.children = []

        #for not allowing same feed on same category
        self.urls = []

    def insert(self, index, value):
        if not isinstance(value, FeedTree):
            raise TypeError('class is must be instance of FeedTree')
        if value.type == 'feed':
            if value.xml_url in self.urls:
                raise AlreadyExistException(
                    "{0!r} is already here".format(value)
                )
            else:
                self.urls.append(value.xml_url)
        elif value.type == 'category':
            if value in self:
                raise AlreadyExistException(
                    "{0!r} is already here"
                    .format(value)
                )
            elif self in value:
                raise AlreadyExistException(
                    "{0!r} contains me. circular referrence is not allowed"
                    .format(value)
                )
            elif value is self:
                raise AlreadyExistException(
                    "{0!r} is me.".format(value)
                )

        self.children.insert(index, value)

    def __contains__(self, key):
        if not isinstance(key, FeedTree):
            raise TypeError("{0!r} must be instance of FeedTree".format(key))

        if key in self.children:
            return True
        else:
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
            raise TypeError('class is must be instance of FeedTree')
        self.children[index] = value

    def __delitem__(self, index):
        del self.children[index]


class Feed(FeedTree):
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
    outline = Child('outline', OutlineElement, multiple=True)


class OPMLDoc(DocumentElement):
    __tag__ = 'opml'
    head = Child('head', HeadElement)
    body = Child('body', BodyElement)


class FeedList(MutableSequence):
    """FeedList is Class for OPML file
    it has a dictionary named :var:`all_feeds` which have all :class:`Feed` for
    linked on multi :class:`FeedCategory`
    :var:`all_feeds` is hashed with tuple key: (type, title, xml_url)
    """
    def __init__(self, path=None, is_xml_string=False):
        """Initializer of Feed list
        when path is None, it doesn't save opml file. just use memory
        """

        #default value
        self.title = "EarthReader"

        self.path = path
        self.feedlist = FeedCategory(self.title)
        self.all_feeds = {}

        if self.path:
            self.open_file(is_xml_string)

    def open_file(self, is_xml_string):
        if is_xml_string:
            xml = self.path
            self.doc = read(OPMLDoc, xml)
            self.parse_doc()
        else:
            try:
                with open(self.path) as fp:
                    xml = fp.read()
                    self.doc = read(OPMLDoc, xml)
            except IOError as e:
                raise e
            else:
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

        #TODO: Change doc.body here
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
            raise SaveOPMLError(e)

    def add_feed(self, type, title, xml_url, html_url=None, text=None,
                 category=None, is_breakoint=None, created=None):
        feed = self.make_feed(type, title, xml_url, html_url, text,
                              category=None, is_breakoint=None, created=None)
        self.feedlist.append(feed)

    def insert(self, index, feed):
        key = (feed.type, feed.title, feed.xml_url)
        if key in self.all_feeds:
            orig_feed = self.all_feeds.get(key)
            self.feedlist.insert(index, orig_feed)

            orig_feed.html_url = feed.html_url
            orig_feed.text = feed.text
        else:
            self.feedlist.insert(index, feed)

    def make_feed(self, type, title, xml_url, html_url=None, text=None,
                  category=None, is_breakoint=None, created=None):
        """pick from all_feeds or make feed for multiple linking"""

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
    def __init__(self, message):
        super(AlreadyExistException, self).__init__(message)


class SaveOPMLError(Exception):
    def __init__(self, message):
        super(SaveOPMLError, self).__init__(message)
