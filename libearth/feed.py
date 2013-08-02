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
        self.feedlist = []

    def __len__(self):
        return len(self.feedlist)

    def __repr__(self):
        return '<{0.__module__}.{0.__name__} using {1}>'.format(type(self), self.path)
    
    def add_feed(self, title, url):
        if filter(lambda x: x['url'] == url, self.feedlist):
            raise AlreadyExistException("{0} is already Exist".format(title))
        self.feedlist.append({'title': title, 'url': url})

    def remove_feed(self, url):
        """Remove feed from feed list
        @return: True when successfuly removed, False when not removed
        """
        count = len(self.feedlist)
        self.feedlist = filter(lambda x: x['url'] != url, self.feedlist)
        if count > len(self.feedlist):
            return True
        else:
            return False

class AlreadyExistException(Exception):
    pass
