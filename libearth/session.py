""":mod:`libearth.session` --- Sessions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The basic concept of Earth Reader eventually arrives at a problem: how can
we merge simultaneous updates of the same feed without any conflicts?
It's a sort of well known problems in computer science, and there are several
solutions for it e.g. MVCC_ (multiversion concurrency control).

::

    repository = Repository('/path/to/save/files')
    session = Session(repository)

.. _MVCC: http://en.wikipedia.org/wiki/Multiversion_concurrency_control

"""
import uuid

from .repository import Repository

__all__ = 'Session',


class Session(object):

    #: (:class:`~libearth.repository.Repository`) The repository to read and
    #: write.
    repository = None

    #: (:class:`str`) The session identifier.  It has to be distinguishable
    #: from other devices/apps, but consistent for the same device/app.
    identifier = None

    def __init__(self, repository, identifier=None):
        if not isinstance(repository, Repository):
            raise TypeError('repository must be a {0.__module__}.{0.__name__}'
                            ', not {1!r}'.format(Repository, repository))
        self.repository = repository
        self.identifier = identifier or str(uuid.getnode())

    def __repr__(self):
        return '{0.__module__}.{0.__name__}({1!r})'.format(type(self),
                                                           self.path)
