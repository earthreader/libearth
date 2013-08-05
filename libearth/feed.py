""":mod:`libearth.feed` --- Feed list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from .compat import xrange
from .schema import Child, Content, DocumentElement, Element, Text

class OutlineElement(Element):
    value = Content()
    text = Text('text')

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



class Feed(object):
    def __init__(self, path=None):
        """Initializer of Feed list
        when path is None, it doesn't save opml file. just use memory
        """
        #TODO: save with file, load with file
        self.path = path
        self.feedlist = {}

        if self.path:
            self.open_file()

    def __len__(self):
        return len(self.feedlist)

    def open_file(self):
        try:
            with open(self.path) as fp:
                xml = fp.read()
                self.doc = OPMLDoc(xml)
        except IOError as e:
            raise e
        else:
            #TODO: add feed list from doc to self.feedlist
            pass

    def save_file(self):
        #TODO: save as opml file
        pass

    def add_feed(self, title, url):
        if url in self.feedlist:
            raise AlreadyExistException("{0} is already Exist".format(title))
        self.feedlist[url] = {'title': title}

    def remove_feed(self, url):
        """Remove feed from feed list
        :returns: :const:`True` when successfuly removed. :const:`False` when have not to or failed to remove.
        :rtype: :class:`bool`
        """
        if url not in self.feedlist:
            return False
        else:
            self.feedlist.pop(url)
            return True


class AlreadyExistException(Exception):
    pass
