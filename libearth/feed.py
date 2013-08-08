""":mod:`libearth.feed` --- Feed list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from .compat import binary_type, text, text_type, xrange
from .schema import Attribute, Child, Content, DocumentElement, Element, Text


class OutlineElement(Element):
    text = Attribute('text')
    type_ = Attribute('type')
    xml_url = Attribute('xmlUrl')


class FeedHead(Element):
    title = Text('title')

    #FIXME: replace these two to Date
    date_created = Text('dateCreated')
    date_modified = Text('dateModified')

    owner_name = Text('ownerName')
    owner_email = Text('ownerEmail')
    docs = Text('docs')
    expansion_state = Text('expansionState')
    vert_scroll_state = Text('vertScrollState', decoder=int)
    window_top = Text('windowTop', decoder=int)
    window_bottom = Text('windowBottom', decoder=int)
    window_left = Text('windowLeft', decoder=int)
    window_right = Text('windowRight', decoder=int)

    @expansion_state.decoder
    def expansion_state(self, text):
        return text.split(',')


class FeedBody(Element):
    outline = Child('outline', OutlineElement, multiple=True)


class OPMLDoc(DocumentElement):
    __tag__ = 'opml'
    head = Child('head', FeedHead)
    body = Child('body', FeedBody)


class Feeds(object):
    def __init__(self, path=None, is_xml_string=False):
        """Initializer of Feed list
        when path is None, it doesn't save opml file. just use memory
        """
        #TODO: save with file, load with file
        self.path = path
        self.feedlist = {}

        if self.path:
            self.open_file(is_xml_string)

    def __len__(self):
        return len(self.feedlist)

    def __getattr__(self, name):
        if name == "title":
            return self.doc.head.title

    def __setattr__(self, name, value):
        if name == "title":
            self.doc.head.title = value
        else:
            self.__dict__[name] = value

    def __iter__(self):
        for feed in self.feedlist.values():
            yield feed

    def open_file(self, is_xml_string):
        if is_xml_string:
            xml = self.path
            self.doc = OPMLDoc(xml)
            self.parse_doc()
        else:
            try:
                with open(self.path) as fp:
                    xml = fp.read()
                    self.doc = OPMLDoc(xml)
            except IOError as e:
                raise e
            else:
                self.parse_doc()

    def parse_doc(self):
        for outline in self.doc.body.outline:
            self.feedlist[outline.xml_url] = {
                'title': outline.text,
                'type': outline.type_,
            }

    def save_file(self):
        #TODO: save as opml file
        pass

    def get_feed(self, url):
        if not isinstance(url, text_type):
            url = text(url)

        return self.feedlist.get(url)

    def add_feed(self, url, title, type_):
        if not isinstance(url, text_type):
            url = text(url)

        if url in self.feedlist:
            raise AlreadyExistException("{0} is already Exist".format(title))
        self.feedlist[url] = {
            'title': title,
            'type': type_,
        }

    def remove_feed(self, url):
        """Remove feed from feed list
        :returns: :const:`True` when successfuly removed.
        :const:`False` when have not to or failed to remove.
        :rtype: :class:`bool`
        """
        if url not in self.feedlist:
            return False
        else:
            self.feedlist.pop(url)
            return True


class AlreadyExistException(Exception):
    pass
