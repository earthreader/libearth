""":mod:`libearth.feed` --- Feed list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from .compat import xrange


class Feed(object):
    def __init__(self, path=None):
        """Initializer of Feed list
        when path is None, it doesn't save opml file. just use memory
        """
        #TODO: save with file, load with file
        self.path = path
        self.feedlist = {}

    def __len__(self):
        return len(self.feedlist)

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
