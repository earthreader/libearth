""":mod:`libearth.feed` --- Feed list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from .compat import xrange
from .schema import Child, Content, DocumentElement, Element, Text

class OutlineElement(Element):
    value = Content()

class FeedHead(Element):
    title = Text('title')
    #FIXME: replace these two to Date

    dateCreated = Text('dateCreated')
    dateModified = Text('dateModified')

    ownerName = Text('ownerName')
    ownerEmail = Text('ownerEmail')
    docs = Text('docs')
    expansionState = Text('expansionState')
    vertScrollState = Text('vertScrollState', decoder=int)
    windowTop = Text('windowTop', decoder=int)
    windowBottom = Text('windowBottom', decoder=int)
    windowLeft = Text('windowLeft', decoder=int)
    windowRight = Text('windowRight', decoder=int)

    @expansionState.decoder
    def expansionState(self, text):
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
        with open(self.path) as fp:
            xml = fp.read()
            self.doc = OPMLDoc(xml)

    def save_file(self):
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
